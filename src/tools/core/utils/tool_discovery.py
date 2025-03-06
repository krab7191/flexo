# tools/core/utils/tool_discovery.py

import pkgutil
import inspect
import logging
import importlib
from typing import Dict, Type

from src.tools.core.base_tool import BaseTool

logger = logging.getLogger(__name__)


def discover_custom_tools() -> Dict[str, Type[BaseTool]]:
    """
    Scans the tools.implementations package to find all tool classes that:
      - Inherit from BaseTool (excluding BaseTool itself)
      - Have a class attribute `name` that uniquely identifies them.
    Returns:
      A dictionary mapping tool_name (str) to the tool class.
    """
    discovered = {}
    try:
        import src.tools.implementations  # Ensure the package is imported
        logger.debug("Scanning tools.implementations for custom tools.")
    except Exception as e:
        logger.error(f"Failed to import tools.implementations package: {e}")
        return discovered

    for finder, module_name, ispkg in pkgutil.iter_modules(src.tools.implementations.__path__):
        try:
            module = importlib.import_module(f"src.tools.implementations.{module_name}")
            logger.debug(f"Imported module: src.tools.implementations.{module_name}")
        except Exception as e:
            logger.error(f"Failed to import module {module_name}: {e}")
            continue

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                    inspect.isclass(attr)
                    and issubclass(attr, BaseTool)
                    and attr is not BaseTool
                    and hasattr(attr, "name")
            ):
                tool_key = getattr(attr, "name")
                discovered[tool_key] = attr
                logger.debug(f"Discovered tool: '{tool_key}' -> {attr.__name__}")

    # Build a single log message for the summary
    if discovered:
        discovered_count = len(discovered)
        tool_names = sorted(discovered.keys())

        log_message = "\n" + "-" * 50
        log_message += f"\nTOOL DISCOVERY: Found {discovered_count} custom tool(s)"
        log_message += "\n" + "-" * 50

        # List discovered tools with their class names
        for i, tool_name in enumerate(tool_names, 1):
            tool_class = discovered[tool_name].__name__
            log_message += f"\n  {i}. {tool_name:<20} -> {tool_class}"

        log_message += f"\n{'-' * 50}"
    else:
        log_message = "\n" + "-" * 50
        log_message += "\nTOOL DISCOVERY: No custom tools found"
        log_message += f"\n{'-' * 50}"

    logger.debug(log_message)

    return discovered
