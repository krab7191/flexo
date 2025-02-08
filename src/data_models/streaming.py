# src/data_models/streaming.py

from typing import Optional
from pydantic import BaseModel, Field, computed_field


class PatternMatchResult(BaseModel):
    """Result of a pattern matching operation in stream processing.

    This class encapsulates all possible outcomes and data from a pattern
    matching operation, including matched patterns, processed output,
    and any errors that occurred.

    Attributes:
        output (Optional[str]): The processed text after pattern matching.
            None if no processing occurred.
        pattern_name (Optional[str]): Name of the matched pattern.
            None if no pattern was matched.
        matched (bool): Whether a pattern was successfully matched.
            Defaults to False.
        text_with_tool_call (Optional[str]): Complete text containing the tool call
            if a match was found. None otherwise.
        tool_call_message (Optional[str]): Message associated with the tool call.
            None if no tool call was detected.
        error (Optional[str]): Error message if pattern matching failed.
            None if processing was successful.

    Example:
        ```python
        result = PatternMatchResult(
            output="Processed text",
            pattern_name="MistralPattern0",
            matched=True,
            text_with_tool_call="Complete tool call text",
            tool_call_message="Tool call detected"
        )
        ```
    """
    output: Optional[str] = Field(
        default=None,
        description="The processed output text after pattern matching"
    )
    pattern_name: Optional[str] = Field(
        default=None,
        description="The name of the matched pattern"
    )
    matched: bool = Field(
        default=False,
        description="Indicates whether a pattern was successfully matched"
    )
    text_with_tool_call: Optional[str] = Field(
        default=None,
        description="The complete text containing the tool call if matched"
    )
    tool_call_message: Optional[str] = Field(
        default=None,
        description="Any message associated with the tool call"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if pattern matching failed"
    )


class StreamConfig(BaseModel):
    """Configuration settings for stream processing operations.

    This class defines the configuration parameters that control how streaming
    data is processed, buffered, and chunked. It uses Pydantic for validation
    and provides several factory methods for common configurations.

    Attributes:
        buffer_size (int): Size of the buffer in characters. Zero disables buffering.
            Must be greater than or equal to 0.
        chunk_separator (str): String used to separate chunks when combining buffered content.
        strip_whitespace (bool): Whether to remove whitespace from chunks before processing.
        buffering_enabled (bool): Computed field indicating if buffering is active.

    Example:
        ```python
        # Create a default configuration
        config = StreamConfig.create_default()

        # Create a buffered configuration
        buffered_config = StreamConfig.create_buffered(buffer_size=100)

        # Create configuration with custom separator
        custom_config = StreamConfig.create_with_separator(
            buffer_size=50,
            separator="\\n"
        )
        ```
    """
    buffer_size: int = Field(
        default=0,
        description="Size of the buffer in characters. Set to 0 to disable buffering.",
        ge=0
    )
    chunk_separator: str = Field(
        default="",
        description="Separator to use between chunks when combining buffered content."
    )
    strip_whitespace: bool = Field(
        default=False,
        description="Whether to strip whitespace from chunks before processing."
    )

    @computed_field
    @property
    def buffering_enabled(self) -> bool:
        """Indicates whether buffering is enabled based on buffer size."""
        return self.buffer_size > 0

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "buffer_size": 10,
                    "chunk_separator": "\n",
                    "strip_whitespace": True
                }
            ]
        }
    }

    @classmethod
    def create_default(cls) -> "StreamConfig":
        """Create a StreamConfig with default values."""
        return cls()

    @classmethod
    def create_buffered(cls, buffer_size: int) -> "StreamConfig":
        """Create a StreamConfig with specified buffer size."""
        return cls(buffer_size=buffer_size)

    @classmethod
    def create_with_separator(
            cls,
            buffer_size: int = 0,
            separator: str = "\n"
    ) -> "StreamConfig":
        """Create a StreamConfig with specified buffer size and separator."""
        return cls(
            buffer_size=buffer_size,
            chunk_separator=separator
        )
