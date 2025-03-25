# Changelog
All notable changes to Flexo will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2.2] - 2025-03-25

### Features & Improvements
- Added `/models` endpoint and enabled CORS support.
- Initiated MCP client and tool registry functionality (WIP).
- Updated tool patterns for enhanced consistency.

### Fixes & Updates
- Fixed multi tool accumulation issue.
- Fixed mid-response tool buffer leak.
- Updated chat completions data models: updated `FunctionDetail` and removed `name` from `ToolCall`.

### Notes
- MCP configuration in `agent.yaml` is now commented out by default.

[v0.2.2]: https://github.com/ibm/flexo/releases/tag/v0.2.2

## [v0.2.1] - 2025-03-14

### Fixes & Updates
- Fixed issue with LLMFactory not recognizing openai-compat vendor names

[v0.2.1]: https://github.com/ibm/flexo/releases/tag/v0.2.1

## [v0.2.0] - 2025-03-10

### Features & Improvements
- Added multiple new LLM adapters:
  - Anthropic adapter with dedicated prompt builder
  - OpenAI compatible adapter with dedicated prompt builder (allows connecting to vLLM, Ollama, etc.)
  - xAI adapter with dedicated prompt builder
  - Mistral AI adapter with SSE conversion
- Refactored tool registration to use `agent.yaml` config definitions instead of class decorators
- Enhanced pattern detection with improved Aho-Corasick method that handles spaces and linebreaks
- Added fallback JSON parsing logic for improved robustness
- Added example DuckDuckGo tool implementation

### Fixes & Updates
- Fixed issue to allow context in ChatCompletionRequest to be empty dict
- Improved tool registry logging
- Updated documentation across multiple components

[v0.2.0]: https://github.com/ibm/flexo/releases/tag/v0.2.0

## [v0.1.1] - 2024-02-14

### Features & Improvements
- Streamlined tool creation and registration workflow with new loading approach
- Added Wikipedia tool support and documentation 
- Enhanced streaming implementation with improved context handling and LLM integration
- Added Llama tool structure example
- Improved nested JSON tool parsing capability

### Fixes & Updates
- Fixed streaming process bug and removed unused type adapters
- Updated tool configuration and path structures
- Added Elasticsearch SSL certificate documentation

[v0.1.1]: https://github.com/ibm/flexo/releases/tag/v0.1.1

## [v0.1.0] - 2024-01-31

### Initial Release
- Configurable AI agent framework with YAML-based configuration
- FastAPI-based interaction endpoint with streaming support
- Tool calling capabilities for Python functions and REST APIs
- Integration with IBM watsonx.ai models (Granite, Mistral, Llama)
- Integration with OpenAI models
- Docker and Podman containerization support
- Complete documentation and deployment guides
- Database integration (Milvus and Elastic)
- Robust prompt building and parsing systems
- Comprehensive LLM integration components

[v0.1.0]: https://github.com/ibm/flexo/releases/tag/v0.1.0
