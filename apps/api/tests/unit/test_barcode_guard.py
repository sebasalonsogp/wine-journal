import asyncio
from types import SimpleNamespace

import pytest
from starlette.types import Message, Receive, Scope, Send

from wine_journal.identification import budget


@pytest.mark.parametrize("mode,expected", [("chunks", 413), ("timeout", 408), ("disconnect", None)])
def test_guard_stops_chunked_oversize_slow_and_disconnected_bodies(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    expected: int | None,
) -> None:
    original_timeout = asyncio.timeout
    monkeypatch.setattr(asyncio, "timeout", lambda _: original_timeout(0.01))
    messages: list[Message] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        pytest.fail("Rejected body reached application")

    async def receive() -> Message:
        if mode == "timeout":
            await asyncio.sleep(1)
        if mode == "disconnect":
            return {"type": "http.disconnect"}
        return {"type": "http.request", "body": b"x" * 3000, "more_body": True}

    async def send(message: Message) -> None:
        messages.append(message)

    scope: Scope = {
        "type": "http",
        "path": "/api/v1/identification/barcode-lookups",
        "method": "POST",
        "client": ("test", 1),
        "state": {"request_id": "test-id"},
        "app": SimpleNamespace(state=SimpleNamespace(barcode_budget=budget.BarcodeBudget())),
    }
    asyncio.run(budget.BarcodeRequestGuard(app)(scope, receive, send))
    if expected is None:
        assert messages == []
    else:
        assert messages[0]["status"] == expected
