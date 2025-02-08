# LLM Adapters Documentation

## Overview

The **LLM Adapters Module** provides implementations for interacting with different Large Language Model (LLM) providers. Each adapter standardizes communication with a specific LLM API, allowing seamless integration into the system.

## Components

### Base Adapter
- **`BaseVendorAdapter`** - Abstract base class that defines the interface for all LLM vendor adapters. All specific adapters inherit from this class.

### Supported LLM Providers

#### Anthropic
- **`AnthropicAdapter`** - Adapter for integrating with Anthropic’s Claude models.

#### Mistral AI
- **`MistralAdapter`** - Adapter for Mistral AI models.

#### OpenAI
- **`OpenAIAdapter`** - Adapter for OpenAI’s GPT models.

#### IBM WatsonX
- **`WatsonXAdapter`** - Adapter for IBM WatsonX models.
- **`WatsonXConfig`** - Configuration settings for WatsonX integration.
- **`IBMTokenManager`** - Token manager for handling authentication and access tokens for WatsonX.

## Additional Resources
- [WatsonX Adapters](watsonx/index.md)
