# src/llm/llm_factory.py

import logging
from typing import Dict
from .adapters.watsonx.watsonx_config import WatsonXConfig
from .adapters.watsonx.ibm_token_manager import IBMTokenManager
from .adapters import OpenAIAdapter, WatsonXAdapter, AnthropicAdapter, MistralAdapter

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating and managing LLM adapters for different vendors.

    This class implements the Factory pattern to instantiate and manage different
    LLM adapters based on configuration. It maintains a singleton-like pattern
    for adapter instances and the WatsonX token manager.

    Attributes:
        _adapters (Dict[str, Any]): Class-level dictionary storing instantiated adapters.
        _token_manager (IBMTokenManager): Class-level token manager instance for WatsonX.
    """

    _adapters = None
    _token_manager = None

    def __init__(self, config: Dict):
        """Initialize the LLM Factory with configuration.

        Args:
            config (Dict): Configuration dictionary containing model configurations.
                Expected format:
                {
                    "model_name": {
                        "vendor": str,
                        "model_id": str,
                        ...additional_config
                    }
                }

        Raises:
            ValueError: If the configuration format is invalid.
        """
        if LLMFactory._adapters is None:
            self._initialize_adapters(config)

    @classmethod
    def _initialize_adapters(cls, config: Dict):
        """Initialize adapters based on the provided configuration.

        This method creates adapter instances for each model in the config,
        filtering out model_id and vendor from kwargs before passing to adapter.

        Args:
            config (Dict): Configuration dictionary for all models.

        Raises:
            ValueError: If an unknown vendor is specified or if WatsonX
                token manager initialization fails.
        """
        cls._adapters = {}
        logger.debug("Initializing LLM adapters")

        # Initialize WatsonX Token Manager once
        if any("watsonx" in model_config.get("vendor", "") for model_config in config.values()):
            cls._token_manager = IBMTokenManager(api_key=WatsonXConfig.CREDS.get('apikey'))
            logger.debug("Initialized WatsonX Token Manager")

        for model_name, model_config in config.items():
            vendor = model_config.get("vendor")
            model_id = model_config.get("model_id")
            adapter_config = {k: v for k, v in model_config.items() if k not in ["vendor", "model_id"]}

            try:
                if vendor == "openai":
                    cls._adapters[model_name] = OpenAIAdapter(model_name=model_id, **adapter_config)
                    logger.debug(f"Initialized OpenAI adapter for model: {model_name}")
                elif "watsonx" in vendor:
                    if cls._token_manager is None:
                        raise ValueError("IBMTokenManager was not initialized for WatsonX models.")
                    cls._adapters[model_name] = WatsonXAdapter(
                        model_name=model_id,
                        token_manager=cls._token_manager,
                        **adapter_config
                    )
                    logger.debug(f"Initialized WatsonX adapter for model: {model_name}")
                elif vendor == "anthropic":
                    cls._adapters[model_name] = AnthropicAdapter(model_name=model_id, **adapter_config)
                    logger.debug(f"Initialized Anthropic adapter for model: {model_name}")
                elif vendor == "mistral":
                    cls._adapters[model_name] = MistralAdapter(model_name=model_id, **adapter_config)
                    logger.debug(f"Initialized Mistral adapter for model: {model_name}")
                else:
                    raise ValueError(f"Unknown vendor '{vendor}' for model '{model_name}'.")
            except Exception as e:
                logger.error(f"Failed to initialize adapter for {model_name}: {str(e)}")
                raise

    @classmethod
    def get_adapter(cls, model_name: str):
        """Retrieve an adapter instance for a specific model.

        Args:
            model_name (str): Name of the model to retrieve the adapter for.

        Returns:
            Any: The adapter instance for the specified model.

        Raises:
            ValueError: If adapters haven't been initialized or if the
                requested model adapter is not found.
        """
        if cls._adapters is None:
            raise ValueError("Adapters have not been initialized. Initialize the factory with a config first.")

        adapter = cls._adapters.get(model_name)
        if adapter:
            logger.debug(f"Retrieved adapter for model: {model_name}")
            return adapter
        else:
            raise ValueError(f"Adapter for model '{model_name}' not found.")
