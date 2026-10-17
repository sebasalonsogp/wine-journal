from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Score = Annotated[float, Field(ge=1, le=5, multiple_of=0.5, strict=True)]


class RatingChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = Field(ge=0, strict=True)
    score: Score | None


class RatingState(BaseModel):
    score: Score | None
    version: int


class RatingHistoryItem(RatingState):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    changed_at: datetime


class RatingHistory(BaseModel):
    items: list[RatingHistoryItem]
    nextBeforeVersion: int | None
