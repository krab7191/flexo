# src/llm/adapters/anthropic_adapter.py

import os
import time
import logging
from typing import AsyncGenerator, List, Optional, Union, Dict, Any

from anthropic import AsyncAnthropic
from src.data_models.tools import Tool
from src.llm.adapters.base_vendor_adapter import BaseVendorAdapter
from src.api import SSEChunk, SSEChoice, SSEDelta, SSEToolCall, SSEFunction
from src.data_models.chat_completions import (
    UserMessage,
    SystemMessage,
    AssistantMessage,
    ToolMessage,
    TextChatMessage,
    UserTextContent,
    UserImageURLContent,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# Content Conversion Functions
# --------------------------------------------------
def convert_content(
    content: Union[str, List[Union[UserTextContent, UserImageURLContent, Dict[str, Any]]]]
) -> List[Dict[str, Any]]:
    """Convert message content into Anthropic content blocks.

    Args:
        content (Union[str, List[Union[UserTextContent, UserImageURLContent, Dict[str, Any]]]]):
            Either a simple text string or a list of content blocks. The list can contain:

            - `UserTextContent`: A text content block.
            - `UserImageURLContent`: An image content block.
            - `Dict`: A dictionary representing other content types (e.g., for assistant messages).

    Returns:
        List[Dict[str, Any]]: A list of content blocks in Anthropic-compatible format.

    Raises:
        ValueError: If the content is neither a string nor a list, or if a block is of an invalid type.
    """
    if isinstance(content, str):
        return [{"type": "text", "text": content}]

    if not isinstance(content, list):
        raise ValueError(f"Content must be a string or a list, got {type(content)}")

    blocks = []
    for block in content:
        if isinstance(block, UserTextContent):
            blocks.append({"type": "text", "text": block.text})
        elif isinstance(block, UserImageURLContent):
            blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": block.image_url.get("url", ""),
                }
            })
        elif isinstance(block, dict):
            block_type = block.get("type")
            if block_type == "text":
                blocks.append({"type": "text", "text": block.get("text", "")})
            elif block_type == "image_url":
                blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": block.get("image_url", {}).get("url", ""),
                    }
                })
            else:
                # Pass through other block types (e.g., tool_use or tool_result)
                blocks.append(block)
        else:
            raise ValueError(f"Invalid content block type: {type(block)}")

    return blocks


# --------------------------------------------------
# Tool Conversion Functions
# --------------------------------------------------
def convert_tool_to_anthropic_format(tool: Tool) -> dict:
    """Convert our Tool model to Anthropic's format.

    Args:
        tool (Tool): The tool to convert.

    Returns:
        dict: A dictionary representing the tool in Anthropic's expected format.
    """
    input_schema = tool.function.parameters.model_dump() if tool.function.parameters else {}
    return {
        "name": tool.function.name,
        "description": tool.function.description or "",
        "input_schema": input_schema,
    }


# --------------------------------------------------
# Message Conversion Functions
# --------------------------------------------------
def convert_user_message(msg: UserMessage) -> Dict[str, Any]:
    """Convert a UserMessage to Anthropic format.

    Args:
        msg (UserMessage): The user message to convert.

    Returns:
        Dict[str, Any]: The converted message in Anthropic format.
    """
    return {"role": "user", "content": convert_content(msg.content)}


def convert_assistant_message(msg: AssistantMessage) -> Dict[str, Any]:
    """Convert an AssistantMessage to Anthropic format.

    Args:
        msg (AssistantMessage): The assistant message to convert.

    Returns:
        Dict[str, Any]: The converted message in Anthropic format.
    """
    blocks = []
    if msg.content:
        blocks.extend(convert_content(msg.content))
    if msg.refusal:
        blocks.append({"type": "text", "text": msg.refusal})
    if msg.tool_calls:
        for call in msg.tool_calls:
            blocks.append({
                "type": "tool_use",
                "id": call.id,
                "name": call.function.name,
                "input": call.function.arguments,
            })
    return {"role": "assistant", "content": blocks}


def convert_tool_message(msg: ToolMessage) -> Dict[str, Any]:
    """Convert a ToolMessage to Anthropic format.

    Note:
        Tool results must be returned as user messages for Anthropic.

    Args:
        msg (ToolMessage): The tool message to convert.

    Returns:
        Dict[str, Any]: The converted tool message in Anthropic format.
    """
    return {
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": msg.tool_call_id,
            "content": msg.content,
        }],
    }


def convert_messages_to_anthropic(messages: List[TextChatMessage]) -> Dict[str, Any]:
    """Convert a list of messages to Anthropic's format.

    Args:
        messages (List[TextChatMessage]): A list of chat messages.

    Returns:
        Dict[str, Any]: A dictionary containing the converted messages and an optional system prompt.
    """
    system_prompt = None
    converted = []

    for msg in messages:
        if isinstance(msg, SystemMessage):
            system_prompt = (system_prompt + "\n" + msg.content) if system_prompt else msg.content
        elif isinstance(msg, UserMessage):
            converted.append(convert_user_message(msg))
        elif isinstance(msg, AssistantMessage):
            converted.append(convert_assistant_message(msg))
        elif isinstance(msg, ToolMessage):
            converted.append(convert_tool_message(msg))
        else:
            raise ValueError(f"Unsupported message type: {type(msg)}")

    result = {"messages": converted}
    if system_prompt:
        result["system"] = system_prompt
    return result


# --------------------------------------------------
# Anthropic Adapter
# --------------------------------------------------
class AnthropicAdapter(BaseVendorAdapter):
    """Adapter for interacting with Anthropic's API."""

    def __init__(self, model_name: str, **default_params):
        """Initialize Anthropic Adapter.

        Args:
            model_name (str): The name of the model to use.
            **default_params: Additional default parameters for the adapter.

        Raises:
            ValueError: If the Anthropic API key is missing.
        """
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing Anthropic API key. Set the ANTHROPIC_API_KEY environment variable."
            )
        self.client = AsyncAnthropic(api_key=self.api_key)
        self.model_name = model_name
        self.default_params = default_params
        logger.info(f"Anthropic Adapter initialized with model: {self.model_name}")

    async def gen_sse_stream(
        self, prompt: str, **kwargs
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate an SSE stream from a text prompt.

        Args:
            prompt (str): The text prompt to generate an SSE stream for.
            **kwargs: Additional keyword arguments for generation.

        Yields:
            AsyncGenerator[SSEChunk, None]: A generator yielding SSEChunk objects.
        """
        async for chunk in self.gen_chat_sse_stream([{"role": "user", "content": prompt}], **kwargs):
            yield chunk

    async def gen_chat_sse_stream(
        self,
        messages: List[TextChatMessage],
        tools: Optional[List[Tool]] = None,
        **kwargs,
    ) -> AsyncGenerator[SSEChunk, None]:
        """Generate a streaming chat response.

        Args:
            `messages` (List[TextChatMessage]): A list of chat messages.
            `tools` (Optional[List[Tool]], optional): A list of Tool objects. Defaults to None.
            `**kwargs`: Additional keyword arguments for generation.

        Yields:
            AsyncGenerator[SSEChunk, None]: A generator yielding SSEChunk objects.
        """
        request_payload = {
            "model": self.model_name,
            "max_tokens": self.default_params.get("max_tokens", 1024),
            "stream": True,
            **self.default_params,
            **kwargs,
            **convert_messages_to_anthropic(messages),
        }

        if tools:
            anthropic_tools = [convert_tool_to_anthropic_format(tool) for tool in tools]
            request_payload["tools"] = anthropic_tools
            request_payload["tool_choice"] = {"type": "auto"}

        try:
            stream = await self.client.messages.create(**request_payload)
            async for event in stream:
                yield await self._convert_to_sse_chunk(event)
        except Exception as e:
            logger.error(f"Error in Anthropic streaming: {str(e)}", exc_info=True)
            raise RuntimeError(f"Anthropic API streaming failed: {str(e)}") from e

    async def _convert_to_sse_chunk(self, raw_event: Any) -> SSEChunk:
        """Convert an Anthropic event to an SSEChunk.

        Args:
            `raw_event` (Any): The raw event from the Anthropic API.

        Returns:
            SSEChunk: The converted SSEChunk object.

        Raises:
            ValueError: If conversion of the event fails.
        """
        try:
            event_type = raw_event.type
            current_time = int(time.time())

            match event_type:
                case "content_block_start":
                    content_block = raw_event.content_block
                    if content_block.type == "text":
                        delta = SSEDelta(
                            role="assistant",
                            content=getattr(content_block, "text", ""),
                        )
                    elif content_block.type == "tool_use":
                        delta = SSEDelta(
                            role="assistant",
                            content="",
                            tool_calls=[SSEToolCall(
                                id=content_block.id,
                                type="function",
                                function=SSEFunction(name=content_block.name, arguments=""),
                            )],
                        )
                    else:
                        delta = SSEDelta(role="assistant", content="")
                    choice = SSEChoice(index=raw_event.index, delta=delta)
                    return SSEChunk(
                        id=f"content_block_start_{raw_event.index}",
                        object="chat.completion.chunk",
                        created=current_time,
                        model=self.model_name,
                        choices=[choice],
                    )

                case "content_block_delta":
                    delta_info = raw_event.delta
                    if delta_info.type == "text_delta":
                        delta = SSEDelta(
                            role="assistant",
                            content=delta_info.text,
                        )
                    elif delta_info.type == "input_json_delta":
                        delta = SSEDelta(
                            role="assistant",
                            content="",
                            tool_calls=[SSEToolCall(
                                type="function",
                                function=SSEFunction(
                                    name="",
                                    arguments=delta_info.partial_json,
                                ),
                            )],
                        )
                    else:
                        delta = SSEDelta(role="assistant", content="")
                    choice = SSEChoice(index=raw_event.index, delta=delta)
                    return SSEChunk(
                        id=f"delta_{raw_event.index}",
                        object="chat.completion.chunk",
                        created=current_time,
                        model=self.model_name,
                        choices=[choice],
                    )

                case "content_block_stop":
                    delta = SSEDelta(role="assistant", content="")
                    choice = SSEChoice(index=raw_event.index, delta=delta)
                    return SSEChunk(
                        id=f"block_stop_{raw_event.index}",
                        object="chat.completion.chunk",
                        created=current_time,
                        model=self.model_name,
                        choices=[choice],
                    )

                case "message_delta":
                    delta = SSEDelta(role="assistant", content="")
                    choice = SSEChoice(
                        index=0,
                        delta=delta,
                        finish_reason=getattr(raw_event.delta, "stop_reason", None),
                    )
                    return SSEChunk(
                        id="message_delta",
                        object="chat.completion.chunk",
                        created=current_time,
                        model=self.model_name,
                        choices=[choice],
                    )

                case "message_stop":
                    delta = SSEDelta(role="assistant", content="")
                    choice = SSEChoice(index=0, delta=delta)
                    return SSEChunk(
                        id="message_stop",
                        object="chat.completion.chunk",
                        created=current_time,
                        model=self.model_name,
                        choices=[choice],
                    )

                case _:
                    delta = SSEDelta(role="assistant", content="")
                    choice = SSEChoice(index=0, delta=delta)
                    return SSEChunk(
                        id=f"unknown_{event_type}",
                        object="chat.completion.chunk",
                        created=current_time,
                        model=self.model_name,
                        choices=[choice],
                    )

        except Exception as e:
            logger.error(f"Error converting Anthropic event: {raw_event}", exc_info=True)
            raise ValueError(f"Failed to convert Anthropic response to SSEChunk: {str(e)}") from e
