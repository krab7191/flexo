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

    # Log summary of discovery process with improved formatting
    if discovered:
        discovered_count = len(discovered)
        tool_names = sorted(discovered.keys())

        header = "\n" + "-" * 50
        header += f"\nTOOL DISCOVERY: Found {discovered_count} custom tool(s)"
        header += "\n" + "-" * 50
        logger.info(header)

        # List discovered tools with their class names
        for i, tool_name in enumerate(tool_names, 1):
            tool_class = discovered[tool_name].__name__
            logger.info(f"  {i}. {tool_name:<20} -> {tool_class}")

        logger.info("-" * 50)
    else:
        logger.info("\n" + "-" * 50)
        logger.info("TOOL DISCOVERY: No custom tools found")
        logger.info("-" * 50)

    return discovered
