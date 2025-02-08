# src/main.py

import os
import logging
from fastapi import FastAPI
from starlette import status
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.api.sse_models import SSEChunk
from src.api.routes.chat_completions_api import router as chat_completions_router

"""
This module initializes and configures the FastAPI application, sets up logging,
loads environment variables, and defines global exception handlers. It serves
as the main entrypoint for the chat completions API service.

Environment Variables:
    LOG_LEVEL: Logging level for the application (default: 'INFO')
        Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL

Example:
    To run the application:
    ```bash
    # Set environment variables in .env file or export them
    export LOG_LEVEL=DEBUG

    # Run the FastAPI application
    uvicorn src.main:app --reload
    ```
"""

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Chat Completions API",
    description="API for handling chat completions with streaming support",
    version="1.0.0"
)

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Initializing application with log level: %s", log_level)

# Include the chat completions router
logger.info("Registering chat completions router at /v1")
app.include_router(chat_completions_router, prefix="/v1")


# --------------------
# EXCEPTION HANDLERS
# --------------------

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc: Exception):
    """Global exception handler for all unhandled exceptions.

    Provides a consistent error response format for any unhandled exceptions that
    occur during request processing. Different error types result in different
    HTTP status codes and appropriate error messages.

    Args:
        request: The FastAPI request object.
        exc (Exception): The exception that was raised.

    Returns:
        JSONResponse: A formatted error response with appropriate status code
            and error message.

    Note:
        - ValueError results in 400 Bad Request
        - TimeoutError results in 504 Gateway Timeout
        - All other exceptions result in 500 Internal Server Error
    """
    error_msg = str(exc)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if isinstance(exc, ValueError):
        logger.warning("ValueError occurred: %s", error_msg)
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, TimeoutError):
        logger.error("Request timed out: %s", error_msg)
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
        error_msg = "Request timed out. Please try again."
    else:
        logger.error("Unhandled exception occurred", exc_info=True)

    logger.debug("Generating error response chunk with status %d", status_code)
    error_response = await SSEChunk.make_stop_chunk(
        refusal=error_msg,
        content="I apologize, but an error occurred while processing your request."
    )

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """Exception handler for request validation errors.

    Handles errors that occur during request validation, typically due to
    invalid request format or missing required fields.

    Args:
        request: The FastAPI request object.
        exc (RequestValidationError): The validation exception that was raised.

    Returns:
        JSONResponse: A formatted error response with a 422 status code and
            details about the validation failure.

    Note:
        This handler is specifically for FastAPI's RequestValidationError,
        which occurs when request data fails Pydantic validation.
    """
    logger.warning("Request validation failed: %s", str(exc))
    logger.debug("Validation error details: %s", exc.errors())

    error_response = await SSEChunk.make_stop_chunk(
        refusal=str(exc),
        content="There seems to be an issue with the provided request format. Please check your input and try again."
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )
