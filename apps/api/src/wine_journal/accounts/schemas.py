from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BootstrapAccount(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    state: Literal["ACTIVE", "DISABLED"]
    created_at: datetime = Field(serialization_alias="createdAt")
