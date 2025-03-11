"""
ImageRAGTool for retrieving document content including images from a vector database.
This version includes proper authentication for IBM Cloud Object Storage.
"""
# src/tools/implementations/image_rag_tool.py

import json
import logging
import asyncio
import base64
import aiohttp
import os
import time
from typing import Optional, Dict, List, Tuple, Any, Union

from src.tools.core.base_tool import BaseTool
from src.data_models.tools import ToolResponse
from src.data_models.agent import StreamContext
from src.database import ElasticsearchClient, ElasticQueryBuilder
from src.data_models.chat_completions import UserImageURLContent, UserTextContent
from src.tools.core.tool_registry import ToolRegistry

@ToolRegistry.register_tool()
class ImageRAGTool(BaseTool):
    name = "image_rag"

    def __init__(self, config: Optional[Dict] = None):
        super().__init__()
        self.config = config or {}
        self.strict = True

        self.description = (
            "Tool designed to guide users through iPad setup and issues, MACOS setup, Adobe Acrobat setup, VPN troubleshooting, and VDI troubleshooting. "
        )

        self.parameters = {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': ('Search terms to find relevant content in documents. '
                                    'Example: "content about data processing" or "image showing diagram"'),
                },
                'include_images': {
                    'type': 'boolean',
                    'description': 'Whether to include images in the search results. Defaults to true.',
                }
            },
            'required': ['query'],
            'additionalProperties': False
        }

        self.logger = logging.getLogger(self.__class__.__name__)

        # Load configuration from environment variables if specified in config
        elasticsearch_config = self._load_config_from_env(self.config.get('connector_config', {}))

        self.max_images = elasticsearch_config.get('max_images', 1)
        self.logger.info(f"Maximum images to return: {self.max_images}")

        # TODO(security): Temporary SSL verification bypass for development.
        # Must be updated with proper certificate verification before production deployment.
        self.search_client = ElasticsearchClient(verify_certs=False)

        self.query_builder = ElasticQueryBuilder(elasticsearch_config)
        self.top_k = elasticsearch_config.get('top_k', 5)
        self.query_name = elasticsearch_config.get('query_name', 'basic_match')
        self.elasticsearch_timeout = elasticsearch_config.get('timeout', 30)
        self.max_retries = elasticsearch_config.get('max_retries', 3)
        self.index_name = elasticsearch_config.get('index_name', 'document_rag')

        # IBM Cloud Object Storage configuration
        self.ibm_cos_api_key = elasticsearch_config.get('ibm_cos_api_key')
        self.ibm_cos_service_instance_id = elasticsearch_config.get('ibm_cos_service_instance_id')
        self.ibm_cos_endpoint = elasticsearch_config.get('ibm_cos_endpoint')
        self.ibm_cos_bucket = elasticsearch_config.get('ibm_cos_bucket')
        self.ibm_cos_public_endpoint = elasticsearch_config.get('ibm_cos_public_endpoint')

        # Store auth token once generated
        self.ibm_cos_auth_token = None
        self.token_expiration = 0

        # Log configuration (omitting sensitive data)
        self.logger.info(f"Initialized ImageRAGTool with index: {self.index_name}, top_k: {self.top_k}")
        if self.ibm_cos_api_key:
            self.logger.info("IBM COS credentials are configured")
        else:
            self.logger.warning("IBM COS API key not found - images may not be accessible")

    def _load_config_from_env(self, config: Dict) -> Dict:
        """Load configuration values from environment variables if specified.

        Args:
            config: The base configuration dictionary

        Returns:
            Updated configuration with values from environment variables
        """
        updated_config = config.copy()

        # Load Elasticsearch endpoint from environment if specified
        if 'endpoint_env' in config:
            env_var_name = config['endpoint_env']
            env_value = os.environ.get(env_var_name)
            if env_value:
                updated_config['endpoint'] = env_value
                self.logger.info(f"Loaded Elasticsearch endpoint from {env_var_name}")
            else:
                self.logger.warning(f"Environment variable {env_var_name} not found")

        # Load Elasticsearch API key from environment if specified
        if 'api_key_env' in config:
            env_var_name = config['api_key_env']
            env_value = os.environ.get(env_var_name)
            if env_value:
                updated_config['api_key'] = env_value
                self.logger.info(f"Loaded Elasticsearch API key from {env_var_name}")
            else:
                self.logger.warning(f"Environment variable {env_var_name} not found")

        # IBM COS API Key
        if 'ibm_cos_api_key_env' in config:
            env_var_name = config['ibm_cos_api_key_env']
            env_value = os.environ.get(env_var_name)
            if env_value:
                updated_config['ibm_cos_api_key'] = env_value
                self.logger.info(f"Loaded IBM COS API key from {env_var_name}")
            else:
                self.logger.warning(f"Environment variable {env_var_name} not found")

        # IBM COS Service Instance ID
        if 'ibm_cos_service_instance_id_env' in config:
            env_var_name = config['ibm_cos_service_instance_id_env']
            env_value = os.environ.get(env_var_name)
            if env_value:
                updated_config['ibm_cos_service_instance_id'] = env_value
                self.logger.info(f"Loaded IBM COS Service Instance ID from {env_var_name}")
            else:
                self.logger.warning(f"Environment variable {env_var_name} not found")

        # IBM COS Endpoint
        if 'ibm_cos_endpoint_env' in config:
            env_var_name = config['ibm_cos_endpoint_env']
            env_value = os.environ.get(env_var_name)
            if env_value:
                updated_config['ibm_cos_endpoint'] = env_value
                self.logger.info(f"Loaded IBM COS endpoint from {env_var_name}")
            else:
                self.logger.warning(f"Environment variable {env_var_name} not found")

        # IBM COS Bucket
        if 'ibm_cos_bucket_env' in config:
            env_var_name = config['ibm_cos_bucket_env']
            env_value = os.environ.get(env_var_name)
            if env_value:
                updated_config['ibm_cos_bucket'] = env_value
                self.logger.info(f"Loaded IBM COS bucket from {env_var_name}")
            else:
                self.logger.warning(f"Environment variable {env_var_name} not found")

        # IBM COS Public Endpoint
        if 'ibm_cos_public_endpoint_env' in config:
            env_var_name = config['ibm_cos_public_endpoint_env']
            env_value = os.environ.get(env_var_name)
            if env_value:
                updated_config['ibm_cos_public_endpoint'] = env_value
                self.logger.info(f"Loaded IBM COS public endpoint from {env_var_name}")
            else:
                self.logger.warning(f"Environment variable {env_var_name} not found")

        return updated_config

    async def execute(self, context: Optional[StreamContext] = None, **kwargs) -> ToolResponse:
        """Executes the ImageRAG tool to retrieve document content including images.

        Args:
            context: Context information for the execution.
            **kwargs:
                query (str): The search query string.
                include_images (bool, optional): Whether to include images. Defaults to True.

        Returns:
            ToolResponse: Contains the retrieved content and any image content objects.

        Raises:
            ValueError: If the query parameter is missing.
        """
        query = kwargs.get('query', '')
        if not query:
            raise ValueError("The 'query' parameter is required.")

        include_images = kwargs.get('include_images', True)

        self.logger.info(f"Executing ImageRAG Tool with query: {query}, include_images: {include_images}")

        # Retrieve content from Elasticsearch
        retrieved_content, content_objects = await self._retrieve_content(
            user_input=query,
            index_name=self.index_name,
            top_k=self.top_k,
            include_images=include_images
        )

        # Create the response with both text results and image content objects
        response = ToolResponse(
            result=self.parse_output(retrieved_content),
            context={"content_objects": content_objects} if content_objects else None,
        )
        return response

    async def _retrieve_content(self, user_input: str, index_name: str, top_k: int = None,
                                include_images: bool = True) -> Tuple[
        str, List[Union[UserTextContent, UserImageURLContent]]]:
        """Retrieve content from Elasticsearch including images if requested.

        Args:
            user_input: User's query.
            index_name: Name of the Elasticsearch index.
            top_k: Number of results to return.
            include_images: Whether to include images in results.

        Returns:
            Tuple of (text content, list of content objects for images)

        Raises:
            RuntimeError: If retrieval fails.
        """
        self.logger.info("Querying Elasticsearch for document content")
        top_k = top_k if top_k is not None else self.top_k

        # Configure query to include images if requested
        query_body = self.query_builder.get_query(user_input)

        # Add filter for content_type if not including images
        if not include_images:
            if "query" not in query_body:
                query_body["query"] = {}

            if "bool" not in query_body["query"]:
                query_body["query"] = {"bool": {"must": [query_body["query"]]}}

            if "must_not" not in query_body["query"]["bool"]:
                query_body["query"]["bool"]["must_not"] = []

            # Add filter to exclude image content_type
            query_body["query"]["bool"]["must_not"].append({
                "term": {"content_type.keyword": "image"}
            })

        self.logger.debug(f"Elastic query body: {json.dumps(query_body)}")
        query_results = None

        # Perform Elasticsearch query with retries and timeout
        for attempt in range(self.max_retries):
            try:
                query_results = await asyncio.wait_for(
                    self.search_client.search(query_body, index_name, top_k),
                    timeout=self.elasticsearch_timeout
                )
                break  # Exit the loop if successful
            except asyncio.TimeoutError:
                self.logger.error(f"Elasticsearch query timed out (attempt {attempt + 1}/{self.max_retries})")
                if attempt + 1 == self.max_retries:
                    raise  # Raise the exception if max retries reached

        if query_results is None:
            raise RuntimeError("Failed to retrieve Elasticsearch query results.")

        # Extract hits and sort by score
        hits = []
        for hit in query_results["hits"]["hits"]:
            # Check if response has _source or fields
            if "_source" in hit:
                # Using _source field
                hit_data = {
                    "_score": hit["_score"],
                    "content": hit["_source"].get("content", ""),
                    "content_type": hit["_source"].get("content_type", "text"),
                    "image_url": hit["_source"].get("image_url"),
                    "image_hash": hit["_source"].get("image_hash"),
                    "section_header": hit["_source"].get("section_header", ""),
                    "page_number": hit["_source"].get("page_number", "")
                }
            elif "fields" in hit:
                # Using fields parameter
                fields = hit["fields"]
                hit_data = {
                    "_score": hit["_score"],
                    "content": self._get_first_value(fields.get("content", [])),
                    "content_type": self._get_first_value(fields.get("content_type", [])),
                    "image_url": self._get_first_value(fields.get("image_url", [])),
                    "image_hash": self._get_first_value(fields.get("image_hash", [])),
                    "section_header": self._get_first_value(fields.get("section_header", [])),
                    "page_number": self._get_first_value(fields.get("page_number", []))
                }
            else:
                # Neither _source nor fields found, use empty data
                self.logger.warning(f"Hit missing both _source and fields: {hit}")
                hit_data = {
                    "_score": hit["_score"],
                    "content": "",
                    "content_type": "text",
                    "image_url": None,
                    "image_hash": None,
                    "section_header": "",
                    "page_number": ""
                }
            hits.append(hit_data)

        # Sort hits by score
        hits.sort(key=lambda x: x["_score"], reverse=True)

        # Process hits into text content and image content objects
        text_content = []
        content_objects = []

        # Counter for images added
        image_count = 0

        for hit in hits[:top_k]:
            # Add section header if available
            section_info = ""
            if hit["section_header"]:
                section_info = f"Section: {hit['section_header']}\n\n"

            # Add page number if available
            page_info = ""
            if hit["page_number"]:
                page_info = f"(Page {hit['page_number']})"

            # Handle different content types
            if hit["content_type"] == "image" and include_images and hit["image_url"] and image_count < self.max_images:
                # Create image content for the response
                try:
                    # Add text description to the text content
                    text_content.append(f"{section_info}[Image] {page_info}\n{hit['content']}")

                    # Get image data and convert to base64 for image content object
                    image_base64 = await self._fetch_and_encode_image(hit["image_url"])
                    if image_base64:
                        # Create image content object with data URI
                        image_content = UserImageURLContent(
                            type="image_url",
                            image_url={"url": f"data:image/png;base64,{image_base64}"},
                            detail="high"
                        )
                        content_objects.append(image_content)

                        # Add text content object as well for the description
                        text_objects = UserTextContent(
                            type="text",
                            text=f"{section_info}Image description {page_info}: {hit['content']}"
                        )
                        content_objects.append(text_objects)

                        # Increment image counter
                        image_count += 1
                        self.logger.info(f"Added image {image_count}/{self.max_images}")
                except Exception as e:
                    self.logger.error(f"Error processing image: {str(e)}")
                    # Still include the text description
                    text_content.append(f"{section_info}[Image - Error loading] {page_info}\n{hit['content']}")
            elif hit["content_type"] == "image" and include_images and hit[
                "image_url"] and image_count >= self.max_images:
                # We've reached the maximum number of images, but still include the text description
                text_content.append(f"{section_info}[Image - Limit reached] {page_info}\n{hit['content']}")
                self.logger.info(f"Skipping image due to limit ({image_count}/{self.max_images})")
            else:
                # Regular text content
                text_content.append(f"{section_info}{hit['content']} {page_info}")

        # If we limited the images, add a note
        if image_count >= self.max_images and any(
                hit["content_type"] == "image" for hit in hits[self.max_images:top_k]):
            text_content.append(
                f"\n\nNote: Only showing {self.max_images} images due to limit. More images were found but not displayed.")

        # Combine text content
        combined_text = "\n\n".join(text_content) + "\n\n" + self.get_tool_specific_instruction()

        return combined_text, content_objects

    def _get_first_value(self, field_values: List) -> Any:
        """Extract the first value from a field array or return empty string.

        Args:
            field_values: List of field values from Elasticsearch response

        Returns:
            The first value in the list or empty string if list is empty
        """
        if field_values and len(field_values) > 0:
            return field_values[0]
        return ""

    async def _get_ibm_cos_auth_token(self) -> Optional[str]:
        """Get an authentication token for IBM Cloud Object Storage.

        Uses the IBM Cloud IAM API to get a token using the API key.

        Returns:
            Authentication token string or None if failed
        """
        # Check if we already have a valid token
        current_time = time.time()
        if self.ibm_cos_auth_token and current_time < self.token_expiration:
            return self.ibm_cos_auth_token

        # Get API key from config or environment
        api_key = self.ibm_cos_api_key or os.environ.get('IBM_COS_API_KEY')
        if not api_key:
            self.logger.error("IBM COS API key not found in config or environment")
            return None

        # Request token from IBM IAM API
        auth_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(auth_url, headers=headers, data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.ibm_cos_auth_token = result.get("access_token")
                        # Set expiration time (slightly earlier than actual for safety)
                        expires_in = result.get("expires_in", 3600)
                        self.token_expiration = current_time + expires_in - 60

                        self.logger.info("Successfully obtained IBM COS authentication token")
                        return self.ibm_cos_auth_token
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to get IBM COS token: HTTP {response.status}, {error_text}")
                        return None
        except Exception as e:
            self.logger.error(f"Error obtaining IBM COS authentication token: {str(e)}")
            return None

    async def _fetch_and_encode_image(self, image_url: str) -> Optional[str]:
        """Fetch image from URL and encode as base64.

        Args:
            image_url: URL of the image to fetch.

        Returns:
            Base64 encoded image string, or None if fetching failed.
        """
        if not image_url:
            return None

        # If the image_url is relative and we have IBM COS credentials, build the full URL
        if not image_url.startswith(('http://', 'https://')):
            # Get bucket name from config or environment
            bucket = self.ibm_cos_bucket or os.environ.get('IBM_COS_BUCKET', 'rag-docs-bucket')

            # Use public endpoint if available, otherwise regular endpoint
            endpoint = self.ibm_cos_public_endpoint or os.environ.get('IBM_COS_PUBLIC_ENDPOINT', '')
            if not endpoint:
                endpoint = self.ibm_cos_endpoint or os.environ.get('IBM_COS_ENDPOINT', '')

            # Ensure endpoint has protocol
            if endpoint and not endpoint.startswith(('http://', 'https://')):
                endpoint = f"https://{endpoint}"

            if endpoint:
                # Construct full URL
                if endpoint.endswith('/') and bucket.startswith('/'):
                    full_url = f"{endpoint}{bucket[1:]}"
                elif not endpoint.endswith('/') and not bucket.startswith('/'):
                    full_url = f"{endpoint}/{bucket}"
                else:
                    full_url = f"{endpoint}{bucket}"

                # Add the object path
                if full_url.endswith('/') and image_url.startswith('/'):
                    image_url = f"{full_url}{image_url[1:]}"
                elif not full_url.endswith('/') and not image_url.startswith('/'):
                    image_url = f"{full_url}/{image_url}"
                else:
                    image_url = f"{full_url}{image_url}"

                self.logger.info(f"Constructed full image URL: {image_url}")
            else:
                self.logger.warning("No IBM COS endpoint found, can't construct full URL")

        self.logger.info(f"Fetching image from URL: {image_url}")

        # Try direct access first (no authentication)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        # Convert to base64
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        return base64_data
                    elif response.status == 403:  # Forbidden - needs authentication
                        self.logger.info("Image access forbidden, trying with authentication")
                    else:
                        self.logger.error(f"Failed to fetch image: HTTP {response.status}")
        except Exception as e:
            self.logger.error(f"Error fetching image from {image_url}: {str(e)}")

        # Try with authentication token if direct access failed
        try:
            # Get authentication token
            token = await self._get_ibm_cos_auth_token()
            if not token:
                self.logger.error("Failed to get IBM COS authentication token")
                return None

            # Try fetching with authorization header
            headers = {"Authorization": f"Bearer {token}"}

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, headers=headers) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        # Convert to base64
                        base64_data = base64.b64encode(image_data).decode('utf-8')
                        return base64_data
                    else:
                        self.logger.error(f"Failed to fetch image with token: HTTP {response.status}")
        except Exception as e:
            self.logger.error(f"Error fetching image with authentication: {str(e)}")

        # Failed to fetch the image
        return None

    def parse_output(self, output: str) -> str:
        """Parse and format the retrieved content.

        Args:
            output: Raw content from Elasticsearch.

        Returns:
            Formatted content with context header.
        """
        if not output:
            return "No relevant information found in the documents."

        # Return the output with a context header
        return (
            "## Retrieved Document Content ##\n\n"
            f"{output}"
        )

    def get_tool_specific_instruction(self) -> str:
        return (
            "When responding to the query, carefully assess the relevance of any retrieved content, especially images. "
            "Only reference and describe images that are directly relevant to the user's query. "
            "For images that appear tangential or unrelated to the specific question, omit them from your response. "
            "Prioritize textual information that answers the query directly, and use images as supporting evidence "
            "only when they provide significant additional context or clarification. "
            "If no retrieved content adequately addresses the query, acknowledge this limitation clearly."
        )
