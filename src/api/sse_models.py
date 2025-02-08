# src/api/sse_models.py
from __future__ import annotations

import time
from enum import Enum
from typing import Dict
from typing import List, Optional, Any
from pydantic import BaseModel


class AgentStatus(str, Enum):
    STARTING = "starting_generation"
    TOOL_DETECTED = "tool_call_detected"
    TOOLS_EXECUTED = "tools_executed"
    MAX_DEPTH = "max_depth_reached"
    CONTINUING = "continuing_generation"


class SSEStatus(BaseModel):
    status: AgentStatus
    details: Optional[Dict[str, Any]] = None


class SSEFunction(BaseModel):
    """Model for function calls in SSE responses, with support for streaming chunks."""
    name: str = ""
    arguments: str = ""


class SSEToolCall(BaseModel):
    """Model for tool calls in SSE responses."""
    index: int = 0
    id: Optional[str] = None
    type: str = "function"
    function: Optional[SSEFunction] = None


class SSEDelta(BaseModel):
    """Model for delta content in SSE responses."""
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[SSEToolCall]] = None
    refusal: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None


class SSEChoice(BaseModel):
    """Model for choices in SSE responses."""
    index: int
    delta: SSEDelta
    logprobs: Optional[dict] = None
    finish_reason: Optional[str] = None


class SSEChunk(BaseModel):
    """Model for SSE chunks."""
    id: str
    object: str
    created: int
    model: str
    service_tier: Optional[str] = None
    system_fingerprint: Optional[str] = None
    choices: List[SSEChoice]
    thread_id: Optional[str] = None  # this is an IBM wxO thing

    @staticmethod
    def make_text_chunk(text: str) -> 'SSEChunk':
        """
        Utility to create a minimal SSEChunk that only has user-visible 'content'.
        This ensures we never leak partial function-call details back to the user.
        """
        return SSEChunk(
            id=f"chatcmpl-{time.time()}",
            object="chat.completion.chunk",
            created=int(time.time()),
            model="agent-01",
            choices=[
                SSEChoice(
                    index=0,
                    delta=SSEDelta(role="assistant", content=text),
                    finish_reason=None
                )
            ]
        )

    @staticmethod
    async def make_status_chunk(status: str, extra_info: Optional[Dict] = None) -> 'SSEChunk':
        metadata = {"status": status}
        if extra_info:
            metadata.update(extra_info)

        return SSEChunk(
            id=f"status_{time.time()}",
            object="chat.completion.chunk",
            created=int(time.time()),
            model="agent-01",
            choices=[
                SSEChoice(
                    index=0,
                    delta=SSEDelta(
                        role="system",
                        metadata=metadata
                    ),
                    finish_reason=None
                )
            ]
        )

    @staticmethod
    async def make_stop_chunk(content=None, refusal=None) -> 'SSEChunk':
        return SSEChunk(
            id=f"chatcmpl-{time.time()}",
            object="chat.completion.chunk",
            created=int(time.time()),
            model="agent-01",
            choices=[
                SSEChoice(
                    index=0,
                    delta=SSEDelta(role="assistant", content=content, refusal=refusal),
                    finish_reason="stop"
                )
            ]
        )
