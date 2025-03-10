# LLM Adapters

This directory contains a collection of adapter classes that provide a standardized interface for interacting with various Large Language Model (LLM) providers. Each adapter implements the `BaseVendorAdapter` abstract base class to ensure consistent handling of model interactions across different vendors.

## Overview

These adapters enable our system to work seamlessly with multiple LLM providers by converting vendor-specific APIs into a unified interface. All adapters produce standardized Server-Sent Events (SSE) chunks when streaming text responses.

## Available Adapters

| Adapter | Description                                         |
|---------|-----------------------------------------------------|
| [BaseVendorAdapter](base_vendor_adapter.md) | Interface all adapters must implement               |
| [AnthropicAdapter](anthropic_adapter.md) | Adapter for Anthropic's Claude models               |
| [OpenAIAdapter](openai_adapter.md) | Adapter for OpenAI models                           |
| [OpenAICompatAdapter](openai_compat_adapter.md) | Adapter for APIs compatible with OpenAI's interface |
| [MistralAIAdapter](mistral_ai_adapter.md) | Adapter for Mistral AI models                       |
| [XAIAdapter](xai_adapter.md) | Adapter for xAI models                              |
| [WatsonxAdapter](watsonx/watsonx_adapter.md) | Adapter for IBM's watsonx.ai platform               |

## WatsonX Submodule

The [watsonx](watsonx/) directory contains specialized implementations for IBM's watsonx.ai platform:

- [WatsonxAdapter](watsonx/watsonx_adapter.md) - Main adapter for watsonx.ai models
- [IBMTokenManager](watsonx/ibm_token_manager.md) - Handles authentication with IBM Cloud
- [WatsonxConfig](watsonx/watsonx_config.md) - Configuration for watsonx.ai connections

## Core Features

All adapters implement these key methods:

- `gen_sse_stream(prompt: str)` - Generate streaming responses from a text prompt
- `gen_chat_sse_stream(messages: List[TextChatMessage], tools: Optional[List[Tool]])` - Generate streaming responses from a chat context

## Implementation Requirements

When implementing a new adapter:

1. Inherit from `BaseVendorAdapter`
2. Implement all abstract methods
3. Convert vendor-specific responses to our standardized `SSEChunk` format
4. Handle streaming appropriately for the specific vendor API

## Usage Example

```python
# Example of using an adapter
from src.llm.adapters import OpenAIAdapter

# Initialize with model name and default parameters
adapter = OpenAIAdapter(
    model_name="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000
)

# Generate streaming response
async for chunk in adapter.gen_sse_stream("Tell me about machine learning"):
    # Process each SSEChunk
    if chunk.choices and chunk.choices[0].delta.content:
        content = chunk.choices[0].delta.content
        # Process the content fragment
        print(content, end="")
```

## Adding New Adapters

To add support for a new LLM provider:

1. Create a new file named `your_provider_adapter.py`
2. Implement the `BaseVendorAdapter` interface
3. Add docstrings and logging
4. Update this index with your new adapter

---