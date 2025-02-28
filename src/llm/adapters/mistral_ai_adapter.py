import os
import logging
from datetime import datetime
from mistralai import Mistral
from typing import AsyncGenerator, List, Optional, Any

from src.data_models.tools import Tool
from src.llm.adapters import BaseVendorAdapter
from src.data_models.chat_completions import TextChatMessage
from src.api import SSEChunk, SSEChoice, SSEDelta, SSEToolCall, SSEFunction

logger = logging.getLogger(__name__)


class MistralAIAdapter(BaseVendorAdapter):
    """Adapter for interacting with Mistral AI's API.

    This class implements the BaseVendorAdapter interface for Mistral's chat models,
    handling authentication, request formatting, and response streaming. It converts
    Mistral-specific response formats into standardized SSE chunks for consistent
    handling across different LLM providers.

    Attributes:
        `api_key` (str): Mistral API key loaded from environment variables.
        `client` (Mistral): Authenticated Mistral client instance.
        `model_name` (str): The Mistral model identifier (e.g., "mistral-tiny").
        `default_params` (dict): Default parameters for Mistral API calls.
    """

    def __init__(self, model_name: str, **default_params):
        """Initialize the Mistral AI Adapter with model configuration.

        Args:
            `model_name` (str): The identifier of the Mistral model to use (e.g., "mistral-tiny").
            `**default_params`: Additional parameters to include in all API calls.
                Common parameters include temperature, max_tokens, etc.

        Raises:
            `ValueError`: If MISTRAL_API_KEY environment variable is not set.
        """
        self.api_key = os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("Missing Mistral API key. Set the MISTRAL_API_KEY environment variable.")

        self.client = Mistral(api_key=self.api_key)
        self.model_name = model_name
        self.default_params = default_params
        logger.info(f"Mistral AI Adapter initialized with model: {self.model_name}")
        logger.debug(f"Default parameters configured: {default_params}")

    async def gen_sse_stream(
            self,
            prompt: str,
            **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate SSE stream from a single text prompt.

        Converts a single prompt into a chat message and streams the response.

        Args:
            `prompt` (str): The text prompt to send to the model.
            `**kwargs`: Additional parameters to override defaults for this request.

        Yields:
            `SSEChunk`: Standardized chunks of the streaming response.

        Raises:
            `RuntimeError`: If the streaming request fails.
        """
        logger.debug(f"Converting single prompt to chat format: {prompt[:50]}...")
        messages = [{"role": "user", "content": prompt}]
        async for chunk in self.gen_chat_sse_stream(messages, **kwargs):
            yield chunk

    async def gen_chat_sse_stream(
            self,
            messages: List[TextChatMessage],
            tools: Optional[List[Tool]] = None,
            **kwargs,
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate a streaming chat response from a sequence of messages.

        Args:
            `messages` (List[TextChatMessage]): List of chat messages for context.
            `tools` (Optional[List[Tool]]): List of tools available to the model.
            `**kwargs`: Additional parameters to override defaults for this request.

        Yields:
            `SSEChunk`: Standardized chunks of the streaming response.

        Raises:
            `RuntimeError`: If the Mistral API request fails.
        """
        mistral_messages = [msg.model_dump() for msg in messages]
        logger.debug(f"Processing chat stream request with {len(messages)} messages")

        request_payload = {
            "model": self.model_name,
            "messages": mistral_messages,
            **self.default_params,
            **kwargs,
        }

        if tools:
            logger.debug(f"Adding {len(tools)} tools to request")
            request_payload["tools"] = [tool.model_dump() for tool in tools]
            request_payload["tool_choice"] = "auto"

        try:
            logger.debug("Initiating Mistral streaming request")
            response = await self.client.chat.stream_async(**request_payload)
            async for chunk in response:
                yield await self._convert_to_sse_chunk(chunk)
        except Exception as e:
            logger.error(f"Error in Mistral streaming: {str(e)}", exc_info=True)
            raise RuntimeError(f"Mistral API streaming failed: {str(e)}") from e

    def _is_unset(self, value: Any) -> bool:
        """Check if a value is an Unset instance from Mistral's API.

        Args:
            value: Any value to check

        Returns:
            bool: True if the value is an Unset instance, False otherwise
        """
        # Check for the Unset class without using direct comparison
        # This handles cases where the value is an instance of Unset class
        return (
                value is not None and
                hasattr(value, '__class__') and
                value.__class__.__name__ == 'Unset'
        )

    def _safe_get_attr(self, obj: Any, attr_name: str, default: Any = None) -> Any:
        """Safely get an attribute value, handling Unset instances.

        Args:
            `obj`: Object to get attribute from
            `attr_name`: Name of the attribute
            `default`: Default value if attribute is missing or Unset

        Returns:
            The attribute value or default
        """
        if obj is None:
            return default

        value = getattr(obj, attr_name, default)
        return default if self._is_unset(value) else value

    async def _convert_to_sse_chunk(self, raw_chunk) -> SSEChunk:
        """Convert Mistral's response chunk to standardized SSE format.

        Transforms Mistral's response objects into the application's
        standardized SSEChunk format, handling all possible response fields
        including tool calls, content, and metadata.

        Args:
            `raw_chunk`: Raw chunk from Mistral's API, could be CompletionChunk or CompletionEvent.

        Returns:
            `SSEChunk`: Standardized chunk format for consistent handling.

        Raises:
            `ValueError`: If chunk conversion fails due to unexpected format.
        """
        try:
            # Check if this is a CompletionEvent with data attribute (mistralai client wraps responses)
            chunk_data = getattr(raw_chunk, 'data', raw_chunk)

            # Get chunk ID with fallback
            chunk_id = self._safe_get_attr(chunk_data, 'id', f"gen-{id(chunk_data)}")
            logger.debug(f"Converting chunk ID: {chunk_id}")

            choices = []
            chunk_choices = self._safe_get_attr(chunk_data, 'choices', [])

            for choice in chunk_choices:
                # Extract delta from choice
                delta = self._safe_get_attr(choice, 'delta')

                # Handle tool calls if present
                tool_calls = None
                delta_tool_calls = self._safe_get_attr(delta, 'tool_calls')

                if delta_tool_calls and not self._is_unset(delta_tool_calls):
                    tool_calls = []
                    for tc in delta_tool_calls:
                        # Process function within tool call
                        tc_function = self._safe_get_attr(tc, 'function')
                        function = None

                        if tc_function:
                            function = SSEFunction(
                                name=self._safe_get_attr(tc_function, 'name', ""),
                                arguments=self._safe_get_attr(tc_function, 'arguments', "")
                            )

                        tool_calls.append(SSEToolCall(
                            index=self._safe_get_attr(tc, 'index', 0),
                            id=self._safe_get_attr(tc, 'id'),
                            type="function",  # Default to function if not specified
                            function=function
                        ))

                # Create delta safely
                sse_delta = SSEDelta(
                    role=self._safe_get_attr(delta, 'role'),
                    content=self._safe_get_attr(delta, 'content'),
                    tool_calls=tool_calls,
                    refusal=self._safe_get_attr(delta, 'refusal')
                )

                # Create choice
                choices.append(SSEChoice(
                    index=self._safe_get_attr(choice, 'index', 0),
                    delta=sse_delta,
                    logprobs=self._safe_get_attr(choice, 'logprobs'),
                    finish_reason=self._safe_get_attr(choice, 'finish_reason')
                ))

            # Build and return the final SSEChunk
            return SSEChunk(
                id=chunk_id,
                object=self._safe_get_attr(chunk_data, 'object', 'chat.completion.chunk'),
                created=self._safe_get_attr(chunk_data, 'created', int(datetime.now().timestamp())),
                model=self._safe_get_attr(chunk_data, 'model', self.model_name),
                service_tier=None,  # Default to None if not provided by Mistral
                system_fingerprint=None,  # Default to None if not provided by Mistral
                choices=choices
            )

        except Exception as e:
            logger.error(f"Error converting Mistral chunk: {raw_chunk}", exc_info=True)
            raise ValueError(f"Failed to convert Mistral response to SSEChunk: {str(e)}") from e
