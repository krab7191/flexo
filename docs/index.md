# Welcome to Flexo

The [**Flexo Agent Library**](https://github.com/IBM/flexo) is a powerful and flexible codebase that enables users to configure, customize, and deploy a generative AI agent. Designed for adaptability, the library can be tailored to a wide range of use cases, from conversational AI to specialized automation.

---

## Why Flexo?

- **Simplified Deployment**: Deploy anywhere with comprehensive platform guides
- **Production Ready**: Built for scalability and reliability
- **Extensible**: Add custom tools and capabilities
- **Well Documented**: Clear guides for every step

---

## System Architecture

```mermaid
graph TB
    Client[Client] --> API[FastAPI Server]
    
    subgraph API["API Layer"]
        Router[Chat Completions Router]
        SSE[SSE Models]
        Validation[Request Validation]
    end
    
    subgraph Agent["Agent Layer"]
        ChatAgent[Streaming Chat Agent]
        State[State Management]
        Config[Configuration]
    end
    
    subgraph LLM["LLM Layer"]
        Factory[LLM Factory]
        Detection[Tool Detection]
        Builders[Prompt Builders]
        
        subgraph Adapters["LLM Adapters"]
            WatsonX
            OpenAI
            Anthropic
            Mistral
        end
    end
    
    subgraph Tools["Tools Layer"]
        Registry[Tool Registry]
        REST[REST Tools]
        NonREST["Non-REST Tools: Python etc"]
        ExampleTools["Included Example 
        Tools: RAG + Weather"]
    end
    
    subgraph Database["Database Layer"]
        ES[Elasticsearch]
        Milvus[Milvus]
    end
    
    API --> Agent
    Agent --> LLM
    Agent --> Tools
    Tools --> Database
    
    style API stroke:#ff69b4,stroke-width:4px
    style Agent stroke:#4169e1,stroke-width:4px
    style LLM stroke:#228b22,stroke-width:4px
    style Tools stroke:#cd853f,stroke-width:4px
    style Database stroke:#4682b4,stroke-width:4px
    
    style Router stroke:#ff69b4,stroke-width:2px
    style SSE stroke:#ff69b4,stroke-width:2px
    style Validation stroke:#ff69b4,stroke-width:2px
    
    style ChatAgent stroke:#4169e1,stroke-width:2px
    style State stroke:#4169e1,stroke-width:2px
    style Config stroke:#4169e1,stroke-width:2px
    
    style Factory stroke:#228b22,stroke-width:2px
    style Detection stroke:#228b22,stroke-width:2px
    style Builders stroke:#228b22,stroke-width:2px
    style Adapters stroke:#228b22,stroke-width:2px
    style WatsonX stroke:#228b22,stroke-width:2px
    style OpenAI stroke:#228b22,stroke-width:2px
    style Anthropic stroke:#228b22,stroke-width:2px
    style Mistral stroke:#228b22,stroke-width:2px
    
    style Registry stroke:#cd853f,stroke-width:2px
    style ExampleTools stroke:#cd853f,stroke-width:2px
    style REST stroke:#cd853f,stroke-width:2px
    style NonREST stroke:#cd853f,stroke-width:2px
    
    style ES stroke:#4682b4,stroke-width:2px
    style Milvus stroke:#4682b4,stroke-width:2px
    
    style Client stroke:#333,stroke-width:2px
```

---

## Chat Agent State Flow

```mermaid
stateDiagram-v2
    [*] --> STREAMING: Initialize Agent
    
    STREAMING --> TOOL_DETECTION: Tool Call Found
    STREAMING --> COMPLETING: Generation Done
    
    TOOL_DETECTION --> EXECUTING_TOOLS: Process Tool Call
    EXECUTING_TOOLS --> INTERMEDIATE: Tool Execution Complete
    
    INTERMEDIATE --> STREAMING: Continue Generation
    INTERMEDIATE --> COMPLETING: Max Iterations
    
    COMPLETING --> [*]: End Response
    
    note right of STREAMING
        Main generation state
        Handles LLM responses
    end note
    
    note right of EXECUTING_TOOLS
        Concurrent tool execution
        Error handling
    end note
```

---

## Key Features
- **Configurable AI Agent**: Modify settings to match your specific requirements
- **FastAPI-based API**: RESTful API with streaming support
- **Tool Integration**: Execute Python functions and REST API calls
- **Container Ready**: Deploy anywhere with Docker/Podman support
- **IBM AI Integration**: Optimized for watsonx.ai and other IBM services

---

## Quick Start Guide

### 1. Local Development
Start developing with Flexo locally:

- ⚡ [Quick Setup Guide](getting-started.md)
- 🔧 [Configure Your Agent](agent-configuration.md)
- 📖 [Build from Source](deployment/building-image.md)
- 🚀 [Run the Server](getting-started.md)

### 2. Production Deployment
Deploy Flexo to your preferred platform:

| Platform | Best For | Guide |
|----------|----------|-------|
| IBM Code Engine | Serverless, pay-per-use | [Deploy →](deployment/platforms/code-engine.md) |
| AWS Fargate | AWS integration | [Deploy →](deployment/platforms/fargate.md) |
| OpenShift | Enterprise, hybrid cloud | [Deploy →](deployment/platforms/openshift.md) |
| Kubernetes | Custom infrastructure | [Deploy →](deployment/platforms/kubernetes.md) |

---

## Documentation

### Deployment Guides
- 📦 [Container Registries](deployment/registries/overview.md)
- 🚀 [Platform Deployment](deployment/platforms/overview.md)

### Code Reference
- 🤖 [Agent](reference/agent/chat_agent_streaming)
- 🔌 [API Reference](reference/api.md)
- 🛠️ [Tools System](reference/tools/index.md)
- 📊 [Data Models](reference/data_models.md)
- 🗄️ [Database Integration](reference/database.md)

---

## Contributing
See our [Contributing Guide](https://github.com/IBM/flexo/blob/main/CONTRIBUTING.md) for details.

---

## Security
For security concerns, please review our [Security Policy](https://github.com/IBM/flexo/blob/main/SECURITY.md).

---