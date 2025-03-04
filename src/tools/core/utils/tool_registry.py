# tools/core/utils/tool_registry.py

import logging
from typing import Dict, Optional, List

from src.data_models.tools import Tool
from src.tools.core.base_tool import BaseTool
from src.tools.core.utils.tool_discovery import discover_custom_tools
from src.tools.core.utils.tool_builder import create_tool_from_config


class ToolRegistry:
    """Registry for dynamically loading and storing tool instances.

    This class provides a centralized registry for managing tool instances.
    It supports registering both regular and hidden tools, loading tools from
    configuration files, and retrieving tools by name.

    Attributes:
        tools: A dictionary mapping tool names to their respective BaseTool instances.
        hidden_tools: A dictionary mapping hidden tool names to their BaseTool instances.
    """

    def __init__(self):
        """Initialize an empty ToolRegistry."""
        self.tools: Dict[str, BaseTool] = {}
        self.hidden_tools: Dict[str, BaseTool] = {}
        self.registration_results = {
            "successful": [],
            "hidden_successful": [],
            "failed": []
        }
        self.logger = logging.getLogger(self.__class__.__name__)

    def register_tool(self, name: str, tool: BaseTool, hidden: bool = False):
        """Register a tool instance with the registry.

        Args:
            name: The unique identifier for the tool.
            tool: The BaseTool instance to register.
            hidden: Whether to register the tool as hidden. Defaults to False.
                   Hidden tools are not exposed in tool_definitions but can be
                   accessed directly by name.

        Raises:
            ValueError: If a tool with the given name is already registered.
        """
        if name in self.tools or name in self.hidden_tools:
            self.logger.error(f"Tool registration error: Tool with name '{name}' is already registered.")
            self.registration_results["failed"].append((name, "Already registered"))
            raise ValueError(f"Tool with name '{name}' is already registered.")

        if hidden:
            self.hidden_tools[name] = tool
            self.registration_results["hidden_successful"].append(name)
            self.logger.debug(f"Registered hidden tool: {name}")
        else:
            self.tools[name] = tool
            self.registration_results["successful"].append(name)
            self.logger.debug(f"Registered tool: {name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            The BaseTool instance if found, None otherwise.
        """
        return self.tools.get(name)

    def get_hidden_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a hidden tool by name.

        Args:
            name: The name of the hidden tool to retrieve.

        Returns:
            The BaseTool instance if found, None otherwise.
        """
        return self.hidden_tools.get(name)

    def get_tool_definitions(self) -> List[Tool]:
        """Get definitions for all registered non-hidden tools.

        Returns:
            List[Tool]: A list of tool definitions for all visible tools in the
                registry
        """
        tool_definitions = []
        for tool_name, tool in self.tools.items():
            try:
                # Extra validation to prevent runtime errors
                if not hasattr(tool, 'name') or tool.name is None:
                    self.logger.error(f"Tool has missing or None name property: {tool.__class__.__name__}")
                    continue

                definition = tool.get_definition()
                tool_definitions.append(definition)
            except Exception as e:
                self.logger.error(f"Error getting definition for tool '{tool_name}': {str(e)}", exc_info=True)

        return tool_definitions

    def load_from_config(self, tool_configs: List):
        """Load tools from a configuration dictionary.

        This method processes a configuration dictionary that defines tools,
        creates instances of those tools, and registers them in the registry.

        Args:
            `tool_configs`: A dictionary containing tool configurations.

        Raises:
            Exception: If there is an error creating a tool instance.
        """
        tool_count = len(tool_configs)
        self.logger.info(f"\nStarting tool registration process for {tool_count} tool(s)...")
        self.logger.debug(f"Processing configuration: {tool_configs}")

        # Clear previous results if any
        self.registration_results = {
            "successful": [],
            "hidden_successful": [],
            "failed": []
        }

        # Discover available tools
        discovered_tools = discover_custom_tools()

        # Process each tool configuration
        for i, tool_def in enumerate(tool_configs, 1):
            tool_name = tool_def.get("name", "<unnamed>")
            hidden = tool_def.get("hidden", False)
            tool_type = "hidden" if hidden else "public"

            self.logger.debug(f"Processing {tool_type} tool '{tool_name}' ({i}/{tool_count})")

            try:
                instance = create_tool_from_config(tool_def, discovered_tools=discovered_tools)
                self.register_tool(tool_name, instance, hidden)
            except Exception as e:
                error_msg = f"Failed to load tool '{tool_name}': {e}"
                self.logger.error(error_msg)
                self.registration_results["failed"].append((tool_name, str(e)))

        # Log the summary after processing all tools
        self.log_registration_summary()

    def log_registration_summary(self):
        """Log a summary of the tool registration process with improved formatting."""
        successful_count = len(self.registration_results["successful"])
        hidden_count = len(self.registration_results["hidden_successful"])
        failed_count = len(self.registration_results["failed"])
        total_count = successful_count + hidden_count + failed_count

        # Create a header with divider
        header = "\n\n" + "=" * 60 + "\n"
        header += f"TOOL REGISTRATION SUMMARY ({total_count} TOTAL)\n"
        header += "=" * 60
        self.logger.info(header)

        # Status section
        status = f"\n  SUCCESS: {successful_count} public tool(s)"
        if hidden_count > 0:
            status += f", {hidden_count} hidden tool(s)"
        if failed_count > 0:
            status += f"\n  FAILED:  {failed_count} tool(s)"
        self.logger.info(status)

        # Detailed sections
        if successful_count > 0:
            self.logger.info("\nREGISTERED PUBLIC TOOLS:")
            for i, name in enumerate(sorted(self.registration_results["successful"]), 1):
                self.logger.info(f"  {i}. {name}")

        if hidden_count > 0:
            self.logger.info("\nREGISTERED HIDDEN TOOLS:")
            for i, name in enumerate(sorted(self.registration_results["hidden_successful"]), 1):
                self.logger.info(f"  {i}. {name}")

        if failed_count > 0:
            self.logger.info("\nFAILED REGISTRATIONS:")
            for i, (name, error) in enumerate(self.registration_results["failed"], 1):
                self.logger.info(f"  {i}. {name}")
                self.logger.info(f"     Error: {error}")

        # Final divider
        self.logger.info("\n" + "=" * 60 + "\n")
