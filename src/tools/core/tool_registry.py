# src/tools/core/tool_registry.py

import logging
import asyncio
from typing import Dict, Optional, List, Any, Tuple

from src.data_models.tools import Tool
from src.tools.core.base_tool import BaseTool
from src.tools.core.utils.tool_discovery import discover_custom_tools
from src.tools.core.utils.tool_builder import create_tool_from_config
from src.tools.core.observer import ToolUpdateEvent

TOOL_SOURCE_LOCAL = "local"
TOOL_SOURCE_MCP = "mcp"

REGISTRATION_SUCCESS = "successful"
REGISTRATION_HIDDEN_SUCCESS = "hidden_successful"
REGISTRATION_FAILED = "failed"

ToolInfo = Dict[str, Any]
RegistrationResult = Tuple[str, str]


class ToolRegistry:
    """
    Registry for dynamically loading and storing tool instances.

    Initialization is split into two phases:
      1. Construction: Stores provided configurations.
      2. Asynchronous initialization: Gathers tool infos (from local and, optionally, MCP sources),
         registers tools, and logs summaries.

    Callers with MCP configurations must await `initialize_all_tools()` after construction.
    """

    def __init__(self, tools_config: List[Any], mcp_config: Optional[Dict[str, Any]] = None):
        """
        Args:
            tools_config: A list of tool configurations for local tools.
            mcp_config: A dictionary containing MCP configuration.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.tools: Dict[str, BaseTool] = {}
        self.hidden_tools: Dict[str, BaseTool] = {}
        self.registration_results: Dict[str, List[RegistrationResult]] = {
            REGISTRATION_SUCCESS: [],
            REGISTRATION_HIDDEN_SUCCESS: [],
            REGISTRATION_FAILED: []
        }
        self.tools_config = tools_config or []
        self.mcp_config = mcp_config

        # Synchronously gather local tool info.
        self._local_tool_info: List[ToolInfo] = self._gather_local_tool_info()
        self._mcp_tool_infos: List[ToolInfo] = []
        self._lock = asyncio.Lock()  # thinking about mcp notifications, registering, initialization competing

        if not self.mcp_config:
            # In local-only mode, we expect the caller to await initialization.
            self.logger.info("No MCP config provided. Call 'await initialize_all_tools()' to register local tools.")

    def _gather_local_tool_info(self) -> List[ToolInfo]:
        """Collect local tool infos from tools_config."""
        infos = []
        for cfg in self.tools_config:
            info = {
                "name": cfg.get("name", "<unnamed>"),
                "source": TOOL_SOURCE_LOCAL,
                "config": cfg
            }
            infos.append(info)
        return infos

    async def _gather_mcp_tool_infos(self) -> List[ToolInfo]:
        """Asynchronously gather tool infos from the MCP server."""
        infos = []
        try:
            from src.mcp.client import FlexoMCPClient

            self.mcp_client = FlexoMCPClient(self.mcp_config)
            await self.mcp_client.connect()
            self.logger.info("MCP client connected successfully.")

            mcp_tools_result = await self.mcp_client.session.list_tools()
            if mcp_tools_result and mcp_tools_result.tools:
                for mcp_tool_def in mcp_tools_result.tools:
                    info = {
                        "name": mcp_tool_def.name,
                        "source": TOOL_SOURCE_MCP,
                        "config": mcp_tool_def
                    }
                    infos.append(info)
                self.logger.info(f"Gathered {len(infos)} MCP tool(s).")
            else:
                self.logger.info("No MCP tools received from the MCP server.")

            # Subscribe to MCP tool updates.
            if hasattr(self.mcp_client, "observer"):
                self.mcp_client.observer.subscribe(self.update_tools_from_mcp)
                self.logger.info("Subscribed to MCP tool update events.")
        except Exception as e:
            self.logger.error(f"Failed to gather MCP tools: {e}", exc_info=True)
        return infos

    def _log_discovered_summary(self, local_count: int, mcp_count: int):
        """Log the discovered tools summary."""
        total = local_count + mcp_count
        summary = "\n" + "=" * 60 + "\n"
        summary += f"DISCOVERED TOOLS SUMMARY: Total: {total} (Local: {local_count}, MCP: {mcp_count})\n"
        summary += "=" * 60 + "\n"
        self.logger.info(summary)

    async def _register_tools(self, tool_infos: List[ToolInfo]):
        """
        Process the aggregated tool infos and register each tool.
        This method clears previous registration results and registers each tool.
        """
        async with self._lock:
            self.registration_results = {
                REGISTRATION_SUCCESS: [],
                REGISTRATION_HIDDEN_SUCCESS: [],
                REGISTRATION_FAILED: []
            }
        discovered_tools = discover_custom_tools()

        # Import MCP tool adapter once.
        from src.mcp.mcp_tool_adapter import convert_mcp_tool_to_flexo_tool

        for info in tool_infos:
            name = info.get("name", "<unnamed>")
            source = info.get("source", TOOL_SOURCE_LOCAL)
            try:
                if source == TOOL_SOURCE_LOCAL:
                    instance = create_tool_from_config(info["config"], discovered_tools=discovered_tools)
                elif source == TOOL_SOURCE_MCP:
                    instance = convert_mcp_tool_to_flexo_tool(info["config"])
                else:
                    raise ValueError(f"Unknown tool source: {source}")

                await self.register_tool(name, instance, source=source)
                self.logger.debug(f"Successfully registered {source} tool: {name}")
            except Exception as e:
                self.logger.error(f"Failed to register tool '{name}' from {source}: {e}", exc_info=True)
                async with self._lock:
                    self.registration_results[REGISTRATION_FAILED].append((name, str(e)))

    async def register_tool(self, name: str, tool: BaseTool, source: str = TOOL_SOURCE_LOCAL, hidden: bool = False):
        """Register a tool instance with the registry, recording its source."""
        async with self._lock:
            if name in self.tools or name in self.hidden_tools:
                error_msg = f"Tool registration error: Tool with name '{name}' is already registered."
                self.logger.error(error_msg)
                self.registration_results[REGISTRATION_FAILED].append((name, "Already registered"))
                raise ValueError(error_msg)

            if hidden:
                self.hidden_tools[name] = tool
                self.registration_results[REGISTRATION_HIDDEN_SUCCESS].append((name, source))
                self.logger.debug(f"Registered hidden tool: {name} from {source}")
            else:
                self.tools[name] = tool
                self.registration_results[REGISTRATION_SUCCESS].append((name, source))
                self.logger.debug(f"Registered tool: {name} from {source}")

    def _log_registration_summary(self):
        """Log the final registration summary (displays discovered and registered info)."""
        # Reading shared state without a lock is acceptable here given our controlled update context.
        succ_list: List[RegistrationResult] = self.registration_results.get(REGISTRATION_SUCCESS, [])
        hidden_list: List[RegistrationResult] = self.registration_results.get(REGISTRATION_HIDDEN_SUCCESS, [])
        failed_list: List[RegistrationResult] = self.registration_results.get(REGISTRATION_FAILED, [])

        total = len(succ_list) + len(hidden_list) + len(failed_list)
        summary = "\n" + "=" * 60 + "\n"
        summary += f"REGISTERED TOOLS SUMMARY ({total} TOTAL)\n"
        summary += "=" * 60 + "\n"
        summary += f"SUCCESS: {len(succ_list)} public tool(s)"
        if hidden_list:
            summary += f", {len(hidden_list)} hidden tool(s)"
        if failed_list:
            summary += f"\nFAILED: {len(failed_list)} tool(s)"
        if succ_list:
            summary += "\n\nREGISTERED TOOLS:"
            for i, (name, source) in enumerate(sorted(succ_list, key=lambda x: x[0]), 1):
                display_name = f"{name} (MCP)" if source == TOOL_SOURCE_MCP else name
                summary += f"\n  {i}. {display_name}"
        if hidden_list:
            summary += "\n\nREGISTERED HIDDEN TOOLS:"
            for i, (name, source) in enumerate(sorted(hidden_list, key=lambda x: x[0]), 1):
                display_name = f"{name} (MCP)" if source == TOOL_SOURCE_MCP else name
                summary += f"\n  {i}. {display_name}"
        if failed_list:
            summary += "\n\nFAILED REGISTRATIONS:"
            for i, (name, err) in enumerate(failed_list, 1):
                summary += f"\n  {i}. {name} - Error: {err}"
        summary += "\n" + "=" * 60 + "\n"
        self.logger.info(summary)

    async def initialize_all_tools(self):
        """
        Asynchronously gather tool infos from both local and MCP sources,
        register all tools, and log a single, combined summary.
        """
        if self.mcp_config:
            mcp_infos = await self._gather_mcp_tool_infos()
            self._mcp_tool_infos = mcp_infos
        else:
            mcp_infos = []

        all_infos = self._local_tool_info + mcp_infos
        self.logger.info(
            f"Total tool infos gathered: {len(all_infos)} (Local: {len(self._local_tool_info)}, MCP: {len(mcp_infos)})"
        )
        self._log_discovered_summary(local_count=len(self._local_tool_info), mcp_count=len(mcp_infos))
        await self._register_tools(all_infos)
        self._log_registration_summary()

    async def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a registered tool by name."""
        async with self._lock:
            return self.tools.get(name)

    async def get_hidden_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve a hidden tool by name."""
        async with self._lock:
            return self.hidden_tools.get(name)

    async def get_tool_definitions(
            self,
            allowed: Optional[List[str]] = None,
            disallowed: Optional[List[str]] = None
    ) -> List[Tool]:
        """Get definitions for all registered non-hidden tools with optional filtering."""
        definitions = []
        async with self._lock:
            tools_copy = list(self.tools.items())
        for tool_name, tool in tools_copy:
            if allowed is not None and tool_name not in allowed:
                continue
            if disallowed is not None and tool_name in disallowed:
                continue
            try:
                definitions.append(tool.get_definition())
            except Exception as e:
                self.logger.error(f"Error getting definition for tool '{tool_name}': {e}", exc_info=True)
        return definitions

    def update_tools_from_mcp(self, event: ToolUpdateEvent):
        """
        Synchronous callback for MCP tool update events.
        Defers handling to an asynchronous task.
        """
        asyncio.create_task(self._handle_mcp_update(event))

    async def _handle_mcp_update(self, event: ToolUpdateEvent):
        """
        Asynchronously process MCP tool update events for additions, removals, and updates.
        """
        self.logger.info(f"Processing tool update event: {event}")
        from src.mcp.mcp_tool_adapter import convert_mcp_tool_to_flexo_tool

        # Handle tool additions.
        if event.new_tool_defs:
            self.logger.info(f"Processing {len(event.new_tool_defs)} new tools from MCP")
            for tool_def in event.new_tool_defs:
                try:
                    name = tool_def.name
                    async with self._lock:
                        if name in self.tools or name in self.hidden_tools:
                            self.logger.warning(f"Tool '{name}' already registered, skipping")
                            continue
                    instance = convert_mcp_tool_to_flexo_tool(tool_def)
                    await self.register_tool(name, instance, source=TOOL_SOURCE_MCP)
                    self.logger.info(f"Successfully registered new MCP tool: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to register new MCP tool '{tool_def.name}': {e}", exc_info=True)

        # Handle tool removals.
        if event.removed_tool_names:
            self.logger.info(f"Processing {len(event.removed_tool_names)} removed tools from MCP")
            async with self._lock:
                for name in event.removed_tool_names:
                    if name in self.tools:
                        self.logger.info(f"Removing MCP tool: {name}")
                        del self.tools[name]
                    elif name in self.hidden_tools:
                        self.logger.info(f"Removing hidden MCP tool: {name}")
                        del self.hidden_tools[name]
                    else:
                        self.logger.warning(f"Cannot remove unknown tool: {name}")

        # Handle tool updates.
        if event.updated_tool_defs:
            self.logger.info(f"Processing {len(event.updated_tool_defs)} updated tools from MCP")
            for tool_def in event.updated_tool_defs:
                try:
                    name = tool_def.name
                    instance = convert_mcp_tool_to_flexo_tool(tool_def)
                    async with self._lock:
                        if name in self.tools:
                            self.tools[name] = instance
                            self.logger.info(f"Updated MCP tool: {name}")
                        elif name in self.hidden_tools:
                            self.hidden_tools[name] = instance
                            self.logger.info(f"Updated hidden MCP tool: {name}")
                        else:
                            self.logger.warning(f"Cannot update unknown tool: {name}")
                except Exception as e:
                    self.logger.error(f"Failed to update MCP tool '{tool_def.name}': {e}", exc_info=True)

        # Log updated registration summary.
        if event.new_tool_defs or event.removed_tool_names or event.updated_tool_defs:
            self._log_registration_summary()
