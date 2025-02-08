# src/llm/tool_detection/vendor_detection_strategy.py

import json
import logging
from src.api import SSEChunk
from src.data_models.agent import StreamContext
from src.data_models.chat_completions import ToolCall, FunctionDetail
from src.llm.tool_detection import BaseToolCallDetectionStrategy
from src.llm.tool_detection.detection_result import DetectionResult, DetectionState


class VendorToolCallDetectionStrategy(BaseToolCallDetectionStrategy):
    """A strategy for detecting tool calls using vendor-provided metadata in SSE chunks.

    This strategy processes tool calls by accumulating function names and arguments
    across multiple Server-Sent Events (SSE) chunks. It relies on vendor-specific
    metadata in the chunks to identify tool calls and their completion status.

    Attributes:
        found_complete_call (bool): Flag indicating if a complete tool call was found.
        collected_tool_calls (List[ToolCall]): List of fully collected tool calls.
        partial_name (str): Buffer for accumulating function name.
        partial_args (str): Buffer for accumulating function arguments.

    Example:
        ```python
        detector = VendorToolCallDetectionStrategy()

        async for chunk in stream:
            result = await detector.detect_chunk(chunk, context)
            if result.state == DetectionState.COMPLETE_MATCH:
                tool_calls = result.tool_calls
                # Process the complete tool calls
        ```
    """

    def __init__(self):
        """Initialize the vendor tool call detection strategy."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initializing VendorToolCallDetectionStrategy")
        self.found_complete_call = None
        self.collected_tool_calls = None
        self.partial_name = None
        self.partial_args = None
        self.reset()

    def reset(self) -> None:
        """Reset all stored tool call information to initial state.

        This method clears all accumulated data and resets flags, preparing the
        detector for processing a new stream of chunks.
        """
        self.logger.debug("Resetting detector state")
        self.partial_name = None
        self.partial_args = ""  # Accumulates streamed arguments
        self.collected_tool_calls = []
        self.found_complete_call = False

    async def detect_chunk(
            self,
            sse_chunk: SSEChunk,
            context: StreamContext
    ) -> DetectionResult:
        """Process an SSE chunk for tool call detection.

        Analyzes the chunk for tool call information using vendor-provided metadata.
        Accumulates partial tool calls across multiple chunks until a complete call
        is detected.

        Args:
            sse_chunk (SSEChunk): The chunk of streaming content to process.
            context (StreamContext): Context information for the current stream.

        Returns:
            DetectionResult: Result of processing the chunk, including detection state
                and any content or tool calls found.

        Note:
            This method maintains state between calls detect_chunk() to properly handle tool calls
            that span multiple chunks. It relies on the finish_reason field to
            determine when a tool call is complete.
        """
        tool_call_data = None
        if not sse_chunk.choices:
            return DetectionResult(state=DetectionState.NO_MATCH)

        delta = sse_chunk.choices[0].delta
        finish_reason = sse_chunk.choices[0].finish_reason

        text_content = delta.content if delta.content else None

        # Check if tool call data is present in this chunk
        tool_calls = delta.tool_calls if delta.tool_calls else None

        if tool_calls:
            tool_call_data = tool_calls[0]  # Assuming index 0 for simplicity
            function_name = tool_call_data.function.name if tool_call_data.function else None
            arguments = tool_call_data.function.arguments if tool_call_data.function else None

            # If this chunk contains a function name, store it
            if function_name:
                self.partial_name = function_name

            # If arguments are being streamed, accumulate them
            if arguments:
                self.partial_args += arguments

        # If finish_reason indicates the tool call is complete, finalize it
        if finish_reason == "tool_calls":
            if self.partial_name:
                try:
                    parsed_args = json.loads(self.partial_args) if self.partial_args else {}
                except json.JSONDecodeError:
                    self.logger.warning("Failed to parse arguments as JSON: %s", self.partial_args[:50])
                    parsed_args = {"_malformed": self.partial_args}

                tool_call = ToolCall(
                    id=(tool_call_data and tool_call_data.id) or "call_generated",
                    function=FunctionDetail(
                        name=self.partial_name,
                        arguments=parsed_args
                    )
                )
                self.collected_tool_calls.append(tool_call)
                self.found_complete_call = True

                return DetectionResult(
                    state=DetectionState.COMPLETE_MATCH,
                    tool_calls=[tool_call],
                    content=text_content
                )

        # If we're still collecting tool call data, return PARTIAL_MATCH
        if self.partial_name or self.partial_args:
            return DetectionResult(
                state=DetectionState.PARTIAL_MATCH,
                content=text_content
            )

        # Otherwise, just return NO_MATCH and pass the text through
        return DetectionResult(
            state=DetectionState.NO_MATCH,
            content=text_content
        )

    async def finalize_detection(self, context: StreamContext) -> DetectionResult:
        """Finalize the detection process and handle any accumulated tool calls.

        This method is called at the end of the SSE stream to process any remaining
        tool call data and return final results.

        Args:
            context (StreamContext): Context information for the current stream.

        Returns:
            DetectionResult: Final result of the detection process, including any
                complete tool calls or remaining content.

        Note:
            This method handles cleanup of partial tool calls that were never
            completed due to stream termination.
        """
        self.logger.debug("Finalizing detection")
        if self.found_complete_call:
            self.logger.debug("Returning %d collected tool calls", len(self.collected_tool_calls))
            return DetectionResult(
                state=DetectionState.COMPLETE_MATCH,
                tool_calls=self.collected_tool_calls
            )

        if self.partial_name or self.partial_args:
            self.logger.debug("Incomplete tool call data at stream end")
            return DetectionResult(state=DetectionState.NO_MATCH)

        self.logger.debug("No tool calls to finalize")
        return DetectionResult(state=DetectionState.NO_MATCH)
