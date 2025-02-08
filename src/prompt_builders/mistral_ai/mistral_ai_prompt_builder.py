# src/prompt_builders/mistral_ai/mistral_ai_prompt_builder.py

from typing import List, Dict
from pathlib import Path
import yaml

from ...prompt_builders.base_prompt_builder import BasePromptBuilder
from ...data_models.chat_completions import TextChatMessage


class MistralAIPromptBuilder(BasePromptBuilder):
    """Prompt builder for MistralAI models.

    Placeholder implementation for handling MistralAI's specific message format.

    Attributes:
        config (Dict): Configuration loaded from prompt_builders.yaml
    """

    def __init__(self):
        """Initialize the MistralAI prompt builder."""
        super().__init__()
        self.config = self._load_config()

    async def build_chat(self, context: dict) -> List[TextChatMessage]:
        """Build chat messages for MistralAI's format.

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
        raise NotImplementedError("MistralAIPromptBuilder.build_chat() not implemented")

    async def build_text(self, context: Dict) -> str:
        """Build text prompt for MistralAI models.

        Args:
            context (dict): Dictionary containing conversation history and tools

        Returns:
            str: Formatted prompt string

        Raises:
            NotImplementedError: This method needs to be implemented
        """
        raise NotImplementedError("MistralAIPromptBuilder.build_text() not implemented")

    @staticmethod
    def _load_config() -> Dict:
        """Load MistralAI-specific configuration from YAML file.

        Returns:
            Dict: Configuration dictionary for MistralAI prompt building
        """
        config_path = Path("src/configs/prompt_builders.yaml")
        with config_path.open() as f:
            config = yaml.safe_load(f)
            return config.get('mistralai', {})