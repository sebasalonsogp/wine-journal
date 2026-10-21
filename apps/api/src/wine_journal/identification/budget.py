"""Single-process request guard; deployment must also enforce shared edge limits."""

import asyncio
from collections import deque
from math import ceil
from threading import Lock
from time import monotonic

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from wine_journal.core.errors import ApiError, error_response


class BarcodeBudget:
    """Shared by lookup/confirmation; no tokens, codes or persistent IP records."""

    def __init__(self) -> None:
        self.lock = Lock()
        self.global_requests: deque[float] = deque()
        self.peers: dict[str, deque[float]] = {}

    def consume(self, peer: str) -> None:
        with self.lock:
            now = monotonic()
            while self.global_requests and self.global_requests[0] <= now - 60:
                self.global_requests.popleft()
            for key in list(self.peers):
                queue = self.peers[key]
                while queue and queue[0] <= now - 60:
                    queue.popleft()
                if not queue:
                    del self.peers[key]
            queue = self.peers.get(peer, deque())
            blocked = queue if len(queue) >= 30 else self.global_requests
            if len(queue) >= 30 or len(self.global_requests) >= 120:
                raise ApiError(
                    429,
                    "BARCODE_RATE_LIMITED",
                    "Too many lookups. Try again shortly.",
                    max(1, ceil(blocked[0] + 60 - now)),
                )
            queue.append(now)
            self.peers[peer] = queue
            self.global_requests.append(now)


class BarcodeRequestGuard:
    """Charge before JSON parsing; cap bytes including chunked/incorrect-length bodies."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["path"]
            not in {
                "/api/v1/identification/barcode-lookups",
                "/api/v1/identification/barcode-confirmations",
            }
            or scope["method"] != "POST"
        ):
            await self.app(scope, receive, send)
            return
        try:
            # Never parse forwarded headers or client-supplied account IDs here.
            # ASGI proxy trust must be restricted to the actual deployment ingress.
            peer = scope["client"][0] if scope.get("client") else "unknown"
            budget: BarcodeBudget = scope["app"].state.barcode_budget
            budget.consume(peer)
            body = bytearray()
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > 4096:
                        raise ApiError(
                            413, "BARCODE_REQUEST_TOO_LARGE", "The lookup request is too large."
                        )
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            response = error_response(
                scope["state"]["request_id"],
                408,
                "BARCODE_REQUEST_TIMEOUT",
                "The lookup request timed out.",
            )
            await response(scope, receive, send)
            return
        except ApiError as exc:
            response = error_response(
                scope["state"]["request_id"], exc.status, exc.code, exc.message
            )
            if exc.retry_after is not None:
                response.headers["Retry-After"] = str(exc.retry_after)
            await response(scope, receive, send)
            return

        delivered = False

        async def bounded_receive() -> Message:
            nonlocal delivered
            if delivered:
                return await receive()
            delivered = True
            return {"type": "http.request", "body": bytes(body), "more_body": False}

        await self.app(scope, bounded_receive, send)
