"""
API routes for OpenAI integration (e.g., code completion, suggestions).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from openai import OpenAI  # Ensure this matches your OpenAI library version

from openpypi.api.dependencies import get_api_key, get_openai_client
from openpypi.api.schemas import (
    APIResponse,
    ErrorResponse,
    OpenAICompletionRequest,
    OpenAICompletionResponse,
)
from openpypi.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/completion",
    response_model=OpenAICompletionResponse,
    summary="Get Code Completion from OpenAI",
    description="Sends a prompt to the OpenAI API for code completion or generation.",
    responses={503: {"model": ErrorResponse, "description": "OpenAI service unavailable"}},
)
async def get_openai_completion(
    request_data: OpenAICompletionRequest,
    api_key: str = Depends(get_api_key),  # Protects this endpoint
    openai_client: OpenAI = Depends(get_openai_client),  # Gets configured client
) -> OpenAICompletionResponse:
    """Handles requests for code completion using OpenAI."""
    if not openai_client:
        logger.error("OpenAI client not available for /completion endpoint.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI service is not configured or unavailable.",
        )

    logger.info(
        f"Received OpenAI completion request. Model: {request_data.model}, Prompt: '{request_data.prompt[:50]}...'"
    )

    try:
        # Example: Using the chat completions endpoint for newer models
        # Adjust if using older completion models or different OpenAI methods.
        completion = await openai_client.chat.completions.create(
            model=request_data.model,  # e.g., "gpt-3.5-turbo" or "gpt-4"
            messages=[
                {"role": "system", "content": "You are a helpful AI programming assistant."},
                {"role": "user", "content": request_data.prompt},
            ],
            max_tokens=request_data.max_tokens,
            temperature=request_data.temperature,
            # Add other parameters as needed, e.g., n, stop, presence_penalty
        )

        # Extract the response content
        # The structure of 'completion' object depends on the OpenAI library version and endpoint used.
        # For chat completions, it's typically like: completion.choices[0].message.content
        if completion.choices and len(completion.choices) > 0:
            response_text = completion.choices[0].message.content.strip()
            logger.info(f"OpenAI completion successful. Response: '{response_text[:100]}...'")
            return OpenAICompletionResponse(
                success=True,
                message="OpenAI completion successful.",
                data={
                    "completion_text": response_text,
                    "raw_response": completion.model_dump(),
                },  # or completion.to_dict()
            )
        else:
            logger.warning("OpenAI response did not contain expected choices.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI returned an unexpected response structure.",
            )

    except Exception as e:
        logger.error(f"Error during OpenAI API call: {e}", exc_info=True)
        # More specific error handling can be added here based on OpenAI exceptions
        # For example, openai.APIError, openai.AuthenticationError, etc.
        error_detail = str(e)
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if "authentication" in error_detail.lower():
            status_code = (
                status.HTTP_503_SERVICE_UNAVAILABLE
            )  # Or 401 if it's an API key issue with the client
            error_detail = "OpenAI authentication failed. Check server configuration."
        elif "rate limit" in error_detail.lower():
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
            error_detail = "OpenAI rate limit exceeded. Please try again later."

        raise HTTPException(
            status_code=status_code, detail=f"Failed to get completion from OpenAI: {error_detail}"
        )


# TODO: Add more specific OpenAI integration endpoints as needed:
# - /suggest/refactor: For refactoring suggestions
# - /suggest/docstring: For generating docstrings
# - /generate/tests: For generating test cases for a piece of code
# - /analyze/code: For code analysis or vulnerability detection (if applicable models exist)
