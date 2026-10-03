"""Shared API errors and their response shape."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, **details: object):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message, **exc.details}},
    )


def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "not_found" if exc.status_code == 404 else "http_error", "message": str(exc.detail)}},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
