# src/llm/llm_factory.py

import logging
import os
from typing import Dict, Any, Type, Callable, Optional, Union, TypeVar

from .adapters.base_vendor_adapter import BaseVendorAdapter
from .adapters.watsonx.watsonx_config import WatsonXConfig
from .adapters.watsonx.ibm_token_manager import IBMTokenManager
from .adapters import (
    OpenAIAdapter,
    WatsonXAdapter,
    AnthropicAdapter,
    MistralAdapter,
    OpenAICompatAdapter,
    GrokAdapter,
)

logger = logging.getLogger(__name__)

# Type variable for adapter instances
T = TypeVar('T', bound=BaseVendorAdapter)


class LLMFactory:
    """Factory for creating and managing LLM adapters for different vendors.

    This class implements the Factory pattern to instantiate and manage different
    LLM adapters based on configuration. It maintains a singleton-like pattern
    for adapter instances and service-specific token managers.

    Attributes:
        _adapters (Dict[str, BaseVendorAdapter]): Class-level dictionary storing instantiated adapters.
        _token_manager (IBMTokenManager): Class-level token manager instance for WatsonX.
        _adapter_registry (Dict[str, Type[BaseVendorAdapter]]): Mapping of vendor names to adapter classes.
    """

    _adapters: Optional[Dict[str, BaseVendorAdapter]] = None
    _token_manager: Optional[IBMTokenManager] = None

    # Registry of standard adapter classes by vendor name
    _adapter_registry: Dict[str, Type[BaseVendorAdapter]] = {
        "openai": OpenAIAdapter,
        "anthropic": AnthropicAdapter,
        "mistral-ai": MistralAdapter,
        "xai": GrokAdapter,
        "grok": GrokAdapter,
        "openai-compat": OpenAICompatAdapter,
    }

    def __init__(self, config: Dict[str, Dict[str, Any]]):
        """Initialize the LLM Factory with configuration.

        Args:
            config (Dict[str, Dict[str, Any]]): Configuration dictionary containing model configurations.
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
    def _initialize_adapters(cls, config: Dict[str, Dict[str, Any]]) -> None:
        """Initialize adapters based on the provided configuration.

        This method creates adapter instances for each model in the config.

        Args:
            config (Dict[str, Dict[str, Any]]): Configuration dictionary for all models.

        Raises:
            ValueError: If an unknown vendor is specified or if required configuration is missing.
        """
        cls._adapters = {}
        logger.debug("Initializing LLM adapters")

        # Initialize service-specific components once if needed
        cls._initialize_service_components(config)

        # Process each model in the configuration
        for model_name, model_config in config.items():
            try:
                # Validate and extract configuration
                validated_config = cls._validate_model_config(model_name, model_config)
                vendor = validated_config["vendor"]
                model_id = validated_config["model_id"]
                adapter_params = validated_config["adapter_params"]

                # Create the adapter
                adapter = cls._create_adapter(vendor, model_id, **adapter_params)
                cls._adapters[model_name] = adapter
                logger.debug(f"Initialized {vendor} adapter for model: {model_name}")

            except Exception as e:
                logger.error(f"Failed to initialize adapter for {model_name}: {str(e)}")
                # Add context to the exception
                raise ValueError(f"Adapter initialization failed for {model_name}") from e

    @classmethod
    def _initialize_service_components(cls, config: Dict[str, Dict[str, Any]]) -> None:
        """Initialize service-specific components required by adapters.

        Args:
            config (Dict[str, Dict[str, Any]]): Configuration dictionary for all models.

        Raises:
            ValueError: If initialization of a service component fails.
        """
        # Initialize WatsonX Token Manager if needed
        if any("watsonx" in model_config.get("vendor", "") for model_config in config.values()):
            try:
                cls._token_manager = IBMTokenManager(api_key=WatsonXConfig.CREDS.get('apikey'))
                logger.debug("Initialized WatsonX Token Manager")
            except Exception as e:
                logger.error(f"Failed to initialize WatsonX Token Manager: {str(e)}")
                raise ValueError("Failed to initialize WatsonX Token Manager") from e

    @classmethod
    def _create_adapter(cls, vendor: str, model_id: str, **kwargs) -> BaseVendorAdapter:
        """Create an adapter instance based on vendor and model ID.

        Args:
            vendor (str): The vendor identifier.
            model_id (str): The model identifier.
            **kwargs: Additional parameters for the adapter.

        Returns:
            BaseVendorAdapter: The created adapter instance.

        Raises:
            ValueError: If the vendor is unknown or if adapter creation fails.
        """
        # Handle special case for WatsonX
        if "watsonx" in vendor:
            if cls._token_manager is None:
                raise ValueError("IBMTokenManager was not initialized for WatsonX models.")
            return WatsonXAdapter(
                model_name=model_id,
                token_manager=cls._token_manager,
                **kwargs
            )

        # Handle special case for X.AI/Grok
        if vendor in ["xai", "grok"]:
            # Get API key from config or environment
            api_key = kwargs.pop("api_key", None) or os.getenv("XAI_API_KEY")
            if not api_key:
                logger.warning(f"No XAI API key found for model {model_id}. Set XAI_API_KEY environment variable.")

            # Use the standard X.AI base URL unless overridden
            base_url = kwargs.pop("base_url", "https://api.x.ai/v1")

            return GrokAdapter(
                model_name=model_id,
                api_key=api_key,
                base_url=base_url,
                **kwargs
            )

        # Handle standard adapters from registry
        adapter_class = cls._adapter_registry.get(vendor)
        if adapter_class:
            return adapter_class(model_name=model_id, **kwargs)

        # If we get here, the vendor is unknown
        raise ValueError(f"Unknown vendor '{vendor}'")

    @staticmethod
    def _validate_model_config(model_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate model configuration and extract adapter parameters.

        Args:
            model_name (str): The name of the model.
            config (Dict[str, Any]): The model configuration.

        Returns:
            Dict[str, Any]: Validated configuration with extracted parameters.

        Raises:
            ValueError: If required fields are missing.
        """
        # Check required fields
        required_fields = ["vendor", "model_id"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' for model '{model_name}'")

        # Extract and return relevant configuration
        return {
            "vendor": config["vendor"],
            "model_id": config["model_id"],
            "adapter_params": {k: v for k, v in config.items() if k not in ["vendor", "model_id"]}
        }

    @classmethod
    def get_adapter(cls, model_name: str, config: Optional[Dict[str, Dict[str, Any]]] = None) -> BaseVendorAdapter:
        """Retrieve an adapter instance for a specific model with lazy initialization if needed.

        Args:
            model_name (str): Name of the model to retrieve the adapter for.
            config (Optional[Dict[str, Dict[str, Any]]]): Configuration to use if factory is not initialized.

        Returns:
            BaseVendorAdapter: The adapter instance for the specified model.

        Raises:
            ValueError: If adapters haven't been initialized or if the
                requested model adapter is not found.
        """
        # Lazy initialization if needed
        if cls._adapters is None:
            if not config:
                raise ValueError("Adapters have not been initialized. Initialize the factory with a config first.")
            cls._initialize_adapters(config)

        adapter = cls._adapters.get(model_name)
        if adapter:
            logger.debug(f"Retrieved adapter for model: {model_name}")
            return adapter
        else:
            raise ValueError(f"Adapter for model '{model_name}' not found.")

    @classmethod
    def has_adapter(cls, model_name: str) -> bool:
        """Check if an adapter is available for a model without raising exceptions.

        Args:
            model_name (str): The name of the model to check.

        Returns:
            bool: True if the adapter exists, False otherwise.
        """
        return cls._adapters is not None and model_name in cls._adapters

    @classmethod
    def list_available_models(cls) -> list:
        """List all available model names that have initialized adapters.

        Returns:
            list: List of model names with initialized adapters.

        Raises:
            ValueError: If adapters haven't been initialized.
        """
        if cls._adapters is None:
            raise ValueError("Adapters have not been initialized.")

        return list(cls._adapters.keys())
