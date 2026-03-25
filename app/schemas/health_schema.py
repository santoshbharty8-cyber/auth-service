from pydantic import BaseModel
from typing import Dict


class HealthResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    checks: Dict[str, bool]