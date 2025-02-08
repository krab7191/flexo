# src/prompt_builders/llama/llama_prompt_builder.py

from typing import Optional
from datetime import datetime
from jinja2 import Template
import yaml
from pathlib import Path

from src.prompt_builders.base_prompt_builder import BasePromptBuilder
from src.prompt_builders.prompt_models import PromptPayload, PromptBuilderOutput
from src.data_models.chat_completions import TextChatMessage, SystemMessage, UserMessage
from src.data_models.tools import Tool


class LlamaPromptBuilder(BasePromptBuilder):
    """Prompt builder for the Llama model architecture.

    This class handles the construction of prompts and chat messages specifically
    formatted for Llama models, with support for tool definitions and
    context-aware message formatting.

    Attributes:
        config (Dict): Configuration loaded from prompt_builders.yaml.
        template (Template): Jinja2 template for text generation prompts.

    Example:
        ```python
        builder = LlamaPromptBuilder()

        # Build chat messages
        output = await builder.build_chat(PromptPayload(
            conversation_history=history,
            tool_definitions=tools
        ))

        # Build text prompt
        output = await builder.build_text(PromptPayload(
            conversation_history=history,
            tool_definitions=tools
        ))
        ```
    """
    def __init__(self, template_dir: Optional[str] = None):
        """Initialize the Llama prompt builder.

        Args:
            template_dir (Optional[str]): Custom directory for template files.
                If None, uses default directory 'src/prompt_builders/llama'.
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

        if not tool_definitions:
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
            modified_history[0] = SystemMessage(content=f"{tool_info}\n{existing_content}")
        else:
            system_msg = SystemMessage(content=tool_info)
            modified_history.insert(0, system_msg)

        return PromptBuilderOutput(chat_messages=modified_history)

    async def build_text(self, payload: PromptPayload) -> PromptBuilderOutput:
        """Build text prompt using Llama-specific template.

        Constructs a complete prompt string using the Jinja2 template,
        incorporating conversation history, tool definitions, and model-specific
        tokens.

        Args:
            payload (PromptPayload): The structured input containing conversation history,
                                   tool definitions, and other context-specific data

        Returns:
            PromptBuilderOutput: Contains the formatted text prompt for generation
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
            'bos_token': self.config['tokens']['begin_text'],
            'tool_instructions': self.config['system_prompt']['tool_instructions']
        }

        return PromptBuilderOutput(text_prompt=self.template.render(**template_vars))

    @staticmethod
    def _preprocess_message(message: TextChatMessage) -> TextChatMessage:
        """Preprocess message for Llama format."""
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
    def _load_config() -> dict:
        """Load Llama-specific configuration from YAML file."""
        config_path = Path("src/configs/prompt_builders.yaml")
        with config_path.open() as f:
            config = yaml.safe_load(f)
            return config.get('watsonx-llama')

    @staticmethod
    def _load_template(template_dir: str = "src/prompt_builders/watsonx/llama") -> Template:
        """Load Jinja2 template for Llama prompt generation."""
        template_path = Path(template_dir) / "llama-3.3-70b.jinja"
        with open(template_path) as f:
            return Template(f.read())

    @staticmethod
    def _format_tool_for_template(tool: Tool) -> dict:
        """Format tool definition for Llama template usage."""
        return {
            "name": tool.function.name,
            "description": tool.function.description,
            "parameters": {
                "type": "object",
                "properties": tool.function.parameters.properties,
                "required": tool.function.parameters.required
            }
        }
