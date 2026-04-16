from __future__ import annotations

from pydantic import BaseModel


class StatusItem(BaseModel):
    id: int
    name: str | None = None

