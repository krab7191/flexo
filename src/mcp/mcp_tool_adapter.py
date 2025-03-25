# src/mcp/mcp_tool_adapter.py

from typing import Any, Dict, Optional
from mcp.types import Tool as MCPToolDefinition
from src.tools.core.base_mcp_tool import BaseMCPTool
from src.data_models.tools import ToolResponse
from src.data_models.agent import StreamContext


class DefaultMCPTool(BaseMCPTool):
    """
    A default implementation of an MCP-based tool.
    This class automatically initializes from an MCP tool definition and provides
    a basic execution behavior (which you can later customize).
    """

    async def execute(self, context: Optional[StreamContext] = None, **kwargs) -> ToolResponse:
        # Default behavior: simply echo the provided arguments.
        result_text = f"Executed {self.name} with arguments: {kwargs}"
        # Construct and return a ToolResponse (adapt to your actual structure)
        return ToolResponse(result=result_text)

    def parse_output(self, output: str) -> Dict[str, Any]:
        # Default parsing: wrap the output in a dictionary.
        return {"result": output}


def convert_mcp_tool_to_flexo_tool(mcp_tool_def: MCPToolDefinition, config: Optional[Dict] = None) -> BaseMCPTool:
    """
    Convert an MCP tool definition into a Flexo tool instance.

    Args:
        mcp_tool_def: An MCP tool definition instance (from mcp.types).
        config: Optional configuration for the tool.

    Returns:
        An instance of BaseMCPTool (or a subclass thereof) that represents the tool.
    """
    return DefaultMCPTool(mcp_tool_def, config)
