# src/prompt_builders/base_prompt_builder.py

from typing import List
from abc import ABC, abstractmethod

from src.data_models.tools import Tool
from src.data_models.chat_completions import TextChatMessage
from src.prompt_builders.prompt_models import PromptPayload, PromptBuilderOutput


class BasePromptBuilder(ABC):
    @abstractmethod
    async def build_text(self, payload: PromptPayload) -> PromptBuilderOutput:
        """
        Build prompt string for text generation endpoint.

        Args:
            payload (PromptPayload): The structured input containing conversation history,
                                   tool definitions, and other context-specific data.

        Returns:
            str: Formatted prompt string for text generation
        """
        pass

    @abstractmethod
    async def build_chat(self, payload: PromptPayload) -> PromptBuilderOutput:
        """
        Build message list for chat completions endpoint.

        Args:
            payload (PromptPayload): The structured input containing conversation history,
                                   tool definitions, and other context-specific data.

        Returns:
            PromptBuilderOutput: Contains either text_prompt or chat_messages for the LLM
        """
        pass

    @staticmethod
    async def _build_system_content(tool_definitions: List[Tool], header: str, instructions: str) -> str:
        """Build system message content incorporating tool information.

        Args:
            tool_definitions (List[Tool]): List of tool definitions to include
            header (str): Header text for the system message
            instructions (str): Instructions text for tool usage

        Returns:
            str: Formatted system message content with tool information

        Note:
            Should only be called when tool_definitions is non-empty.
        """
        tool_sections = []
        for tool in tool_definitions:
            tool_str = (
                f"Use the function '{tool.function.name}' to: {tool.function.description}\n"
                f"{tool.function.parameters.model_dump_json()}\n"
            )
            tool_sections.append(tool_str)

        return f"{header}\n\n{instructions}\n\n" + "\n".join(tool_sections)

    @staticmethod
    def _format_conversation_history(
            messages: List[TextChatMessage],
            include_roles: bool = True
    ) -> str:
        """
        Helper method to format conversation history as a string.

        Args:
            messages: List of chat messages to format
            include_roles: Whether to include role labels in the output

        Returns:
            str: Formatted conversation history
        """
        formatted = []
        for msg in messages:
            if include_roles:
                formatted.append(f"{msg.role}: {msg.content}")
            else:
                formatted.append(msg.content)
        return "\n\n".join(formatted)
