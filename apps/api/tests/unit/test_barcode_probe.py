import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from wine_journal.identification.gtin import canonical_gtin
from wine_journal.integrations.barcode_probe import BASE_URL, ProbeResult, probe_product

CODE = "089121288122"
CANONICAL = "00089121288122"
FOUND = {
    "code": "0089121288122",
    "status": "success_with_warnings",
    "result": {"id": "product_found"},
    "product": {"code": "0089121288122", "product_name": "Cabernet Sauvignon", "brands": "J. Lohr"},
}
ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("code", [CODE, "0089121288122", CANONICAL])
def test_gtin_padding_preserves_the_package_identity(code: str) -> None:
    assert canonical_gtin(code) == CANONICAL


@pytest.mark.parametrize("code", ["96385074", "036000291452", "4006381333931", "10089121288129"])
def test_all_supported_lengths_have_valid_check_digits(code: str) -> None:
    assert canonical_gtin(code) == code.zfill(14)


@pytest.mark.parametrize(
    "code",
    [
        None,
        89121288122,
        True,
        "",
        "089121288123",
        "89121288122",
        " 089121288122",
        "089121288122 ",
        "089121-288122",
        "０８９１２１２８８１２２",
        "00000000000000",
        "089121288122\n",
    ],
)
def test_invalid_codes_are_rejected_before_network(code: object) -> None:
    with pytest.raises(ValueError):
        canonical_gtin(code)


class Chunks(httpx.AsyncByteStream):
    def __init__(self, raw: bytes):
        self.raw = raw

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.raw


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (200, FOUND, "PRODUCT_FOUND_UNVERIFIED"),
        (404, {"code": CODE, "result": {"id": "product_not_found"}}, "NOT_FOUND"),
        (404, {"error": "proxy not found"}, "INVALID_RESPONSE"),
        (200, {**FOUND, "code": "089121068823"}, "INVALID_RESPONSE"),
        (
            200,
            {**FOUND, "product": {"code": "089121068823", "product_name": "Other"}},
            "INVALID_RESPONSE",
        ),
        (200, {**FOUND, "product": {"code": CODE, "product_name": "  "}}, "INVALID_RESPONSE"),
        (200, {**FOUND, "status": "error"}, "INVALID_RESPONSE"),
        (200, {**FOUND, "result": []}, "INVALID_RESPONSE"),
        (200, {**FOUND, "product": {"code": CODE, "product_name": "x" * 201}}, "INVALID_RESPONSE"),
        (200, [], "INVALID_RESPONSE"),
        (429, {}, "RATE_LIMITED"),
        (503, {}, "UNAVAILABLE"),
        (302, {}, "UNAVAILABLE"),
    ],
)
def test_bounded_provider_outcomes(status: int, body: object, expected: str) -> None:
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert str(request.url).startswith(BASE_URL + CODE)
        assert request.headers["User-Agent"].startswith("WineJournalEvaluation/")
        assert request.headers["Accept-Encoding"] == "identity"
        assert "authorization" not in request.headers
        return httpx.Response(
            status,
            headers={"content-type": "application/json"},
            stream=Chunks(json.dumps(body).encode()),
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            result = await probe_product(client, CODE)
        assert result.status == expected
        if result.product:
            assert result.product.model_dump() == {
                "code": "0089121288122",
                "product_name": "Cabernet Sauvignon",
                "brands": "J. Lohr",
                "quantity": None,
            }
            assert not hasattr(result.product, "year")

    asyncio.run(run())
    assert len(requests) == 1


@pytest.mark.parametrize(
    ("raw", "headers"),
    [
        (b"x" * 65537, {"content-type": "application/json"}),
        (b"not JSON", {"content-type": "application/json"}),
        (b"\xff", {"content-type": "application/json"}),
        (b"[" * 2000, {"content-type": "application/json"}),
        (b"<html>", {"content-type": "text/html"}),
        (b"compressed", {"content-type": "application/json", "content-encoding": "gzip"}),
    ],
    ids=["oversized", "not-json", "bad-utf8", "deep-json", "html", "encoded"],
)
def test_untrusted_response_limits(raw: bytes, headers: dict[str, str]) -> None:
    async def run() -> None:
        transport = httpx.MockTransport(
            lambda _: httpx.Response(200, headers=headers, stream=Chunks(raw))
        )
        async with httpx.AsyncClient(transport=transport) as client:
            assert (await probe_product(client, CODE)).status == "INVALID_RESPONSE"

    asyncio.run(run())


def test_provider_timeout_and_invalid_input_do_not_retry() -> None:
    calls = 0

    async def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        await asyncio.sleep(1)
        raise AssertionError("Deadline should cancel the request")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with pytest.raises(ValueError):
                await probe_product(client, "bad")
            assert calls == 0
            timeout = asyncio.timeout
            with patch(
                "wine_journal.integrations.barcode_probe.asyncio.timeout", lambda _: timeout(0.01)
            ):
                assert (await probe_product(client, CODE)).status == "TIMEOUT"
            assert calls == 1

    asyncio.run(run())


def test_preflight_groups_codes_without_calls_or_release_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from evaluate_barcode import evaluate, load_observations

    observations = load_observations(ROOT / "assets/evaluation/barcode-observations.json")
    with patch(
        "evaluate_barcode.probe_product", side_effect=AssertionError("Offline mode made a request")
    ):
        report = asyncio.run(evaluate(observations, False))
    assert report["source_observations"] == 2 and report["distinct_package_codes"] == 1
    assert report["confirmed_wine_releases"] == 0
    assert report["requested_package_codes"] == 0
    assert report["camera_decoding_tested"] is False
    assert report["results"] == [
        {
            "canonical_gtin": CANONICAL,
            "sample_ids": ["B001", "B002"],
            "expected_fixture_ids": ["W015", "W016"],
            "status": "NOT_REQUESTED",
        }
    ]


def test_bad_manifest_is_rejected_before_evaluation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from evaluate_barcode import load_observations

    source = json.loads((ROOT / "assets/evaluation/barcode-observations.json").read_text())
    path = tmp_path / "observations.json"
    invalid: list[dict[str, object]] = [
        {"gtin": 89121288122},
        {"expected_fixture_ids": ["W999"]},
        {"source_url": "https://name:credential@example.test"},
        {"retrieved_on": "2999-01-01"},
        {"evidence_status": "CAMERA_VERIFIED"},
    ]
    for changes in invalid:
        path.write_text(json.dumps([{**source[0], **changes}]))
        with pytest.raises(ValueError):
            load_observations(path)
    path.write_text(json.dumps([source[0], source[0]]))
    with pytest.raises(ValueError):
        load_observations(path)


def test_rate_limit_stops_the_batch_and_counts_unattempted_codes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    from evaluate_barcode import evaluate, load_observations

    observations = load_observations(ROOT / "assets/evaluation/barcode-observations.json")
    observations.append(
        observations[0].model_copy(update={"sample_id": "B003", "gtin": "089121068823"})
    )
    with patch(
        "evaluate_barcode.probe_product", return_value=ProbeResult(status="RATE_LIMITED")
    ) as probe:
        report = asyncio.run(evaluate(observations, True))
    assert probe.call_count == 1
    assert report["requested_package_codes"] == 1
    assert report["unrequested_package_codes"] == 1
