from pydantic import BaseModel
from typing import Any


class JobCreateRequest(BaseModel):
    title: str
    raw_description: str


class JobResponse(BaseModel):
    id: int
    title: str
    raw_description: str
    rubric: list[dict[str, Any]]

    class Config:
        from_attributes = True