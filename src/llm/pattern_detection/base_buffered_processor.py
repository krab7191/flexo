# src/llm/pattern_detection/base_buffered_processor.py

from abc import abstractmethod
from src.data_models.streaming import PatternMatchResult


class BaseBufferedProcessor:
    """Base class for buffered text processors.

    This abstract base class implements common buffering logic for streaming text
    processing. Subclasses must implement process_chunk_impl to define specific
    matching behavior.

    Attributes:
        `tool_call_message`: Message to include when a tool call is detected.
        `trailing_buffer_original`: Buffer containing text carried over from previous chunks.

    Args:
        `tool_call_message`: Optional message to use when a tool call is detected.
            Defaults to "Tool call detected."
    """

    def __init__(self, tool_call_message: str = "Tool call detected."):
        self.tool_call_message = tool_call_message
        self.trailing_buffer_original = ""

    def reset_states(self):
        """Resets the processor's internal state.

        Clears the trailing buffer and resets any internal state to initial values.
        Should be called before starting to process a new stream of text.
        """
        self.trailing_buffer_original = ""

    async def process_chunk(self, chunk: str) -> PatternMatchResult:
        """Processes a chunk of text with buffering.

        Combines the new chunk with any trailing text from previous chunks and
        delegates the actual processing to process_chunk_impl.

        Args:
            `chunk`: The new text chunk to process.

        Returns:
            `PatternMatchResult` containing the processed output and any match information.

        ``` python title="Example usage"
        processor = MyProcessor()
        result = await processor.process_chunk("some text")
        print(result.output)  # some text
        ```
        """
        # Combine the trailing buffer with new chunk
        combined_original = self.trailing_buffer_original + chunk

        # Let the subclass handle the matching logic on combined_original.
        result, new_trailing = self.process_chunk_impl(combined_original)

        # Update the trailing buffer with what's left
        self.trailing_buffer_original = new_trailing
        return result

    async def flush_buffer(self) -> PatternMatchResult:
        """Flushes any remaining text in the trailing buffer.

        Should be called after processing the final chunk to handle any remaining
        buffered text.

        Returns:
            `PatternMatchResult` containing any remaining buffered text.

        ``` python title="Example usage"
        processor = MyProcessor()
        result = await processor.flush_buffer()
        print(len(result.output))  # 0
        ```
        """
        from src.data_models.streaming import PatternMatchResult
        result = PatternMatchResult()
        if self.trailing_buffer_original:
            result.output = self.trailing_buffer_original
            self.trailing_buffer_original = ""
        return result

    @abstractmethod
    def process_chunk_impl(self, combined_original: str):
        """Processes combined text to find pattern matches.

        This abstract method must be implemented by subclasses to define specific
        pattern matching behavior.

        Args:
            `combined_original`: Text to process, including any trailing text from
                previous chunks.

        Returns:
            A tuple containing:

                - `PatternMatchResult`: Result object with match information and
                    processed text.
                - `str`: Any trailing text to carry over to the next chunk.
        """
        pass
