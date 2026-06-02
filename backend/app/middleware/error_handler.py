"""
Error handling middleware for CSV Upload API
Catches unhandled exceptions and returns user-friendly JSON error responses
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware:
    """Middleware to handle and log all errors"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next: Callable):
        try:
            response = await call_next(request)
            return response
        except RequestValidationError as exc:
            logger.warning(f"Validation error on {request.method} {request.url.path}: {exc}")
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": "Validation Error",
                    "message": "The request data is invalid",
                    "details": [
                        {
                            "field": error.get("loc", ["unknown"])[0],
                            "message": error.get("msg", "Invalid value")
                        }
                        for error in exc.errors()
                    ]
                }
            )
        except Exception as exc:
            logger.error(
                f"Unhandled error on {request.method} {request.url.path}: {str(exc)}",
                exc_info=True
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Server Error",
                    "message": "An unexpected error occurred. Please try again later."
                }
            )


def create_error_responses():
    """
    Create standardized error response objects
    Used by route handlers to return consistent error formats
    """
    return {
        "bad_request": lambda msg: {
            "status_code": status.HTTP_400_BAD_REQUEST,
            "content": {"error": "Bad Request", "message": msg}
        },
        "unauthorized": lambda msg="Unauthorized": {
            "status_code": status.HTTP_401_UNAUTHORIZED,
            "content": {"error": "Unauthorized", "message": msg}
        },
        "forbidden": lambda msg="Forbidden": {
            "status_code": status.HTTP_403_FORBIDDEN,
            "content": {"error": "Forbidden", "message": msg}
        },
        "not_found": lambda msg="Not Found": {
            "status_code": status.HTTP_404_NOT_FOUND,
            "content": {"error": "Not Found", "message": msg}
        },
        "conflict": lambda msg="Conflict": {
            "status_code": status.HTTP_409_CONFLICT,
            "content": {"error": "Conflict", "message": msg}
        },
        "payload_too_large": lambda msg="File too large": {
            "status_code": status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "content": {"error": "Payload Too Large", "message": msg}
        },
        "server_error": lambda msg="Internal server error": {
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "content": {"error": "Server Error", "message": msg}
        },
        "service_unavailable": lambda msg="Service temporarily unavailable": {
            "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
            "content": {"error": "Service Unavailable", "message": msg}
        }
    }
