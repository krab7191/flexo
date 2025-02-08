# src/data_models/prompt_models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Union

from src.data_models.tools import Tool
from src.data_models.chat_completions import TextChatMessage


class PromptPayload(BaseModel):
    """Container for prompt generation input data.

    This class encapsulates the necessary data for generating prompts,
    including conversation history and available tools.

    Attributes:
        conversation_history (List[TextChatMessage]): The complete conversation
            history as a chronological list of messages between user and assistant.
        tool_definitions (Optional[List[Tool]]): List of tools that are available
            for the model to use in its responses. Defaults to None if no tools
            are available.
    """

    conversation_history: List[TextChatMessage] = Field(
        ...,
        description="The conversation history as a list of messages"
    )
    tool_definitions: Optional[List[Tool]] = Field(
        None,
        description="Available tools that can be used by the model"
    )


class PromptBuilderOutput(BaseModel):
    """Output container for prompt builder results.

    Stores either a text prompt or a list of chat messages, providing
    a unified interface for different types of prompt outputs.

    Attributes:
        text_prompt (Optional[str]): A single string containing the generated
            prompt. Mutually exclusive with chat_messages.
        chat_messages (Optional[List[TextChatMessage]]): A list of chat messages
            representing the prompt. Mutually exclusive with text_prompt.
    """

    text_prompt: Optional[str] = None
    chat_messages: Optional[List[TextChatMessage]] = None

    def get_output(self) -> Union[str, List[TextChatMessage]]:
        """Retrieve the prompt output in its appropriate format.

        Returns either the text prompt or chat messages, depending on which
        was set during initialization.

        Returns:
            Union[str, List[TextChatMessage]]: Either a string containing the
                text prompt or a list of chat messages.

        Raises:
            ValueError: If neither text_prompt nor chat_messages was set.
        """
        if self.text_prompt is not None:
            return self.text_prompt
        if self.chat_messages is not None:
            return self.chat_messages
        raise ValueError("Neither text_prompt nor chat_messages was set")
