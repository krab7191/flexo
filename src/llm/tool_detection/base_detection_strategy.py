# src/llm/tool_detection/base_detection_strategy.py

from abc import ABC, abstractmethod

from src.api import SSEChunk
from src.data_models.agent import StreamContext
from src.llm.tool_detection.detection_result import DetectionResult


class BaseToolCallDetectionStrategy(ABC):
    """Abstract base class for implementing tool call detection strategies.

    This class defines the interface for strategies that detect when an LLM
    wants to make tool calls within its response stream. Implementations should
    handle parsing of SSE chunks to identify tool call patterns and maintain
    any necessary state between chunks.

    The detection process happens in three phases:
    1. Reset - Clear any accumulated state
    2. Detect - Process incoming chunks sequentially
    3. Finalize - Handle any remaining state and make final determination
    """

    @abstractmethod
    def reset(self) -> None:
        """Reset the strategy's internal state.

        This method should be called before starting a new detection sequence
        to ensure no state is carried over from previous detections.

        Implementation should clear any accumulated buffers, counters, or other
        state variables used during detection.
        """
        pass

    @abstractmethod
    async def detect_chunk(
            self,
            sse_chunk: SSEChunk,
            context: StreamContext
    ) -> DetectionResult:
        """Process an SSE chunk to detect potential tool calls.

        Args:
            sse_chunk (SSEChunk): The chunk of streaming response to analyze.
                Contains delta updates and choice information.
            context (StreamContext): Contextual information about the current
                stream, including conversation history and available tools.

        Returns:
            DetectionResult: The result of analyzing this chunk, including
                whether a tool call was detected and any extracted tool
                call information.
        """
        pass

    @abstractmethod
    async def finalize_detection(
            self,
            context: StreamContext
    ) -> DetectionResult:
        """Complete the detection process and handle any remaining state.

        This method should be called after all chunks have been processed
        to handle any buffered content or partial tool calls that may need
        final processing.

        Args:
            context (StreamContext): Contextual information about the current
                stream, including conversation history and available tools.

        Returns:
            DetectionResult: Final detection result, including any tool calls
                that were detected from accumulated state.
        """
        pass
