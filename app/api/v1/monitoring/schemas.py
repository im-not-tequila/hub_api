from __future__ import annotations

import datetime
from enum import StrEnum

from pydantic import BaseModel
from pydantic import ConfigDict


class ArrivalStatus(StrEnum):
    BEFORE_SHIFT_START = "BEFORE_SHIFT_START"
    WITHIN_GRACE_PERIOD = "WITHIN_GRACE_PERIOD"
    LATE = "LATE"


class WorkScheduleType(StrEnum):
    DEFAULT = "DEFAULT"
    CUSTOM = "CUSTOM"


class TutorListItem(BaseModel):
    platonus_id: int
    user_id: int | None = None
    lastname: str | None = None
    firstname: str | None = None
    patronomic: str | None = None
    absence_status: str | None = None
    structural_subdivision_id: int | None = None
    structural_subdivision_name: str | None = None
    rate: float | None = None
    position_name: str | None = None


class TutorAcademicPositionRateItem(BaseModel):
    cafedra_id: int | None = None
    cafedra_name: str | None = None
    position_name: str | None = None
    rate: float | None = None


class TutorAcademicListItem(BaseModel):
    platonus_id: int
    user_id: int | None = None
    lastname: str | None = None
    firstname: str | None = None
    patronomic: str | None = None
    positions: list[TutorAcademicPositionRateItem]


class TutorDetailItem(BaseModel):
    iin: str | None = None
    platonus_id: int
    user_id: int | None = None
    lastname: str | None = None
    firstname: str | None = None
    patronomic: str | None = None
    absence_status: str | None = None
    structural_subdivision_name: str | None = None
    mobile_phone: str | None = None
    is_married: int | None = None
    address: str | None = None
    birth_date: datetime.date | None = None
    rate: float | None = None
    nationality: str | None = None
    position_name: str | None = None


class TutorAcademicDetailItem(BaseModel):
    iin: str | None = None
    platonus_id: int
    user_id: int | None = None
    lastname: str | None = None
    firstname: str | None = None
    patronomic: str | None = None
    mobile_phone: str | None = None
    is_married: int | None = None
    address: str | None = None
    birth_date: datetime.date | None = None
    nationality: str | None = None
    positions: list[TutorAcademicPositionRateItem]


class PersonControlItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    controlid: int
    personid: int
    createdate: datetime.datetime
    turniketid: int
    inoutdata: str
    role: str
    repl: int
    type: str | None = None
    shir: float | None = None
    dolg: float | None = None


class EmployeeAccessLogItem(BaseModel):
    control_name: str
    createdate: datetime.datetime
    inoutdata: str


class TutorFirstInItem(BaseModel):
    platonus_id: int | None = None
    user_id: int | None = None
    lastname: str | None = None
    firstname: str | None = None
    patronomic: str | None = None
    absence_status: str | None = None
    structural_subdivision_name: str | None = None
    position_name: str | None = None
    createdate: datetime.datetime | None = None
    arrival_status: ArrivalStatus | None = None
    perco_status_name: str | None = None
    work_schedule: str | None = None
    work_schedule_type: WorkScheduleType | None = None


class TutorAcademicFirstInItem(BaseModel):
    platonus_id: int
    user_id: int | None = None
    lastname: str | None = None
    firstname: str | None = None
    patronomic: str | None = None
    createdate: datetime.datetime | None = None
    arrival_status: ArrivalStatus | None = None
    perco_status_name: str | None = None
    positions: list[TutorAcademicPositionRateItem]


class EmployeePunctualityStatsItem(BaseModel):
    platonus_id: int
    user_id: int | None = None
    full_name: str
    structural_subdivision_id: int | None = None
    structural_subdivision_name: str | None = None
    position_name: str | None = None
    before_shift_start_count: int
    within_grace_period_count: int
    late_count: int
    no_show_count: int
    working_hours: float


class EmployeeWorkScheduleItem(BaseModel):
    id: int
    user_id: int
    start_date: datetime.date
    end_date: datetime.date | None = None
    work_start_time: datetime.time
    work_end_time: datetime.time


class EmployeeWorkScheduleCreateUpdate(BaseModel):
    start_date: datetime.date
    end_date: datetime.date | None = None
    work_start_time: datetime.time
    work_end_time: datetime.time

