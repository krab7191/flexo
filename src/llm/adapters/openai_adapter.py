# src/llm/adapters/openai_adapter.py

import os
import logging
from openai import AsyncOpenAI
from typing import AsyncGenerator, List, Optional
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from src.data_models.tools import Tool
from src.llm.adapters import BaseVendorAdapter
from src.data_models.chat_completions import TextChatMessage
from src.api import SSEChunk, SSEChoice, SSEDelta, SSEToolCall, SSEFunction

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseVendorAdapter):
    """Adapter for interacting with OpenAI's API.

    This class implements the BaseVendorAdapter interface for OpenAI's chat models,
    handling authentication, request formatting, and response streaming. It converts
    OpenAI-specific response formats into standardized SSE chunks for consistent
    handling across different LLM providers.

    Attributes:
        api_key (str): OpenAI API key loaded from environment variables.
        client (AsyncOpenAI): Authenticated OpenAI client instance.
        model_name (str): The OpenAI model identifier (e.g., "gpt-4").
        default_params (dict): Default parameters for OpenAI API calls.
    """

    def __init__(self, model_name: str, **default_params):
        """Initialize the OpenAI Adapter with model configuration.

        Args:
            model_name (str): The identifier of the OpenAI model to use (e.g., "gpt-4").
            **default_params: Additional parameters to include in all API calls.
                Common parameters include temperature, max_tokens, etc.

        Raises:
            ValueError: If OPENAI_API_KEY environment variable is not set.
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing OpenAI API key. Set the OPENAI_API_KEY environment variable.")

        self.client = AsyncOpenAI()
        self.client.api_key = self.api_key

        self.model_name = model_name
        self.default_params = default_params
        logger.info(f"OpenAI Adapter initialized with model: {self.model_name}")
        logger.debug(f"Default parameters configured: {default_params}")

    async def gen_sse_stream(
            self,
            prompt: str,
            **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate SSE stream from a single text prompt.

        Converts a single prompt into a chat message and streams the response.

        Args:
            prompt (str): The text prompt to send to the model.
            **kwargs: Additional parameters to override defaults for this request.

        Yields:
            SSEChunk: Standardized chunks of the streaming response.

        Raises:
            RuntimeError: If the streaming request fails.
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
            messages (List[TextChatMessage]): List of chat messages for context.
            tools (Optional[List[Tool]]): List of tools available to the model.
            **kwargs: Additional parameters to override defaults for this request.

        Yields:
            SSEChunk: Standardized chunks of the streaming response.

        Raises:
            RuntimeError: If the OpenAI API request fails.
        """
        openai_messages = [msg.model_dump() for msg in messages]
        logger.debug(f"Processing chat stream request with {len(messages)} messages")

        request_payload = {
            "model": self.model_name,
            "messages": openai_messages,
            "stream": True,
            **self.default_params,
            **kwargs,
        }

        if tools:
            logger.debug(f"Adding {len(tools)} tools to request")
            request_payload["tools"] = [tool.model_dump() for tool in tools]
            request_payload["tool_choice"] = "auto"

        try:
            logger.debug("Initiating OpenAI streaming request")
            async for chunk in await self.client.chat.completions.create(**request_payload):
                yield await self._convert_to_sse_chunk(chunk)
        except Exception as e:
            logger.error(f"Error in OpenAI streaming: {str(e)}", exc_info=True)
            raise RuntimeError(f"OpenAI API streaming failed: {str(e)}") from e

    async def _convert_to_sse_chunk(self, raw_chunk: ChatCompletionChunk) -> SSEChunk:
        """Convert OpenAI's response chunk to standardized SSE format.

        Transforms OpenAI's ChatCompletionChunk into the application's
        standardized SSEChunk format, handling all possible response fields
        including tool calls, content, and metadata.

        Args:
            raw_chunk (ChatCompletionChunk): Raw chunk from OpenAI's API.

        Returns:
            SSEChunk: Standardized chunk format for consistent handling.

        Raises:
            ValueError: If chunk conversion fails due to unexpected format.
        """
        try:
            logger.debug(f"Converting chunk ID: {raw_chunk.id}")
            choices = []
            for choice in raw_chunk.choices:
                tool_calls = None
                if choice.delta.tool_calls:
                    tool_calls = []
                    for tc in choice.delta.tool_calls:
                        function = None
                        if tc.function:
                            function = SSEFunction(
                                name="" if tc.function.name is None else tc.function.name,
                                arguments="" if tc.function.arguments is None else tc.function.arguments
                            )

                        tool_calls.append(SSEToolCall(
                            index=tc.index if tc.index is not None else 0,
                            id=tc.id,
                            type=tc.type if tc.type else "function",
                            function=function
                        ))

                delta = SSEDelta(
                    role=choice.delta.role,
                    content=choice.delta.content,
                    tool_calls=tool_calls,
                    refusal=choice.delta.refusal
                )

                choices.append(SSEChoice(
                    index=choice.index,
                    delta=delta,
                    logprobs=choice.logprobs,
                    finish_reason=choice.finish_reason
                ))

            return SSEChunk(
                id=raw_chunk.id,
                object=raw_chunk.object,
                created=raw_chunk.created,
                model=raw_chunk.model,
                service_tier=raw_chunk.service_tier,
                system_fingerprint=raw_chunk.system_fingerprint,
                choices=choices
            )

        except Exception as e:
            logger.error(f"Error converting OpenAI chunk: {raw_chunk}", exc_info=True)
            raise ValueError(f"Failed to convert OpenAI response to SSEChunk: {str(e)}") from e
