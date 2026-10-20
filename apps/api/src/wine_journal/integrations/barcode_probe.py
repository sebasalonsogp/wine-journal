"""Read-only feasibility probe, not a production identification provider."""

import asyncio
import json
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from wine_journal.identification.gtin import canonical_gtin

BASE_URL = "https://world.openfoodfacts.org/api/v3/product/"
USER_AGENT = "WineJournalEvaluation/0.1 (https://github.com/sebasalonsogp/wine-journal)"
MAX_RESPONSE_BYTES = 65536


class ProductFacts(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True, strict=True)

    code: str = Field(max_length=14)
    product_name: str = Field(min_length=1, max_length=200)
    brands: str | None = Field(default=None, max_length=200)
    quantity: str | None = Field(default=None, max_length=100)


class ProbeResult(BaseModel):
    status: Literal[
        "PRODUCT_FOUND_UNVERIFIED",
        "NOT_FOUND",
        "RATE_LIMITED",
        "UNAVAILABLE",
        "INVALID_RESPONSE",
        "TIMEOUT",
    ]
    product: ProductFacts | None = None


def parse_product(raw: bytes, requested: str, http_status: int) -> ProbeResult:
    try:
        body = json.loads(raw)
        if not isinstance(body, dict) or canonical_gtin(body.get("code")) != requested:
            raise ValueError
        result = body.get("result")
        if not isinstance(result, dict):
            raise ValueError
        if http_status == 404 and result.get("id") == "product_not_found":
            return ProbeResult(status="NOT_FOUND")
        if http_status != 200 or body.get("status") not in ("success", "success_with_warnings"):
            raise ValueError
        if result.get("id") != "product_found":
            raise ValueError
        product = ProductFacts.model_validate(body.get("product"))
        if canonical_gtin(product.code) != requested:
            raise ValueError
        return ProbeResult(status="PRODUCT_FOUND_UNVERIFIED", product=product)
    except (ValueError, TypeError, RecursionError, ValidationError):
        return ProbeResult(status="INVALID_RESPONSE")


async def probe_product(client: httpx.AsyncClient, code: str) -> ProbeResult:
    canonical = canonical_gtin(code)  # Reject invalid input before any network activity.
    try:
        async with asyncio.timeout(10):
            async with client.stream(
                "GET",
                BASE_URL + code,
                params={"fields": "code,product_name,brands,quantity"},
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                    "Accept-Encoding": "identity",
                },
                follow_redirects=False,
                timeout=5,
            ) as response:
                if response.status_code == 429:
                    return ProbeResult(status="RATE_LIMITED")
                if response.status_code not in (200, 404):
                    return ProbeResult(status="UNAVAILABLE")
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    return ProbeResult(status="INVALID_RESPONSE")
                if "application/json" not in response.headers.get("content-type", "").lower():
                    return ProbeResult(status="INVALID_RESPONSE")
                data = bytearray()
                async for chunk in response.aiter_raw(chunk_size=8192):
                    if len(data) + len(chunk) > MAX_RESPONSE_BYTES:
                        return ProbeResult(status="INVALID_RESPONSE")
                    data.extend(chunk)
                return parse_product(bytes(data), canonical, response.status_code)
    except (TimeoutError, httpx.TimeoutException):
        return ProbeResult(status="TIMEOUT")
    except httpx.HTTPError:
        return ProbeResult(status="UNAVAILABLE")
