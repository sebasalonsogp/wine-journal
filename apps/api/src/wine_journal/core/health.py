from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class LivenessResponse(BaseModel):
    status: Literal["ok"] = "ok"


@router.get("/live", operation_id="get_liveness")
def get_liveness() -> LivenessResponse:
    """Check process liveness only; does not claim database/provider readiness."""
    return LivenessResponse()
