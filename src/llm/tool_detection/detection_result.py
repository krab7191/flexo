# src/llm/tool_detection/detection_result.py

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel

from src.api import SSEChunk
from src.data_models.chat_completions import ToolCall


class DetectionState(str, Enum):
    """Enumeration of possible tool call detection states.

    Represents the different states a tool call detection can be in during
    the processing of streaming chunks.

    Attributes:
        NO_MATCH: No tool call pattern was detected in the current content.
        PARTIAL_MATCH: A potential tool call was detected but is incomplete.
        COMPLETE_MATCH: A complete and valid tool call was detected.
    """
    NO_MATCH = "no_match"
    PARTIAL_MATCH = "partial_match"
    COMPLETE_MATCH = "complete_match"


class DetectionResult(BaseModel):
    """Container for tool call detection results.

    Encapsulates the result of processing an SSE chunk for tool calls,
    including the detection state, any found tool calls, accumulated content,
    and the original chunk.

    Attributes:
        state (DetectionState): The current state of tool call detection.
            Indicates whether a tool call was found and if it's complete.
        tool_calls (Optional[List[ToolCall]]): List of tool calls found in the
            content. Only present when state is COMPLETE_MATCH.
        content (Optional[str]): Accumulated text content from the chunk,
            excluding any tool call syntax.
        sse_chunk (Optional[SSEChunk]): The original SSE chunk that was
            processed, preserved for reference or further processing.
    """
    state: DetectionState
    tool_calls: Optional[List[ToolCall]] = None
    content: Optional[str] = None
    sse_chunk: Optional[SSEChunk] = None
