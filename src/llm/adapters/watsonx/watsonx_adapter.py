import time
import json
import logging
import asyncio
import aiohttp
from aiohttp import ClientError
from asyncio import TimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional, Dict, Any

from src.data_models.tools import Tool
from src.llm.adapters import BaseVendorAdapter
from src.data_models.chat_completions import TextChatMessage
from src.llm.adapters.watsonx.watsonx_config import WatsonXConfig
from src.llm.adapters.watsonx.ibm_token_manager import IBMTokenManager
from src.api.sse_models import SSEChunk, SSEChoice, SSEDelta, SSEToolCall, SSEFunction

logger = logging.getLogger(__name__)

MAX_RETRIES = 1  # no retries
MIN_RETRY_WAIT = 1  # seconds
MAX_RETRY_WAIT = 10  # seconds

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(
    total=300,  # 5 minutes total timeout
    connect=60,  # 60 seconds connection timeout
    sock_read=60  # 60 seconds socket read timeout
)


class WatsonXAdapter(BaseVendorAdapter):
    """Adapter for interacting with IBM WatsonX's API.

    This class implements the BaseVendorAdapter interface for WatsonX language models,
    handling authentication, streaming requests, and response parsing. It converts
    WatsonX-specific formats into standardized SSE chunks for consistent handling
    across different LLM providers.

    Attributes:
        model_id (str): The WatsonX model identifier.
        model_params (dict): Default parameters for model requests.
        token_manager (IBMTokenManager): Manager for IBM Cloud authentication tokens.
        project_id (str): WatsonX project identifier.
        base_url (str): Base URL for WatsonX API endpoints.
        timeout (aiohttp.ClientTimeout): Timeout configuration for requests.
        _session (Optional[aiohttp.ClientSession]): Reusable HTTP session.
    """

    def __init__(self,
                 model_name: str,
                 token_manager: IBMTokenManager,
                 timeout: Optional[aiohttp.ClientTimeout] = None,
                 **model_params):
        """Initialize the WatsonX Adapter with model configuration.

        Args:
            model_name (str): The identifier of the WatsonX model to use.
            token_manager (IBMTokenManager): Manager for handling IBM authentication.
            timeout (Optional[aiohttp.ClientTimeout]): Custom timeout configuration.
            **model_params: Additional parameters to include in model requests.

        Raises:
            ValueError: If required configuration is missing.
        """
        self.model_id = model_name
        self.model_params = model_params or {}
        self.token_manager = token_manager
        self.project_id = WatsonXConfig.PROJECT_ID
        self.base_url = "https://us-south.ml.cloud.ibm.com/ml/v1/text"
        self._session: Optional[aiohttp.ClientSession] = None
        self.timeout = timeout or DEFAULT_TIMEOUT
        logger.info(f"WatsonX Adapter initialized with model: {self.model_id}")
        logger.debug(f"Model parameters configured: {model_params}")
        logger.debug(f"Timeout configuration: {self.timeout}")

    @asynccontextmanager
    async def _session_context(self):
        """Manage the lifecycle of an HTTP session.

        Yields:
            aiohttp.ClientSession: Active HTTP session for making requests.
        """
        logger.debug("Creating new HTTP session")
        session = aiohttp.ClientSession(timeout=self.timeout)
        try:
            yield session
        finally:
            await session.close()
            logger.debug("HTTP session closed")

    async def gen_chat_sse_stream(
            self,
            messages: List[TextChatMessage],
            tools: Optional[List[Tool]] = None,
            timeout: Optional[aiohttp.ClientTimeout] = None,
            **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate a streaming chat response from a sequence of messages.

        Args:
            messages (List[TextChatMessage]): List of chat messages for context.
            tools (Optional[List[Tool]]): List of tools available to the model.
            timeout (Optional[aiohttp.ClientTimeout]): Optional request-specific timeout.
            **kwargs: Additional parameters to override defaults.

        Yields:
            SSEChunk: Standardized chunks of the streaming response.

        Raises:
            RuntimeError: If the WatsonX API request fails.
            TimeoutError: If the request times out.
        """
        logger.debug(f"Processing chat stream request with {len(messages)} messages")
        serialized_messages = [msg.model_dump() for msg in messages]
        serialized_tools = [tool.model_dump() for tool in tools] if tools else None

        payload = {
            "model_id": self.model_id,
            "project_id": self.project_id,
            "messages": serialized_messages,
            **kwargs
        }
        if serialized_tools:
            logger.debug(f"Adding {len(serialized_tools)} tools to request")
            payload["tools"] = serialized_tools

        async for raw_chunk in self._make_sse_request("chat_stream", payload, timeout):
            sse_chunk = self._convert_to_sse_chunk(raw_chunk)
            yield sse_chunk

    async def gen_sse_stream(
            self,
            prompt: str,
            timeout: Optional[aiohttp.ClientTimeout] = None,
            **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate text using WatsonX's generation_stream endpoint.

        Args:
            prompt (str): The input text prompt.
            timeout (Optional[aiohttp.ClientTimeout]): Optional request-specific timeout.
            **kwargs: Additional parameters to pass to the API.

        Yields:
            SSEChunk: Server-sent event chunks containing generated text.

        Raises:
            RuntimeError: If the streaming request fails.
            TimeoutError: If the request times out.
        """
        logger.debug(f"Processing generation stream request. Prompt: {prompt[:50]}...")
        payload = {
            "model_id": self.model_id,
            "project_id": self.project_id,
            "input": prompt,
            "parameters": {
                **self.model_params,
                **kwargs
            }
        }

        async for raw_chunk in self._make_sse_request("generation_stream", payload, timeout):
            sse_chunk = self._convert_to_sse_chunk(raw_chunk)
            yield sse_chunk

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=MIN_RETRY_WAIT, max=MAX_RETRY_WAIT),
        retry=retry_if_exception_type((ClientError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    async def _make_sse_request(self,
                                endpoint: str,
                                payload: Dict[str, Any],
                                timeout: Optional[aiohttp.ClientTimeout] = None) \
            -> AsyncGenerator[Dict[str, Any], None]:
        """Make a streaming request to WatsonX API with retry logic.

        Args:
            endpoint (str): API endpoint to call.
            payload (Dict[str, Any]): Request payload data.
            timeout (Optional[aiohttp.ClientTimeout]): Optional request-specific timeout.

        Yields:
            Dict[str, Any]: Raw response chunks from the API.

        Raises:
            aiohttp.ClientError: If all retry attempts fail with HTTP errors.
            ValueError: If response parsing fails.
            TimeoutError: If all retry attempts timeout.
            Exception: If all retry attempts fail for other reasons.
        """
        token = await self.token_manager.get_token()
        url = f"{self.base_url}/{endpoint}?version=2023-05-29"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        logger.debug(f"Making request to endpoint: {endpoint}")
        logger.debug(f"Request payload: {json.dumps(payload, indent=2)}")

        try:
            async with self._session_context() as session:
                async with session.post(url,
                                        json=payload,
                                        headers=headers,
                                        timeout=timeout or self.timeout) as resp:
                    resp.raise_for_status()
                    logger.debug(f"Stream connected, status: {resp.status}")

                    buffer = []
                    async for raw_line in resp.content:
                        line = raw_line.decode("utf-8").strip()

                        if not line:
                            event_data = self._parse_sse_event(buffer)
                            buffer = []

                            if "data" in event_data:
                                try:
                                    data_parsed = json.loads(event_data["data"])
                                    yield data_parsed
                                except json.JSONDecodeError:
                                    logger.warning(f"Skipping invalid SSE data: {event_data['data']}")
                            continue

                        buffer.append(line)

        except aiohttp.ClientError as e:
            logger.error(f"HTTP request failed: {str(e)}", exc_info=True)
            raise
        except asyncio.TimeoutError as e:
            logger.error(f"Request timed out: {str(e)}", exc_info=True)
            raise TimeoutError(f"Request to {endpoint} timed out") from e

    def _parse_sse_event(self, lines: List[str]) -> Dict[str, str]:
        """Parse Server-Sent Events format into structured data.

        Args:
            lines (List[str]): Raw SSE message lines.

        Returns:
            Dict[str, str]: Parsed event data.
        """
        event = {}
        for line in lines:
            if line.startswith("id:"):
                event["id"] = line[len("id:"):].strip()
            elif line.startswith("event:"):
                event["event"] = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                event["data"] = event.get("data", "") + data_str
        return event

    def _convert_to_sse_chunk(self, raw_chunk: dict) -> SSEChunk:
        """Convert WatsonX response format to standardized SSE chunk.

        Handles both generation_stream and chat_stream response formats.

        Args:
            raw_chunk (dict): Raw response data from WatsonX.

        Returns:
            SSEChunk: Standardized chunk format.

        Raises:
            ValueError: If chunk conversion fails.
        """
        try:
            logger.debug(f"Converting chunk: {json.dumps(raw_chunk, indent=2)}")
            # Handle generation_stream format
            if "results" in raw_chunk:
                result = raw_chunk["results"][0]
                choices = [
                    SSEChoice(
                        index=0,
                        delta=SSEDelta(
                            content=result.get("generated_text"),
                            role="assistant"
                        ),
                        logprobs=None,
                        finish_reason=result.get("stop_reason")
                    )
                ]
            # Handle chat_stream format
            else:
                choices = []
                for choice_dict in raw_chunk.get('choices', []):
                    delta_data = choice_dict.get('delta', {})

                    tool_calls = None
                    if "tool_calls" in delta_data:
                        tool_calls = [
                            SSEToolCall(
                                index=tc.get("index", 0),
                                id=tc.get("id"),
                                type=tc.get("type", "function"),
                                function=SSEFunction(
                                    name=tc["function"]["name"],
                                    arguments=tc["function"].get("arguments", "")
                                ) if tc.get("function") else None
                            ) for tc in delta_data["tool_calls"]
                        ]

                    delta = SSEDelta(
                        role=delta_data.get("role"),
                        content=delta_data.get("content"),
                        tool_calls=tool_calls,
                        refusal=delta_data.get("refusal"),
                        status=delta_data.get("status"),
                        metadata=delta_data.get("metadata")
                    )

                    choices.append(SSEChoice(
                        index=choice_dict.get("index", 0),
                        delta=delta,
                        logprobs=choice_dict.get("logprobs"),
                        finish_reason=choice_dict.get("finish_reason")
                    ))

            return SSEChunk(
                id=raw_chunk.get("id", f"watsonx-{int(time.time())}"),
                object=raw_chunk.get("object", "chat.completion.chunk"),
                created=raw_chunk.get("created", int(time.time())),
                model=raw_chunk.get("model", self.model_id),
                choices=choices
            )
        except Exception as e:
            logger.error(f"Error converting WatsonX chunk: {raw_chunk}", exc_info=True)
            raise ValueError(f"Failed to convert WatsonX response to SSEChunk: {str(e)}") from e
