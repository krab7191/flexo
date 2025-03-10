# src/prompt_builders/xai/xai_prompt_builder.py

import yaml
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from src.prompt_builders import BasePromptBuilder
from src.data_models.chat_completions import SystemMessage
from src.prompt_builders.prompt_models import PromptPayload, PromptBuilderOutput


class XAIPromptBuilder(BasePromptBuilder):
    """A prompt builder specialized for xAI's chat completion models.

    This class handles the construction of prompts for xAI models, with special
    handling for tool definitions and system messages. It loads configuration from
    a YAML file and supports embedding tool information into the conversation history.

    The builder primarily supports chat completions, following OpenAI-compatible format
    which aligns with xAI's API. Text completions are not supported.

    Attributes:
        config (Dict): Configuration dictionary loaded from prompt_builders.yaml.
            Expected to contain 'system_prompt' with 'header' and 'tool_instructions'.

    Example:
        ```python
        builder = XAIPromptBuilder()
        payload = PromptPayload(
            conversation_history=history,
            tool_definitions=tools
        )
        output = await builder.build_chat(payload)
        # Use output.chat_messages with xAI API
        ```
    """

    def __init__(self):
        """Initialize the xAI prompt builder.

        Loads configuration from the prompt_builders.yaml file and sets up logging.
        Raises FileNotFoundError if the config file is not found.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initializing XAIPromptBuilder")
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
                with xAI's chat completion API.

        Note:
            If the first message in history is a system message, tool information
            will be prepended to it. Otherwise, a new system message will be created.
        """
        conversation_history = payload.conversation_history
        tool_definitions = payload.tool_definitions or []

        if not tool_definitions:
            self.logger.debug("No tool definitions provided, returning original history")
            return PromptBuilderOutput(chat_messages=conversation_history)

        tool_names = [tool.function.name for tool in tool_definitions]

        tool_section_header = self.config['system_prompt']['header'].format(
            tools=", ".join(tool_names),
            date=datetime.now().strftime('%Y-%m-%d')
        )
        tool_instructions = self.config['system_prompt']['tool_instructions']
        tool_info = await self._build_system_content(tool_definitions, tool_section_header, tool_instructions)
        modified_history = conversation_history.copy()

        if conversation_history and isinstance(conversation_history[0], SystemMessage):
            existing_content = conversation_history[0].content
            modified_history[0] = SystemMessage(
                content=f"{existing_content}\n\n## Tools Available:\n\n{tool_info}\n\n"
            )
        else:
            system_msg = SystemMessage(content=f"## Tools Available:\n\n{tool_info}")
            modified_history.insert(0, system_msg)

        self.logger.debug("Returning modified history with %d messages", len(modified_history))
        return PromptBuilderOutput(chat_messages=modified_history)

    async def _build_system_content(self, tool_definitions, header, instructions):
        """Build the system content that includes tool definitions.

        Args:
            tool_definitions (List): List of tool definition objects
            header (str): Header text for the tools section
            instructions (str): General instructions for using tools

        Returns:
            str: Formatted system content with tool information
        """
        tool_descriptions = []

        for tool in tool_definitions:
            function = tool.function
            name = function.name
            description = function.description or "No description available"
            parameters = function.parameters.model_dump() if function.parameters else {}

            # Format parameter information
            param_info = ""
            if parameters and "properties" in parameters:
                properties = parameters["properties"]
                required = parameters.get("required", [])
                param_info = "\nParameters:\n"

                for param_name, param_details in properties.items():
                    req_status = "(required)" if param_name in required else "(optional)"
                    param_desc = param_details.get("description", "No description")
                    param_type = param_details.get("type", "any")
                    param_info += f"- {param_name} {req_status}: {param_desc} (Type: {param_type})\n"

            tool_descriptions.append(f"### {name}\n{description}\n{param_info}")

        formatted_tools = "\n\n".join(tool_descriptions)
        return f"{header}\n\n{formatted_tools}\n\n{instructions}"

    async def build_text(self, context: Dict) -> str:
        """Text completion is not supported for xAI models.

        Args:
            context (Dict): Unused context dictionary.

        Raises:
            NotImplementedError: Always raised as this method is not supported.
        """
        raise NotImplementedError(
            "xAI models use chat completions interface. Use build_chat() instead."
        )

    @staticmethod
    def _load_config() -> Dict:
        """Load the xAI-specific configuration from the prompt builders YAML file.

        Returns:
            Dict: Configuration dictionary containing Mistral-specific settings.

        Raises:
            FileNotFoundError: If the config file doesn't exist.
            yaml.YAMLError: If the config file is malformed.
        """
        config_path = Path("src/configs/prompt_builders.yaml")
        with config_path.open() as f:
            config = yaml.safe_load(f)
            return config.get('xai', {})
