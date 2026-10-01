from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class ManualWine(BaseModel):
    model_config = ConfigDict(extra="forbid", alias_generator=to_camel, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    producer: str | None = Field(default=None, min_length=1, max_length=200)
    vintage_status: Literal["YEAR", "NON_VINTAGE", "MULTI_VINTAGE", "UNKNOWN"] = "UNKNOWN"
    year: int | None = Field(default=None, ge=1000, le=9999, strict=True)
    edition: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def valid_vintage(self) -> Self:
        if (self.vintage_status == "YEAR") != (self.year is not None):
            raise ValueError("A year is required only when vintage status is YEAR.")
        return self
