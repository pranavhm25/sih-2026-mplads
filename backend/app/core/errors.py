"""Structured error handling.

APIs return predictable, user-safe error envelopes; raw stack traces never
reach the client (TRD §3 Reliability).
"""
from fastapi import Request
from fastapi.responses import JSONResponse


class DrishtiError(Exception):
    """Domain error carrying a user-safe message and HTTP status."""

    def __init__(self, message: str, status_code: int = 400, code: str = "error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(DrishtiError):
    def __init__(self, entity: str, entity_id: str):
        super().__init__(
            message=f"{entity} '{entity_id}' was not found.",
            status_code=404,
            code="not_found",
        )


class ValidationError400(DrishtiError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=400, code="validation_error")


class StateTransitionError(DrishtiError):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=409, code="invalid_transition")


def drishti_error_handler(_: Request, exc: DrishtiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Log server-side only; client gets a generic message.
    import logging

    logging.getLogger("drishti").exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An unexpected error occurred. Please try again.",
            }
        },
    )
