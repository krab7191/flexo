# src/tools/core/tool_registry.py

import inspect
import logging
import importlib
import traceback
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Type, Optional, Callable, Set, Any, Tuple

from src.data_models.tools import Tool
from src.tools.core.base_tool import BaseTool


class ToolClass(BaseModel):
    """Information about a tool class discovered during scanning."""
    file_path: str
    module_name: str
    class_name: str
    tool_name: Optional[str] = None
    registered: bool = False
    error: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class RegistrationSummary(BaseModel):
    """A Pydantic model that provides a summary of tool registration results.

    This class encapsulates information about the tool registration process, including
    statistics about scanned files, discovered tools, and any issues encountered during
    the registration process.

    Attributes:
        `total_files_scanned` (Optional[int]): The total number of Python files scanned
            during tool discovery.
        `total_tools_found` (Optional[int]): The total number of valid tools found across
            all scanned files.
        `visible_tools` (Optional[List[str]]): Names of tools that are publicly accessible
            in the registry.
        `hidden_tools` (Optional[List[str]]): Names of tools that are registered but hidden
            from public access.
        `failed_imports` (Optional[List[str]]): List of import failures encountered during
            tool discovery.
        `initialization_failures` (List[str]): List of tools that failed to initialize
            properly.
        `unregistered_tools` (List[ToolClass]): Tool classes that were found but not registered.
        `registration_failures` (List[ToolClass]): Tool classes that had issues during registration.
    """
    total_files_scanned: Optional[int] = Field(default=0, description="Total number of files scanned.")
    total_tools_found: Optional[int] = Field(default=0, description="Total number of tools found.")
    visible_tools: Optional[List[str]] = Field(default_factory=list, description="List of tools visible.")
    hidden_tools: Optional[List[str]] = Field(default_factory=list, description="List of tools hidden.")
    failed_imports: Optional[List[str]] = Field(default_factory=list, description="List of failed imports.")
    initialization_failures: List[str] = Field(default_factory=list, description="List of initialization failures.")
    unregistered_tools: List[ToolClass] = Field(default_factory=list,
                                                description="Tool classes that were found but not registered.")
    registration_failures: List[ToolClass] = Field(default_factory=list,
                                                   description="Tool classes that had issues during registration.")

    def __str__(self) -> str:
        summary = f"""Tool Registration Summary:
├─ Files Scanned: {self.total_files_scanned}
├─ Total Tools: {self.total_tools_found}
│  ├─ Visible Tools ({len(self.visible_tools)}): {', '.join(self.visible_tools)}
│  └─ Hidden Tools ({len(self.hidden_tools)}): {', '.join(self.hidden_tools)}
└─ Issues:
   ├─ Import Failures ({len(self.failed_imports)}): {', '.join(self.failed_imports) if self.failed_imports else 'None'}
   └─ Init Failures ({len(self.initialization_failures)}): {', '.join(self.initialization_failures) if self.initialization_failures else 'None'}"""

        # Add section for unregistered tools if any exist
        if self.unregistered_tools:
            summary += "\n\n⚠️ UNREGISTERED TOOLS DETECTED ⚠️"
            for tool in self.unregistered_tools:
                summary += f"\n  - {tool.class_name} in {tool.file_path}"
                if tool.error:
                    summary += f"\n    Error: {tool.error}"

        # Add section for registration failures if any exist
        if self.registration_failures:
            summary += "\n\n❌ TOOL REGISTRATION FAILURES ❌"
            for tool in self.registration_failures:
                summary += f"\n  - {tool.class_name} in {tool.file_path}"
                if tool.error:
                    summary += f"\n    Error: {tool.error}"

        return summary


class ToolRegistry:
    """A singleton registry for managing and accessing system tools with decorator support.

    This class implements the Singleton pattern and provides functionality for:
    - Discovering tools in a specified directory
    - Registering tools via a decorator pattern
    - Managing both visible and hidden tools
    - Initializing tools with configuration
    - Providing access to registered tools

    Attributes:
        `tools` (Dict[str, BaseTool]): Dictionary of publicly accessible tools
        `hidden_tools` (Dict[str, BaseTool]): Dictionary of hidden tools
        `config` (Dict): Configuration dictionary for tool initialization
        `logger` (logging.Logger): Logger instance for the registry
    """

    _instance = None
    _registered_tool_classes: Dict[str, tuple[Type[BaseTool], bool]] = {}

    def __new__(cls, *args, **kwargs) -> 'ToolRegistry':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[Dict] = None) -> None:
        if not hasattr(self, 'initialized'):
            self.tools: Dict[str, BaseTool] = {}
            self.hidden_tools: Dict[str, BaseTool] = {}
            self.config = config or {}
            self.initialized = True
            self.logger = logging.getLogger(self.__class__.__name__)

            summary = self._discover_tools()
            failed_tool_names = set()

            if config:
                init_failures, failed_tool_names = self._initialize_registered_tools()
                summary.initialization_failures = init_failures

                # Remove failed tools from the summary's visible and hidden tools lists
                summary.visible_tools = [tool for tool in summary.visible_tools if tool not in failed_tool_names]
                summary.hidden_tools = [tool for tool in summary.hidden_tools if tool not in failed_tool_names]

                # Add failed tools to the unregistered_tools section
                for tool_name in failed_tool_names:
                    if tool_name in self._registered_tool_classes:
                        tool_class, _ = self._registered_tool_classes[tool_name]
                        class_name = tool_class.__name__
                        module_name = tool_class.__module__

                        # Convert module name to relative path
                        module_path = module_name.split('.')
                        relative_path = '/'.join(module_path) + '.py'

                        # Create a ToolClass entry for this failed tool
                        tool_info = ToolClass(
                            file_path=relative_path,
                            module_name=module_name,
                            class_name=class_name,
                            tool_name=tool_name,
                            registered=False,  # Mark as not registered since it failed to initialize
                            error=f"Failed to initialize: {next((err.split(': ', 1)[1] for err in summary.initialization_failures if err.startswith(tool_name + ':')), 'Unknown error')}"
                        )
                        summary.unregistered_tools.append(tool_info)

                # Update total tools count to exclude failed tools
                summary.total_tools_found = len(summary.visible_tools) + len(summary.hidden_tools)

            # Log at ERROR level if there are unregistered tools, failures, or initialization failures
            if (summary.unregistered_tools or summary.registration_failures or
                    summary.initialization_failures):
                self.logger.error(f" ---- TOOL REGISTRATION ISSUES FOUND! ---- \n\n{summary}\n")
            else:
                self.logger.info(f" ---- IMPORTANT! ---- \n\n{summary}\n")

    def _discover_tools(self) -> RegistrationSummary:
        """Discover and import all tool modules to trigger decorators.

        This method scans the implementations directory for Python files containing tool
        definitions. It attempts to import each file and register any tool classes that
        are properly decorated and configured.

        Returns:
            `RegistrationSummary`: A summary object containing information about the
                discovery process, including counts of found tools and any errors
                encountered.
        """
        current_dir = Path(__file__).parent.parent
        implementations_path = current_dir / 'implementations'

        # Find project root (assuming it contains src directory)
        project_root = current_dir.parent.parent
        if not (project_root / 'src').exists():
            # Try one level up if we're not at the right level
            project_root = project_root.parent

        summary = RegistrationSummary()

        if not implementations_path.exists():
            summary.initialization_failures.append("Implementations directory not found")
            return summary

        python_files = [f for f in implementations_path.glob('*.py') if not f.name.startswith('_')]
        summary.total_files_scanned = len(python_files)

        # Keep track of registered tool names before discovery
        registered_tools_before = set(self._registered_tool_classes.keys())

        # Track all BaseTool subclasses found during discovery
        all_found_tool_classes: List[ToolClass] = []

        for file_path in python_files:
            module_name = f"src.tools.implementations.{file_path.stem}"

            # Convert to relative path from project root
            relative_path = file_path.relative_to(project_root)

            try:
                # First attempt: traditional import to register tools via decorator
                module = importlib.import_module(module_name)

                # Second pass: Find all BaseTool subclasses in the module, whether registered or not
                for class_name, obj in inspect.getmembers(module):
                    if not inspect.isclass(obj):
                        continue

                    try:
                        # Check if it's a BaseTool subclass (but not BaseTool itself) and not a base class
                        if (issubclass(obj, BaseTool) and obj != BaseTool and
                                not obj.__name__.startswith('Base') and
                                'Base' not in obj.__name__):

                            tool_info = ToolClass(
                                file_path=str(relative_path),
                                module_name=module_name,
                                class_name=class_name
                            )

                            # Check if class has a name attribute
                            if hasattr(obj, 'name') and isinstance(obj.name, str):
                                tool_info.tool_name = obj.name

                                # Check if this tool is registered
                                if tool_info.tool_name in self._registered_tool_classes:
                                    tool_info.registered = True
                            else:
                                tool_info.error = "Missing or invalid 'name' attribute"

                            all_found_tool_classes.append(tool_info)
                    except Exception as class_exception:
                        # This catches errors when checking issubclass
                        self.logger.error(f"Error checking class {class_name} in {module_name}: {str(class_exception)}")

            except ImportError as e:
                error_msg = f"{module_name}: {str(e)}"
                summary.failed_imports.append(error_msg)
                self.logger.error(f"Failed to import module {module_name}: {str(e)}")

                # Try to extract the traceback for more info
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if exc_traceback:
                    traceback_details = traceback.extract_tb(exc_traceback)
                    self.logger.error(f"Traceback details for {module_name}:")
                    for frame in traceback_details:
                        self.logger.error(
                            f"  File {frame.filename}, line {frame.lineno}, in {frame.name}: {frame.line}")

            except Exception as e:
                # Catch any other exceptions during module import
                error_msg = f"{module_name}: Unexpected error: {str(e)}"
                summary.failed_imports.append(error_msg)
                self.logger.error(f"Unexpected error in module {module_name}: {str(e)}", exc_info=True)

        # Determine which tools were registered during this discovery
        registered_tools_after = set(self._registered_tool_classes.keys())
        newly_registered_tools = registered_tools_after - registered_tools_before

        # Update summary with visible and hidden tools
        for tool_name in newly_registered_tools:
            _, is_hidden = self._registered_tool_classes[tool_name]
            if is_hidden:
                summary.hidden_tools.append(tool_name)
            else:
                summary.visible_tools.append(tool_name)

        # Identify unregistered tools and registration failures
        for tool_info in all_found_tool_classes:
            if not tool_info.registered:
                if tool_info.error:
                    summary.registration_failures.append(tool_info)
                else:
                    # This is a tool class that wasn't registered - likely missing the decorator
                    tool_info.error = "Missing @ToolRegistry.register_tool() decorator"
                    summary.unregistered_tools.append(tool_info)

        summary.total_tools_found = len(summary.visible_tools) + len(summary.hidden_tools)
        return summary

    def _initialize_registered_tools(self) -> Tuple[List[str], Set[str]]:
        """Initialize all registered tool classes with their configurations.

        This method attempts to create instances of all registered tool classes using
        their corresponding configurations from the registry's config dictionary.

        Returns:
            Tuple[List[str], Set[str]]:
                - A list of error messages for any tools that failed to initialize
                  properly. Each entry is formatted as "tool_name: error_message".
                - A set of tool names that failed to initialize
        """
        initialization_failures = []
        failed_tool_names = set()  # Track which tools failed to initialize

        for tool_name, (tool_class, is_hidden) in self._registered_tool_classes.items():
            try:
                tool_config = self.config.get(tool_name)

                if tool_config is None:
                    self.logger.warning(
                        f"⚠️ No configuration found for tool '{tool_name}'. Proceeding with default settings.")

                tool_instance = tool_class(config=tool_config) if tool_config else tool_class()
                self.register_tool_instance(tool_instance, is_hidden)
            except Exception as e:
                error_msg = f"{tool_name}: {str(e)}"
                initialization_failures.append(error_msg)
                failed_tool_names.add(tool_name)  # Track this tool name as failed
                self.logger.error(f"Failed to initialize tool {tool_name}: {str(e)}", exc_info=True)

        return initialization_failures, failed_tool_names

    @classmethod
    def register_tool(cls, hidden: bool = False) -> Callable:
        """Class method decorator for registering tool classes in the registry.

        This decorator registers a tool class with the registry. The decorated class
        must have a 'name' attribute defined as a string.

        Args:
            `hidden` (bool, optional): If True, the tool will be registered as hidden
                and only accessible via get_hidden_tool(). Defaults to False.

        Returns:
            `Callable`: A decorator function that registers the tool class.

        Raises:
            `ValueError`: If the decorated class doesn't have a valid 'name' attribute.
        """

        def decorator(tool_class: Type[BaseTool]) -> Type[BaseTool]:
            # Enhanced validation with detailed error messages
            if not hasattr(tool_class, 'name'):
                raise ValueError(f"Tool class '{tool_class.__name__}' must define a 'name' attribute.")

            if tool_class.name is None:
                raise ValueError(f"Tool class '{tool_class.__name__}' has None 'name' attribute.")

            if not isinstance(tool_class.name, str):
                raise ValueError(
                    f"Tool class '{tool_class.__name__}' must define 'name' as a string, "
                    f"but got {type(tool_class.name).__name__}: {repr(tool_class.name)}"
                )

            if not tool_class.name:  # Empty string check
                raise ValueError(f"Tool class '{tool_class.__name__}' has an empty string as 'name' attribute.")

            # Register the tool
            cls._registered_tool_classes[tool_class.name] = (tool_class, hidden)

            # Add a registration message for debugging
            logging.getLogger(cls.__name__).debug(
                f"Registered tool class '{tool_class.__name__}' with name='{tool_class.name}'"
            )

            return tool_class

        return decorator

    def register_tool_instance(self, tool: BaseTool, hidden: bool = False) -> None:
        """Register a tool instance in the registry.

        Args:
            tool (BaseTool): The tool instance to register
            hidden (bool, optional): If True, registers the tool as hidden.
                Defaults to False.

        Raises:
            ValueError: If the tool has an invalid name property
        """
        # Validate tool name property
        if not hasattr(tool, 'name'):
            raise ValueError(f"Tool class '{tool.__class__.__name__}' is missing required 'name' attribute")

        if tool.name is None:
            raise ValueError(f"Tool class '{tool.__class__.__name__}' has None 'name' attribute")

        if not isinstance(tool.name, str):
            raise ValueError(
                f"Tool class '{tool.__class__.__name__}' has non-string 'name' attribute: {type(tool.name)}")

        target_dict = self.hidden_tools if hidden else self.tools
        target_dict[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name.

        Args:
            name (str): The name of the tool to retrieve

        Returns:
            Optional[BaseTool]: The requested tool instance if found, None otherwise
        """
        return self.tools.get(name)

    def get_hidden_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a hidden tool by name.

        Args:
            name (str): The name of the hidden tool to retrieve

        Returns:
            Optional[BaseTool]: The requested hidden tool instance if found,
                None otherwise
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