# src/llm/adapters/vllm_adapter.py

import logging
from typing import AsyncGenerator, List, Optional
from openai import AsyncOpenAI

from src.data_models.tools import Tool
from src.llm.adapters import BaseVendorAdapter
from src.data_models.chat_completions import TextChatMessage
from src.api.sse_models import SSEChunk, SSEChoice, SSEDelta, SSEToolCall, SSEFunction

logger = logging.getLogger(__name__)


class VLLMAdapter(BaseVendorAdapter):
    """Adapter for interacting with locally deployed vLLM models.

    Supports both chat completions and direct prompt generation through vLLM's
    OpenAI-compatible API endpoints. Handles streaming responses and converts
    them to standardized SSE chunks.

    Attributes:
        model_name (str): The model identifier being served by vLLM
        base_url (str): URL of the vLLM server (default: http://localhost:8000/v1)
        api_key (str): API key for vLLM server authentication
        client (AsyncOpenAI): Configured OpenAI client for vLLM
    """

    def __init__(
            self,
            model_name: str,
            base_url: str = "http://localhost:8000/v1",
            api_key: str = "dummy-key",
            **default_params
    ):
        """Initialize the vLLM adapter.

        Args:
            model_name (str): Name of the model being served (e.g. "NousResearch/Llama-2-7b")
            base_url (str): URL of the vLLM server
            api_key (str): API key for authentication
            **default_params: Additional parameters for generation (temperature etc.)
        """
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.default_params = default_params

        # Configure OpenAI client for vLLM server
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

        logger.info(f"Initialized vLLM adapter for model: {self.model_name}")
        logger.debug(f"Using vLLM server at: {self.base_url}")
        logger.debug(f"Default parameters: {default_params}")

    async def gen_chat_sse_stream(
            self,
            messages: List[TextChatMessage],
            tools: Optional[List[Tool]] = None,
            **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate streaming chat completion using vLLM's chat endpoint.

        Args:
            messages (List[TextChatMessage]): List of chat messages
            tools (Optional[List[Tool]]): Optional tools/functions
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

            # Stream response from vLLM
            async for chunk in await self.client.chat.completions.create(**request_params):
                yield self._convert_to_sse_chunk(chunk)

        except Exception as e:
            logger.error(f"Error in vLLM chat stream: {str(e)}", exc_info=True)
            raise RuntimeError(f"vLLM chat completion failed: {str(e)}") from e

    async def gen_sse_stream(
            self,
            prompt: str,
            **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate streaming completion using vLLM's completions endpoint.

        Args:
            prompt (str): Input text prompt
            **kwargs: Additional parameters to override defaults

        Yields:
            SSEChunk: Standardized chunks of the streaming response
        """
        try:
            # Prepare request payload
            request_params = {
                "model": self.model_name,
                "prompt": prompt,  # vLLM completions endpoint accepts raw string prompts
                "stream": True,
                **self.default_params,
                **kwargs
            }

            logger.debug(f"Making completions request with prompt: {prompt[:50]}...")

            # Use completions endpoint directly
            async for chunk in await self.client.completions.create(**request_params):
                yield self._convert_to_sse_chunk(chunk)

        except Exception as e:
            logger.error(f"Error in vLLM completion stream: {str(e)}", exc_info=True)
            raise RuntimeError(f"vLLM completion failed: {str(e)}") from e

    def _convert_to_sse_chunk(self, raw_chunk) -> SSEChunk:
        """Convert vLLM/OpenAI response chunk to standardized SSE format.

        Args:
            raw_chunk: Raw chunk from vLLM API

        Returns:
            SSEChunk: Standardized chunk format
        """
        try:
            choices = []

            # Check if this is a text completion or chat completion by looking at the object type
            if raw_chunk.object == 'text_completion':
                # Handle text completion format
                for choice in raw_chunk.choices:
                    choices.append(SSEChoice(
                        index=choice.index,
                        delta=SSEDelta(
                            content=choice.text,
                            role="assistant"
                        ),
                        finish_reason=choice.finish_reason
                    ))
            else:
                # Handle chat completion format
                for choice in raw_chunk.choices:
                    tool_calls = None
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
            logger.error(f"Error converting vLLM chunk: {raw_chunk}", exc_info=True)
            raise ValueError(f"Failed to convert vLLM response: {str(e)}") from e
