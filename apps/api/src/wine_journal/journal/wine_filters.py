import base64
import hashlib
import json
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wine_journal.core.errors import ApiError

WineSort = Literal["LAST_CONSUMED", "NAME", "RATING"]
RatingFilter = Literal["ALL", "RATED", "UNRATED"]
VintageFilter = Literal["ALL", "YEAR", "NON_VINTAGE", "MULTI_VINTAGE", "UNKNOWN"]
SortValue = date | str | int | None


class WineFilters(BaseModel):
    model_config = ConfigDict(frozen=True)

    q: str = Field(default="", max_length=200, pattern=r"^[^\x00]*$")
    sort: WineSort = "LAST_CONSUMED"
    rating: RatingFilter = "ALL"
    vintage: VintageFilter = "ALL"

    @field_validator("q")
    @classmethod
    def normalize_search(cls, value: str) -> str:
        return " ".join(value.split())

    def scope(self, owner: UUID) -> str:
        # Bind a cursor to its owner and complete filter set without repeating search text.
        return hashlib.sha256(f"{owner}:{self.model_dump_json()}".encode()).hexdigest()


def encode_wine_cursor(
    filters: WineFilters, owner: UUID, value: SortValue, identifier: UUID
) -> str:
    payload = [
        filters.scope(owner),
        value.isoformat() if isinstance(value, date) else value,
        str(identifier),
    ]
    return base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode()


def decode_wine_cursor(cursor: str, filters: WineFilters, owner: UUID) -> tuple[SortValue, UUID]:
    try:
        if len(cursor) > 2048:
            raise ValueError
        payload = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if not isinstance(payload, list) or len(payload) != 3 or payload[0] != filters.scope(owner):
            raise ValueError
        value = payload[1]
        if filters.sort == "NAME":
            if not isinstance(value, str) or not 1 <= len(value) <= 400 or "\x00" in value:
                raise ValueError
        elif filters.sort == "RATING":
            if value is not None and (type(value) is not int or not 2 <= value <= 10):
                raise ValueError
        elif value is not None:
            if not isinstance(value, str):
                raise ValueError
            value = date.fromisoformat(value)
        return value, UUID(payload[2])
    except (ValueError, TypeError, AttributeError):
        raise ApiError(422, "INVALID_CURSOR", "Reload this list to continue.") from None
