<p align="center">
    <img alt="flexo framework logo" src="/docs/marmot.png" height="128">
    <h1 align="center">Flexo Framework</h1>
</p>

<p align="center">
  <img align="center" alt="Project Status: Beta" src="https://img.shields.io/badge/Status-Beta-yellow">

  <h4 align="center">Flexo is a powerful and flexible agent framework. It provides a FastAPI-based RESTful API for deploying customizable AI agents that can execute Python functions and interact with external services while handling real-time streaming responses.</h4>
</p>

---

## Features
- **Configurable Agent**: YAML-based configuration for custom behaviors
- **Tool Integration**: Execute Python functions and REST API calls
- **Streaming Support**: Real-time streaming with pattern detection
- **Production Ready**: Containerized deployment support with logging
- **FastAPI Backend**: Modern async API with comprehensive docs

---

## Quick Start

### Local Development

1. Fork and clone:
   ```bash
   # First, fork the repository on GitHub by clicking the 'Fork' button
   # Then clone your fork:
   git clone https://github.com/YOUR_USERNAME/flexo.git
   cd flexo

   # Add the upstream repository
   git remote add upstream https://github.com/ibm/flexo.git
   ```

2. Set up the environment:
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

3. Configure:
   - Copy `.env.example` to `.env` and add your credentials
   - Review `src/configs/agent.yaml` for agent settings

4. Run the server:
   ```bash
   uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
   ```

### Docker Development
```bash
docker build -t flexo-agent .
docker run -p 8000:8000 --env-file .env flexo-agent
```


---

## Supported LLM Providers

Flexo supports multiple LLM providers through a unified adapter interface. Configure your preferred models in `src/configs/models.yaml`.

### Cloud Hosted Providers

| Provider    | Supported API Endpoints                        | Service Type |
|-------------|------------------------------------------------|--------------|
| OpenAI      | `/chat/completions`                            | ☁️ API Service |
| Anthropic   | `/messages`                                    | ☁️ API Service |
| xAI         | `/chat/completions`                            | ☁️ API Service |
| Mistral AI  | `/chat/completions`                            | ☁️ API Service |
| IBM WatsonX | `/text/chat_stream`, `/text/generation_stream` | ☁️ API Service |

### Local/Self-Hosted Options

| Implementation | Key Feature | Deployment Type |
|----------------|-------------|----------------|
| vLLM | High throughput, optimized for GPU | 🖥️ Server |
| Ollama | Simplified model management | 💻 Desktop/Server |
| LLaMA.cpp | CPU-friendly, resource efficient | 💻 Desktop/Server |
| LM Studio | User-friendly model testing | 💻 Desktop |
| LocalAI | Multi-model hub with extended features | 🖥️ Server |
| Text Generation WebUI | Rich UI with extensive options | 🖥️ Server |

All local implementations connect through Flexo's OpenAI-compatible adapter, which handles the communication with these tools regardless of their specific API implementations. It can use both `/completions` and `/chat/completions` endpoints.

For detailed configuration including environment variables, API keys, and base URLs, see our [Model Configuration Guide](https://ibm.github.io/flexo/model-configuration/).

---

## Documentation

### Getting Started
- [Documentation](https://ibm.github.io/flexo/)
- [Quick Setup Guide](https://ibm.github.io/flexo/getting-started/)
- [Agent Configuration](https://ibm.github.io/flexo/agent-configuration/)
- [Building from Source](https://ibm.github.io/flexo/deployment/overview/)
- [API Reference](https://ibm.github.io/flexo/api/)

### Reference Documentation
- [Agent System](https://ibm.github.io/flexo/reference/agent/)
- [Tools Overview](https://ibm.github.io/flexo/reference/tools/)
- [Data Models](https://ibm.github.io/flexo/reference/data_models/)
- [Database Integration](https://ibm.github.io/flexo/reference/database/)

### Deployment Guides
- [Building Images](https://ibm.github.io/flexo/deployment/building-image/)
- [Container Registries](https://ibm.github.io/flexo/deployment/registries/overview/)
- [Platform Deployment](https://ibm.github.io/flexo/deployment/platforms/overview/)

---

## Repository Structure
```
flexo/
├── docs/
├── src/
│   ├── agent/            # Agent(s)
│   ├── api/              # API endpoints
│   ├── configs/          # Configurations
│   ├── data_models/      # Data models
│   ├── database/         # Database adapters
│   ├── llm/              # LLM components
│   ├── prompt_builders/  # Core prompt generation
│   ├── tools/                   
│   │   ├── core/                # Core tool components
│   │   ├── implementations/     # 🔧 Add your custom tools here!
│   │   └──notebooks/            # Notebook(s) for tool development/testing
│   ├── utils/            # Utils/shared code
│   └── main.py           # App entry point
└── ...
```

---

## Support
- [Documentation](https://ibm.github.io/flexo/)
- [Issue Tracker](../../issues)
- [Contributing](CONTRIBUTING.md)

## Versioning
This project follows [Semantic Versioning](https://semver.org/). See [releases](../../releases) for version history.

## Contributing
We welcome contributions! All commits must be signed with DCO (`git commit -s`). See our [Contributing Guide](CONTRIBUTING.md) for details.

## Code of Conduct
We are committed to fostering a welcoming and inclusive community. Please review our [Code of Conduct](CODE_OF_CONDUCT.md) to understand the standards we uphold.

## Security
Review our [Security Policy](SECURITY.md) for handling vulnerabilities.

## License
Apache 2.0 License - see [LICENSE](LICENSE) for details.

---