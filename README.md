# Flexo

Flexo is a powerful and flexible agent framework optimized for watsonx.ai and IBM services. It provides a FastAPI-based RESTful API for deploying customizable AI agents that can execute Python functions and interact with external services while handling real-time streaming responses.

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

1. Clone and install:
   ```bash
   git clone https://github.com/YOUR_USERNAME/flexo.git
   cd flexo

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

2. Configure:
   - Copy `.env.example` to `.env` and add your credentials
   - Review `src/configs/agent.yaml` for agent settings

3. Run the server:
   ```bash
   uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
   ```

### Docker Development
```bash
docker build -t flexo-agent .
docker run -p 8000:8000 --env-file .env flexo-agent
```

---

## Documentation

### Getting Started
- ⚡ [Quick Setup Guide](https://pages.github.com/ibm/flexo/getting-started/)
- 🔧 [Agent Configuration](https://pages.github.com/ibm/flexo/agent-configuration/)
- 📖 [Building from Source](https://pages.github.com/ibm/flexo/deployment/overview/)
- 🚀 [API Reference](https://pages.github.com/ibm/flexo/api/)

### Reference Documentation
- 🤖 [Agent System](https://pages.github.com/ibm/flexo/reference/agent/)
- 🛠️ [Tools Overview](https://pages.github.com/ibm/flexo/reference/tools/)
- 📊 [Data Models](https://pages.github.com/ibm/flexo/reference/data_models/)
- 🗄️ [Database Integration](https://pages.github.com/ibm/flexo/reference/database/)

### Deployment Guides
- 🏗️ [Building Images](https://pages.github.com/ibm/flexo/deployment/building-image/)
- 📦 [Container Registries](https://pages.github.com/ibm/flexo/deployment/registries/overview/)
- 🚀 [Platform Deployment](https://pages.github.com/ibm/flexo/deployment/platforms/overview/)

---

## Repository Structure
```
flexo/
├── docs/
├── src/                # Source code
│   ├── configs/        # Configuration files
│   └── ...             # Other modules
├── CONTRIBUTING.md
├── SECURITY.md
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Support
- 📚 [Documentation](https://pages.github.com/ibm/flexo/)
- 🐛 [Issue Tracker](../../issues)
- 🤝 [Contributing](CONTRIBUTING.md)

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
