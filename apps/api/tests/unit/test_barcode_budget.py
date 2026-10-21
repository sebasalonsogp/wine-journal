from concurrent.futures import ThreadPoolExecutor

import pytest

from wine_journal.core.errors import ApiError
from wine_journal.identification import budget


def test_global_limit_expiry_and_bounded_peer_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [100.0]
    monkeypatch.setattr(budget, "monotonic", lambda: now[0])
    guard = budget.BarcodeBudget()
    for i in range(120):
        guard.consume(str(i))
    with pytest.raises(ApiError) as error:
        guard.consume("new")
    assert error.value.status == 429 and error.value.retry_after == 60
    assert len(guard.peers) == 120
    now[0] += 60
    guard.consume("new")
    assert list(guard.peers) == ["new"]


def test_parallel_requests_cannot_exceed_peer_budget() -> None:
    guard = budget.BarcodeBudget()

    def consume(_: int) -> bool:
        try:
            guard.consume("same-peer")
            return True
        except ApiError:
            return False

    with ThreadPoolExecutor(max_workers=8) as executor:
        assert sum(executor.map(consume, range(60))) == 30
