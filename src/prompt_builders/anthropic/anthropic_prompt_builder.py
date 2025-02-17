# src/prompt_builders/anthropic/anthropic_prompt_builder.py

import yaml
import logging
from pathlib import Path
from typing import Dict
from datetime import datetime

from src.prompt_builders import BasePromptBuilder
from src.data_models.chat_completions import SystemMessage
from src.prompt_builders.prompt_models import PromptPayload, PromptBuilderOutput


class AnthropicPromptBuilder(BasePromptBuilder):
    """A prompt builder specialized for Anthropic chat completion models.

    This class handles the construction of prompts for Anthropic models,
    with special handling for tool definitions and system messages. It loads
    configuration from a YAML file and supports embedding tool information into
    the conversation history.

    Example:
        ```python
        builder = AnthropicPromptBuilder()
        payload = PromptPayload(
            conversation_history=history,
            tool_definitions=tools
        )
        output = await builder.build_chat(payload)
        ```
    """

    def __init__(self):
        """Initialize the Anthropic prompt builder.

        Loads configuration from the prompt_builders.yaml file and sets up logging.
        Raises FileNotFoundError if the config file is not found.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initializing AnthropicPromptBuilder")
        super().__init__()
        self.config = self._load_config()

    async def build_chat(self, payload: PromptPayload) -> PromptBuilderOutput:
        """Build a chat completion prompt with optional tool definitions.

        Constructs a prompt by potentially modifying the conversation history to
        include tool information. If tools are defined, they are added to or merged
        with the system message.

        Args:
            payload (PromptPayload): Contains conversation history and optional tool
                definitions. History should be a list of message objects, and tool
                definitions should be a list of tool specification objects.

        Returns:
            PromptBuilderOutput: Contains the modified chat messages ready for use
                with Anthropic's chat completion API.

        Note:
            If the first message in history is a system message, tool information
            will be prepended to it. Otherwise, a new system message will be created.
        """
        conversation_history = payload.conversation_history
        tool_definitions = payload.tool_definitions or []

        if not tool_definitions:
            self.logger.debug("No tool definitions provided, returning original history")
            return PromptBuilderOutput(chat_messages=conversation_history)

        # Extract tool names from the tool definitions.
        tool_names = [tool.function.name for tool in tool_definitions]

        # Build a header for the tool section using our config.
        tool_section_header = self.config['system_prompt']['header'].format(
            tools=", ".join(tool_names),
            date=datetime.now().strftime('%Y-%m-%d')
        )
        tool_instructions = self.config['system_prompt']['tool_instructions']

        # Build the tool information block.
        tool_info = await self._build_system_content(tool_definitions, tool_section_header, tool_instructions)
        modified_history = conversation_history.copy()

        if conversation_history and isinstance(conversation_history[0], SystemMessage):
            existing_content = conversation_history[0].content
            modified_history[0] = SystemMessage(
                content=f"## tools:\n\n{existing_content}\n{tool_info}\n\n"
            )
        else:
            system_msg = SystemMessage(content=tool_info)
            modified_history.insert(0, system_msg)

        self.logger.debug("Returning modified history with %d messages", len(modified_history))
        return PromptBuilderOutput(chat_messages=modified_history)

    async def build_text(self, context: Dict) -> str:
        """Text completion is not supported for Anthropic models.

        Args:
            context (Dict): Unused context dictionary.

        Raises:
            NotImplementedError: Always raised as this method is not supported.
        """
        raise NotImplementedError(
            "Anthropic models primarily use chat completions. Use build_chat() instead."
        )

    @staticmethod
    def _load_config() -> Dict:
        """Load the Anthropic-specific configuration from the prompt builders YAML file.

        Returns:
            Dict: Configuration dictionary containing Anthropic-specific settings.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            yaml.YAMLError: If the config file is malformed.
        """
        config_path = Path("src/configs/prompt_builders.yaml")
        with config_path.open() as f:
            config = yaml.safe_load(f)
            return config.get('anthropic', {})
