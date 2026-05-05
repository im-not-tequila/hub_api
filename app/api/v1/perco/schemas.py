from __future__ import annotations

import datetime

from pydantic import BaseModel


class StatusItem(BaseModel):
    id: int
    name: str | None = None


class ControlItem(BaseModel):
    turniket_id: int
    name: str
    address: str
    lat: float
    lng: float


class PersonControlItem(BaseModel):
    control_id: int
    person_id: int
    create_date: datetime.datetime
    turniket_id: int
    event_type: str
    role: str
    type: str | None = None

    control_name: str | None = None
    control_address: str | None = None
    control_lat: float | None = None
    control_lng: float | None = None

