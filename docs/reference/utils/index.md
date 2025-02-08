# 🔧 Utils Documentation

## 📚 Overview

The Utils module provides essential factory patterns and utility classes that support the core functionality of the system. These utilities focus on creating and managing different types of builders, parsers, and formatters used throughout the application.

```mermaid
graph TB
    A[Factory Module] --> B[PromptBuilderFactory]
    A --> C[ToolCallParserFactory]
    
    B --> D[AnthropicPromptBuilder]
    B --> E[OpenAIPromptBuilder]
    B --> F[MistralAIPromptBuilder]
    B --> G[WatsonX Builders]
    
    C --> H[JSONToolCallParser]
    C --> I[NonJSONToolCallParser]
    
    G --> J[GranitePromptBuilder]
    G --> K[LlamaPromptBuilder]
    G --> L[MistralPromptBuilder]
    
    style A stroke:#333,stroke-width:2px
    style B stroke:#333,stroke-width:2px
    style C stroke:#333,stroke-width:2px
```

---

## 🏗️ Components

### Factory Classes

- **🏭 PromptBuilderFactory**
  - Creates appropriate prompt builders based on vendor type
  - Supports multiple LLM providers:
    - Anthropic
    - OpenAI
    - MistralAI
    - WatsonX (Granite, Llama, Mistral)
  - Located in `factory.md`

- **🛠️ ToolCallParserFactory**
  - Generates parser instances for tool calls
  - Supports:
    - JSON format parsing
    - Non-JSON format parsing
  - Located in `factory.md`

### Enums

- **📋 FormatType**
  - Defines supported format types for tool calls
  - Used by parser factories
  - Located in `factory.md`

---

## 🔍 Implementation Details

### Factory Pattern Benefits

1. **Abstraction**: Hides complex instantiation logic
2. **Flexibility**: Easy to add new builders and parsers
3. **Consistency**: Ensures uniform object creation
4. **Maintainability**: Centralizes creation logic

---

## 📚 Further Documentation

- 🏭 See individual builder documentation in [prompt_builders](../prompt_builders/index.md) directory
- 🛠️ Check parser implementations in [parsers](../tools/parsers/index.md) directory
- 📋 Review format types and enums in [factory](factory.md)

---