# src/prompt_builders/anthropic/anthropic_prompt_builder.py

from typing import List, Dict
from pathlib import Path
import yaml

from ...prompt_builders.base_prompt_builder import BasePromptBuilder
from ...data_models.chat_completions import TextChatMessage


class AnthropicPromptBuilder(BasePromptBuilder):
    """Prompt builder for Anthropic (Claude) models.

    Placeholder implementation for handling Anthropic's specific message format.

    Attributes:
        config (Dict): Configuration loaded from prompt_builders.yaml
    """

    def __init__(self):
        """Initialize the Anthropic prompt builder."""
        super().__init__()
        self.config = self._load_config()

    async def build_chat(self, context: dict) -> List[TextChatMessage]:
        """Build chat messages for Anthropic's format.

        Args:
            context (dict): Dictionary containing:
                - conversation_history (List[TextChatMessage]): Existing messages
                - tool_definitions (List[ToolDefinition]): Available tools
                - Additional context-specific data

        Returns:
            List[TextChatMessage]: Modified message list with tool information.

        Raises:
            NotImplementedError: This method needs to be implemented
        """
        raise NotImplementedError("AnthropicPromptBuilder.build_chat() not implemented")

    async def build_text(self, context: Dict) -> str:
        """Build text prompt for Anthropic models.

        Args:
            context (dict): Dictionary containing conversation history and tools

        Returns:
            str: Formatted prompt string

        Raises:
            NotImplementedError: This method needs to be implemented
        """
        raise NotImplementedError("AnthropicPromptBuilder.build_text() not implemented")

    @staticmethod
    def _load_config() -> Dict:
        """Load Anthropic-specific configuration from YAML file.

        Returns:
            Dict: Configuration dictionary for Anthropic prompt building
        """
        config_path = Path("src/configs/prompt_builders.yaml")
        with config_path.open() as f:
            config = yaml.safe_load(f)
            return config.get('anthropic', {})
