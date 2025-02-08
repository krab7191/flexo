# src/prompt_builders/granite/granite_prompt_builder.py

import yaml
from pathlib import Path
from jinja2 import Template
from typing import Optional
from datetime import datetime

from src.data_models.tools import Tool
from src.prompt_builders.base_prompt_builder import BasePromptBuilder
from src.prompt_builders.prompt_models import PromptPayload, PromptBuilderOutput
from src.data_models.chat_completions import TextChatMessage, SystemMessage, UserMessage


class GranitePromptBuilder(BasePromptBuilder):
    """Prompt builder for the Granite model architecture.

    This class handles the construction of prompts and chat messages specifically
    formatted for Granite models, with support for tool definitions and
    context-aware message formatting.

    Attributes:
        config (Dict): Configuration loaded from prompt_builders.yaml
        template (Template): Jinja2 template for text generation prompts
    """
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize the Granite prompt builder.

        Args:
            template_dir (Optional[str]): Custom directory for template files.
                If None, uses default directory 'src/prompt_builders/granite'.
        """
        super().__init__()
        self.config = self._load_config()
        self.template = self._load_template(template_dir) if template_dir else self._load_template()

    async def build_chat(self, payload: PromptPayload) -> PromptBuilderOutput:
        """Build chat messages with tools embedded in system message.

        Creates or modifies the system message to include tool definitions
        while preserving the existing conversation structure.

        Args:
            payload (PromptPayload): The structured input containing conversation history,
                                   tool definitions, and other context-specific data

        Returns:
            PromptBuilderOutput: Contains the modified message list with tool information
        """
        conversation_history = payload.conversation_history
        tool_definitions = payload.tool_definitions or []

        # If no tools, return history as is
        if not tool_definitions:
            return PromptBuilderOutput(chat_messages=conversation_history)

        # Generate tool information
        tool_names = [tool.function.name for tool in tool_definitions]
        tool_section_header = self.config['system_prompt']['header'].format(
            tools=", ".join(tool_names),
            date=datetime.now().strftime('%Y-%m-%d')
        )
        tool_instructions = self.config['system_prompt']['tool_instructions']

        tool_info = await self._build_system_content(tool_definitions, tool_section_header, tool_instructions)

        # Create modified history list
        modified_history = conversation_history.copy()

        if conversation_history and isinstance(conversation_history[0], SystemMessage):
            # Prepend tool info to existing system message
            existing_content = conversation_history[0].content
            modified_history[0] = SystemMessage(
                content=f"{existing_content}\n<|start_of_role|>tools<|end_of_role|>{tool_info}<|end_of_text|>"
            )
        else:
            # Create new system message with tool info and prepend to history
            system_msg = SystemMessage(content=tool_info)
            modified_history.insert(0, system_msg)

        return PromptBuilderOutput(chat_messages=modified_history)

    async def build_text(self, payload: PromptPayload) -> PromptBuilderOutput:
        """Build text prompt using Granite-specific template.

        Constructs a complete prompt string using the Jinja2 template,
        incorporating conversation history and tool definitions.

        Args:
            payload (PromptPayload): The structured input containing conversation history,
                                   tool definitions, and other context-specific data

        Returns:
            str: Formatted prompt string ready for text generation
        """
        conversation_history = payload.conversation_history
        tool_definitions = payload.tool_definitions or []

        # Preprocess conversation history to flatten user message content
        processed_history = [self._preprocess_message(msg).model_dump() for msg in conversation_history]

        # Format tool definitions for template
        formatted_tools = [
            self._format_tool_for_template(tool)
            for tool in tool_definitions
        ] if tool_definitions else None

        # Prepare template variables
        template_vars = {
            'messages': processed_history,
            'tools': formatted_tools,
            'tools_in_user_message': False,
            'add_generation_prompt': True,
            'date_string': datetime.now().strftime("%d %b %Y"),
            'tool_instructions': self.config['system_prompt']['tool_instructions']
        }

        return PromptBuilderOutput(text_prompt=self.template.render(**template_vars))

    @staticmethod
    def _preprocess_message(message: TextChatMessage) -> TextChatMessage:
        """Preprocess message for Granite format."""
        if not isinstance(message, UserMessage):
            return message

        if isinstance(message.content, list):
            # Extract text content from array of content objects
            text_contents = []
            for content in message.content:
                if getattr(content, 'type', None) == 'text':
                    text_contents.append(content.text)

            # Create new UserMessage with flattened content
            return UserMessage(content=" ".join(text_contents))

        return message

    @staticmethod
    def _format_tool_for_template(tool: Tool) -> dict:
        """Format tool definition for Granite template usage."""
        return {
            "name": tool.function.name,
            "description": tool.function.description,
            "parameters": {
                "type": "object",
                "properties": tool.function.parameters.properties,
                "required": tool.function.parameters.required
            }
        }

    @staticmethod
    def _load_config() -> dict:
        """Load Granite-specific configuration from YAML file."""
        config_path = Path("src/configs/prompt_builders.yaml")
        with config_path.open() as f:
            config = yaml.safe_load(f)
            return config.get('watsonx-granite')

    @staticmethod
    def _load_template(template_dir: str = "src/prompt_builders/watsonx/granite") -> Template:
        """Load Jinja2 template for Granite prompt generation."""
        template_path = Path(template_dir) / "granite-3.1-8b.jinja"
        with open(template_path) as f:
            return Template(f.read())
