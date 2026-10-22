"""Conservative R03 experiment, not an application recognition contract."""

import csv
import io
import math
import re
import unicodedata
from urllib.parse import urlparse


def tokens(text: str) -> set[str]:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return set(re.findall(r"[a-z0-9]+", folded.encode("ascii", "ignore").decode()))


def read_words(tsv: bytes) -> tuple[str, float | None]:
    """Use word confidence only as an OCR filter, never as identity probability."""
    if len(tsv) > 262144:
        raise ValueError("OCR output too large")
    rows = csv.DictReader(io.StringIO(tsv.decode("utf-8")), delimiter="\t")
    if not {"level", "conf", "text"} <= set(rows.fieldnames or []):
        raise ValueError("Malformed OCR output")
    accepted: list[str] = []
    confidences: list[float] = []
    for index, row in enumerate(rows):
        if index >= 4096:
            raise ValueError("Too many OCR rows")
        if None in row or any(value is None for value in row.values()):
            raise ValueError("Malformed OCR row")
        if row["level"] != "5" or not row["text"]:
            continue
        confidence = float(row["conf"])
        if not math.isfinite(confidence) or not 0 <= confidence <= 100:
            raise ValueError("Invalid word confidence")
        confidences.append(confidence)
        if confidence >= 60:
            accepted.append(row["text"])
    text = " ".join(accepted)
    if len(text) > 16384:
        raise ValueError("OCR text too long")
    return text, round(sum(confidences) / len(confidences), 2) if confidences else None


def candidates(text: str, catalog: list[dict[str, str]]) -> list[str]:
    """Require producer evidence + >=80% wine-name tokens; retain every vintage."""
    seen = tokens(text)
    compact = "".join(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", text.casefold())))
    matches = []
    for wine in catalog:
        producer = re.sub(r"[^a-z0-9]", "", wine["producer"].casefold())
        host = re.sub(
            r"[^a-z0-9]", "", (urlparse(wine["source_url"]).hostname or "").removeprefix("www.")
        )
        name = tokens(wine["wine_name"])
        if (producer and producer in compact or host and host in compact) and name:
            if len(name & seen) / len(name) >= 0.8:
                matches.append(wine["fixture_id"])
    return sorted(matches)


def year_tokens(text: str) -> list[int]:
    # Founding/bottling years remain observations, never a vintage selection.
    return sorted({int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", text)})
