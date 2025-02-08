# API Documentation

The generative AI agent exposes a FastAPI-based RESTful API for interacting with the model. This document provides an overview of the API, key endpoints, and how to access the full API documentation.

---

## **Overview**

The API allows you to interact with the AI agent via HTTP requests. It supports:

- Sending messages to the AI agent.
- Streaming conversational responses.
- Providing contextual data for more tailored responses.

---

## **Base URL**

The API server runs on the following base URL when deployed locally:
```
http://127.0.0.1:8000
```

For production deployments, replace the base URL with your server's address.

---

## **Full API Documentation**

The full API documentation is available in OpenAPI format. When the app is running, you can view it interactively using:

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

To access the OpenAPI JSON specification directly:
- [Download openapi.json](openapi.json)

---

## **Key Endpoints**

### 1. **POST `/v1/chat/completions`**
Streams a conversational response from the AI agent.

#### **Request**
- **Headers**:
  - `Content-Type: application/json`
- **Body**:
  ```json
  {
    "messages": [
      {
        "role": "user",
        "content": [
          { "text": "Hello, AI!" }
        ]
      }
    ],
    "context": {
      "values": [
        { "key": "session_id", "value": "abc123" }
      ]
    },
    "include_status_updates": false,
    "stream": true
  }
  ```

#### **Response**
- **Success**:
  ```json
  {
    "id": "abc123",
    "object": "thread.message.delta",
    "thread_id": "None",
    "choices": [
      {
        "delta": {
          "role": "assistant",
          "content": "Hello! How can I assist you?"
        }
      }
    ]
  }
  ```
- **Error**:
  ```json
  {
    "error": "Invalid input format",
    "choices": [
      {
        "delta": {
          "role": "assistant",
          "content": "There seems to be an issue with the provided request format. Please check your input and try again."
        }
      }
    ]
  }
  ```

---

### 2. **GET `/docs`**
Provides interactive Swagger documentation for exploring the API.

---

### 3. **GET `/redoc`**
Provides a ReDoc-based view of the API schema.

---

## **Using the OpenAPI Schema**
The OpenAPI JSON file can be integrated with tools like:

- **Postman**: Import the schema to explore and test endpoints.
- **Swagger Editor**: Visualize and validate the schema.

For instructions, see [Swagger Editor](https://editor.swagger.io/) or [Postman](https://www.postman.com/).

---

## **Troubleshooting**
- If you encounter issues accessing the API or endpoints:
  1. Ensure the server is running (`uvicorn main:app` or via Docker/Podman).
  2. Verify the base URL and port are correct.
  3. Check logs for errors in the server console.

---

For further details, consult the [Getting Started Guide](getting-started.md) or the [Configuration Guide](agent-configuration).
