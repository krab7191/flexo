# src/llm/adapters/xai_adapter.py

import os
import logging
from typing import AsyncGenerator, List, Optional

from openai import AsyncOpenAI
from src.llm.adapters.base_vendor_adapter import BaseVendorAdapter
from src.data_models.tools import Tool
from src.data_models.chat_completions import TextChatMessage
from src.api.sse_models import SSEChunk, SSEChoice, SSEDelta, SSEToolCall, SSEFunction

logger = logging.getLogger(__name__)


class XAIAdapter(BaseVendorAdapter):
    """Adapter for interacting with xAI's API.

    Utilizes the OpenAI client for compatibility with xAI API endpoints.
    Supports streaming responses and converts them to standardized SSE chunks.

    Attributes:
        model_name (str): The model identifier being served
        api_key (str): xAI API key for authentication
        base_url (str): URL of the xAI API server
        client (AsyncOpenAI): Configured OpenAI-compatible client for xAI
    """

    def __init__(
            self,
            model_name: str,
            base_url: str = "https://api.x.ai/v1",
            api_key: str = None,
            **default_params
    ):
        """Initialize the xAI adapter.

        Args:
            model_name (str): Name of the xAI model to use
            base_url (str): URL of the xAI API server
            api_key (str): xAI API key for authentication
            **default_params: Additional parameters for generation (temperature etc.)
        """
        self.model_name = model_name
        self.base_url = base_url

        # Get API key from environment or parameter
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("xAI API key is required. Provide as parameter or set `XAI_API_KEY` environment variable.")

        self.default_params = default_params

        # Configure OpenAI-compatible client for X.AI
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        logger.info(f"Initialized xAI adapter for model: {self.model_name}")
        logger.debug(f"Using X.AI server at: {self.base_url}")
        logger.debug(f"Default parameters: {default_params}")

    async def gen_chat_sse_stream(
            self,
            messages: List[TextChatMessage],
            tools: Optional[List[Tool]] = None,
            **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate streaming chat completion.

        Uses xAI's chat completions endpoint with streaming enabled.

        Args:
            messages (List[TextChatMessage]): List of chat messages
            tools (Optional[List[Tool]]): Optional tools/functions definitions
            **kwargs: Additional parameters to override defaults

        Yields:
            SSEChunk: Standardized chunks of the streaming response
        """
        try:
            # Convert messages to OpenAI format
            openai_messages = [msg.model_dump() for msg in messages]

            # Prepare request payload
            request_params = {
                "model": self.model_name,
                "messages": openai_messages,
                "stream": True,
                **self.default_params,
                **kwargs
            }

            # Add tools if provided
            if tools:
                request_params["tools"] = [tool.model_dump() for tool in tools]
                request_params["tool_choice"] = "auto"

            # Stream response
            async for chunk in await self.client.chat.completions.create(**request_params):
                yield self._convert_to_sse_chunk(chunk)

        except Exception as e:
            logger.error(f"Error in xAI chat stream: {str(e)}", exc_info=True)
            raise RuntimeError(f"xAI chat completion failed: {str(e)}") from e

    async def gen_sse_stream(
            self,
            prompt: str,
            **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate streaming completion from a text prompt.

        For xAI, this simply converts the text prompt to a chat message and calls gen_chat_sse_stream.

        Args:
            prompt (str): Input text prompt
            **kwargs: Additional parameters to override defaults

        Yields:
            SSEChunk: Standardized chunks of the streaming response
        """
        # Convert the prompt to a single user message
        messages = [{"role": "user", "content": prompt}]

        # Use the chat completions endpoint
        async for chunk in self.gen_chat_sse_stream(messages, **kwargs):
            yield chunk

    def _convert_to_sse_chunk(self, raw_chunk) -> SSEChunk:
        """Convert xAI API response chunk to standardized SSE format.

        Args:
            raw_chunk: Raw chunk from xAI API

        Returns:
            SSEChunk: Standardized chunk format
        """
        try:
            choices = []

            # Handle chat completion format
            for choice in raw_chunk.choices:
                tool_calls = None

                # Handle tool calls if present
                if hasattr(choice.delta, 'tool_calls') and choice.delta.tool_calls:
                    tool_calls = []
                    for tc in choice.delta.tool_calls:
                        function = None
                        if tc.function:
                            function = SSEFunction(
                                name=tc.function.name or "",
                                arguments=tc.function.arguments or ""
                            )
                        tool_calls.append(SSEToolCall(
                            index=tc.index or 0,
                            id=tc.id,
                            type=tc.type or "function",
                            function=function
                        ))

                choices.append(SSEChoice(
                    index=choice.index,
                    delta=SSEDelta(
                        role=choice.delta.role if hasattr(choice.delta, 'role') else None,
                        content=choice.delta.content if hasattr(choice.delta, 'content') else None,
                        tool_calls=tool_calls
                    ),
                    finish_reason=choice.finish_reason
                ))

            return SSEChunk(
                id=raw_chunk.id,
                object=raw_chunk.object,
                created=raw_chunk.created,
                model=raw_chunk.model,
                choices=choices
            )

        except Exception as e:
            logger.error(f"Error converting xAI chunk: {raw_chunk}", exc_info=True)
            raise ValueError(f"Failed to convert xAI response: {str(e)}") from e
