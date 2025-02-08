# src/llm/adapters/base_vendor_adapter.py

from abc import abstractmethod
from typing import AsyncGenerator, Optional, List
from ...api.sse_models import SSEChunk
from ...data_models.tools import Tool
from ...data_models.chat_completions import TextChatMessage


class BaseVendorAdapter:
    """
    Abstract base class for any LLM vendor adapter.
    Must produce SSEChunk objects when streaming text.
    """

    @abstractmethod
    async def gen_sse_stream(self, prompt: str) -> AsyncGenerator[SSEChunk, None]:
        """
        Generate SSEChunk objects in a streaming manner from the given prompt.
        """
        pass

    # Optionally, you can define a chat method if you differentiate chat vs text
    @abstractmethod
    async def gen_chat_sse_stream(self, messages: List[TextChatMessage], tools: Optional[List[Tool]]) -> AsyncGenerator[SSEChunk, None]:
        pass
