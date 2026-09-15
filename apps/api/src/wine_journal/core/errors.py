import logging
from dataclasses import dataclass
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("wine_journal.requests")


class ErrorDetail(BaseModel):
    code: str
    message: str
    fields: list[str] = Field(default_factory=list)
    requestId: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


@dataclass
class ApiError(Exception):
    status: int
    code: str
    message: str


def error_response(request_id: str, status: int, code: str, message: str) -> JSONResponse:
    headers = {"Cache-Control": "no-store", "X-Request-ID": request_id}
    if status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(
        ErrorResponse(
            error=ErrorDetail(code=code, message=message, requestId=request_id)
        ).model_dump(),
        status_code=status,
        headers=headers,
    )


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = False

        async def contextual_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = list(message.get("headers", []))
                headers = [(k, v) for k, v in headers if k.lower() != b"x-request-id"]
                headers += [
                    (b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"),
                ]
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, contextual_send)
        except Exception as exc:
            logger.error("request_failed type=%s request_id=%s", type(exc).__name__, request_id)
            if started:
                raise
            response = error_response(
                request_id, 500, "INTERNAL_ERROR", "The request could not be completed."
            )
            await response(scope, receive, contextual_send)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def application_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(request.state.request_id, exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Pydantic error payloads may include the original input. Do not serialize them.
        return error_response(
            request.state.request_id, 422, "VALIDATION_ERROR", "Check the submitted fields."
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return error_response(
            request.state.request_id, exc.status_code, "HTTP_ERROR", "The request is not available."
        )
