
# Deployment Overview

Flexo can be deployed using two main approaches, each suited for different needs and scenarios.

---

## Deployment Approaches

### Approach 1: Build-time Configuration
With this approach, you bake your agent configuration into the container image during build time. Environment variables are still injected at runtime for security.

```mermaid
graph LR
    config1[agent.yaml + tools] --> build[Build Image]
    build --> reg1[Push to Registry]
    reg1 --> deploy1[Deploy Container]
    env1[.env variables] -.-> deploy1

    classDef config stroke:#0288d1
    classDef env stroke:#388e3c
    classDef action stroke:#ffa000
    
    class config1 config
    class env1 env
    class build,reg1,deploy1 action
```

**Best for:**

- Stable configurations
- Version-controlled agent behavior
- Immutable deployments
- Faster container startup

### Approach 2: Runtime Configuration
With this approach, you use a base image and inject both configuration and environment variables at runtime. This allows for more flexible configuration management.

```mermaid
graph LR
    base[Base Image] --> reg2[Push to Registry]
    reg2 --> deploy2[Deploy Container]
    config2[agent.yaml + tools] -.-> deploy2
    env2[.env variables] -.-> deploy2

    classDef config stroke:#6C8EBF
    classDef env stroke:#63825A
    classDef action stroke:#DD7E6B

    class config2 config
    class env2 env
    class base,reg2,deploy2 action
```

**Best for:**

- Dynamic configuration updates
- Environment-specific settings
- Testing different configurations
- Separate configuration management

---

## Deployment Process

The general deployment process follows these steps:

1. [Building the Image](building-image.md)
2. [Pushing to a Registry](registries/overview.md)
3. [Deploying to a Platform](platforms/overview.md)

---
