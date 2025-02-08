# src/tools/tool_registry.py

import logging
from typing import Dict, List

from src.data_models.tools import Tool
from src.tools.base_tool import BaseTool
from src.tools.implementations import RAGTool, WeatherTool, WikipediaTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing and accessing system tools.

    Handles initialization, registration, and access to tools, supporting
    both regular and hidden tools with configuration management.

    Attributes:
        tools (Dict[str, BaseTool]): Dictionary of registered tools.
        hidden_tools (Dict[str, BaseTool]): Dictionary of hidden tools.
        config (Dict): Configuration settings for all tools.

    Example:
        ```python
        config = {
            "rag_tool": {...},
            "weather_tool": {...}
        }
        registry = ToolRegistry(config)
        weather_tool = registry.get_tool("weather")
        ```
    """

    def __init__(self, config: Dict):
        """Initialize the ToolRegistry with configuration settings.

        Args:
            config (Dict): Configuration dictionary containing settings for all tools.
        """
        logger.debug("Initializing ToolRegistry")
        self.tools: Dict[str, BaseTool] = {}
        self.hidden_tools: Dict[str, BaseTool] = {}
        self.config = config
        logger.debug("Configuration received: %s", list(config.keys()))
        self._register_tools()

    def _register_tools(self):
        """Initialize and register all system tools."""
        logger.debug("Starting tool registration process")

        # Initialize weather tool
        weather_config = self.config.get("weather_tool")
        if weather_config:
            logger.debug("Initializing Weather tool with config: %s", weather_config)
            try:
                weather_tool = WeatherTool(config=weather_config)
                self.register_tool(weather_tool)
                logger.debug("Weather tool successfully registered")
            except Exception as e:
                logger.error("Failed to initialize Weather tool: %s", str(e))
                raise

        # Initialize wikipedia tool
        weather_config = self.config.get("wikipedia_tool")
        if weather_config:
            logger.debug("Initializing wikipedia tool with config: %s", weather_config)
            try:
                weather_tool = WikipediaTool(config=weather_config)
                self.register_tool(weather_tool)
                logger.debug("wikipedia tool successfully registered")
            except Exception as e:
                logger.error("Failed to initialize wikipedia tool: %s", str(e))
                raise

        # Initialize RAG tool (disabled by default)
        # rag_config = self.config.get("rag_tool")
        # if rag_config:
        #     logger.debug("Initializing RAG tool with config: %s", rag_config)
        #     try:
        #         rag_tool = RAGTool(config=rag_config)
        #         self.register_tool(rag_tool)
        #         logger.debug("RAG tool successfully registered")
        #     except Exception as e:
        #         logger.error("Failed to initialize RAG tool: %s", str(e))
        #         raise

        logger.info("Tool registration complete. Registered tools: %s",
                    ", ".join(self.tools.keys()))

    def register_tool(self, tool: BaseTool):
        """Register a new tool in the registry.

        Args:
            tool (BaseTool): Tool instance to register.
        """
        logger.debug("Registering tool: %s", tool.name)
        if tool.name in self.tools:
            logger.warning("Tool %s already registered, overwriting", tool.name)
        self.tools[tool.name] = tool
        logger.debug("Tool %s successfully registered", tool.name)

    def get_tool(self, name: str) -> BaseTool:
        """Retrieve a registered tool by name.

        Args:
            name (str): Name of the tool to retrieve.

        Returns:
            BaseTool: The requested tool instance or None if not found.
        """
        tool = self.tools.get(name)
        if tool:
            logger.debug("Retrieved tool: %s", name)
        else:
            logger.warning("Tool not found: %s", name)
        return tool

    def get_hidden_tool(self, name: str) -> BaseTool:
        """Retrieve a hidden tool by name.

        Args:
            name (str): Name of the hidden tool to retrieve.

        Returns:
            BaseTool: The requested hidden tool instance or None if not found.
        """
        tool = self.hidden_tools.get(name)
        if tool:
            logger.debug("Retrieved hidden tool: %s", name)
        else:
            logger.warning("Hidden tool not found: %s", name)
        return tool

    def get_tool_definitions(self) -> List[Tool]:
        """Get definitions for all registered non-hidden tools.

        Returns:
            List[ToolDefinition]: List of tool definitions.
        """
        logger.debug("Retrieving tool definitions for %d tools", len(self.tools))
        definitions = [tool.get_definition() for tool in self.tools.values()]
        logger.debug("Retrieved definitions for tools: %s",
                     ", ".join(tool.name for tool in self.tools.values()))
        return definitions
