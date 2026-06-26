from __future__ import annotations

import datetime

import pandas as pd
from fastapi import HTTPException

from app.api.v1.monitoring.schemas import (
    ArrivalStatus,
    EmployeePunctualityStatsItem,
    TutorAcademicFirstInItem,
    TutorAcademicPositionRateItem,
    TutorFirstInItem,
    WorkScheduleType,
)
from app.services.monitoring.helpers import (
    build_full_name,
    localize_absence_status,
    normalize_name_part,
    uppercase_first,
)


class MonitoringPunctualityMixin:
    @staticmethod
    def _build_academic_position_item(
        *,
        cafedra_id: object,
        cafedra_name: object,
        position_name: object,
        rate: object,
    ) -> TutorAcademicPositionRateItem:
        return TutorAcademicPositionRateItem.model_validate(
            {
                "cafedra_id": cafedra_id,
                "cafedra_name": uppercase_first(cafedra_name),  # type: ignore[arg-type]
                "position_name": uppercase_first(position_name),  # type: ignore[arg-type]
                "rate": float(rate) if rate is not None else None,
            }
        )

    async def list_academic_punctuality(
        self,
        *,
        startdate: datetime.date | None,
        enddate: datetime.date | None,
    ) -> list[TutorAcademicFirstInItem]:
        if self.session_perco is None:
            raise RuntimeError("Perco session is required")
        if self.session_nitro is None or self.session_postgres is None:
            raise RuntimeError("Nitro and Postgres sessions are required")

        if startdate is None:
            startdate = datetime.date.today()
        if enddate is None:
            enddate = datetime.date.today()

        start_dt = datetime.datetime.combine(startdate, datetime.time.min).replace(microsecond=0)
        end_dt = datetime.datetime.combine(enddate, datetime.time(23, 59, 0)).replace(microsecond=0)
        first_in_rows = await self._monitoring_dao().get_academic_first_in_rows(
            start_dt=start_dt,
            end_dt=end_dt,
        )
        active_academic_rows = await self._load_active_academic_rows()

        first_in_by_platonus: dict[int, dict[str, object]] = {}
        for row in first_in_rows:
            pid_raw = row.get("platonus_id")
            if pid_raw is None:
                continue
            pid = int(pid_raw)
            if pid not in first_in_by_platonus:
                first_in_by_platonus[pid] = {
                    "platonus_id": pid,
                    "lastname": row.get("lastname"),
                    "firstname": row.get("firstname"),
                    "patronomic": row.get("patronomic"),
                    "createdate": row.get("createdate"),
                    "perco_status_name": row.get("perco_status_name"),
                    "positions": [],
                }
            first_in_by_platonus[pid]["positions"].append(
                self._build_academic_position_item(
                    cafedra_id=row.get("cafedra_id"),
                    cafedra_name=row.get("cafedra_name_ru"),
                    position_name=row.get("position_name_ru"),
                    rate=row.get("rate"),
                )
            )

        active_by_platonus: dict[int, dict[str, object]] = {}
        for row in active_academic_rows:
            pid_raw = row.get("platonus_id")
            if pid_raw is None:
                continue
            pid = int(pid_raw)
            if pid not in active_by_platonus:
                active_by_platonus[pid] = {
                    "platonus_id": pid,
                    "lastname": row.get("lastname"),
                    "firstname": row.get("firstname"),
                    "patronomic": row.get("patronomic"),
                    "positions": [],
                }
            active_by_platonus[pid]["positions"].append(
                self._build_academic_position_item(
                    cafedra_id=row.get("cafedra_id"),
                    cafedra_name=row.get("cafedra_name_ru"),
                    position_name=row.get("position_name_ru"),
                    rate=row.get("rate"),
                )
            )

        platonus_ids = sorted(set(first_in_by_platonus) | set(active_by_platonus))
        user_by_platonus = await self._platonus_to_user_id_map(platonus_ids)
        user_ids = [uid for uid in user_by_platonus.values() if uid is not None]
        schedules_by_user = await self._load_custom_schedules(
            user_ids=user_ids,
            start_date=startdate,
            end_date=enddate,
        )

        data: list[TutorAcademicFirstInItem] = []
        for platonus_id in platonus_ids:
            first_in_item = first_in_by_platonus.get(platonus_id)
            active_item = active_by_platonus.get(platonus_id)
            base_item = first_in_item or active_item
            if base_item is None:
                continue

            createdate = base_item.get("createdate")
            user_id = user_by_platonus.get(platonus_id)
            if isinstance(createdate, datetime.datetime):
                shift_start_time, _, _ = self._resolve_schedule(
                    user_id=user_id,
                    access_date=createdate.date(),
                    schedules_by_user=schedules_by_user,
                )
                arrival_status = self._calculate_arrival_status(
                    first_in_datetime=createdate,
                    shift_start_time=shift_start_time,
                )
            else:
                arrival_status = None

            item = {
                "platonus_id": platonus_id,
                "user_id": user_id,
                "lastname": normalize_name_part(base_item.get("lastname")),  # type: ignore[arg-type]
                "firstname": normalize_name_part(base_item.get("firstname")),  # type: ignore[arg-type]
                "patronomic": normalize_name_part(base_item.get("patronomic")),  # type: ignore[arg-type]
                "createdate": createdate if isinstance(createdate, datetime.datetime) else None,
                "arrival_status": arrival_status,
                "perco_status_name": (
                    first_in_item.get("perco_status_name") or "—"
                    if first_in_item is not None
                    else "—"
                ),
                "positions": (
                    active_item.get("positions")
                    if active_item is not None
                    else base_item.get("positions")
                )
                or [],
            }
            data.append(TutorAcademicFirstInItem.model_validate(item))

        return sorted(
            data,
            key=lambda item: build_full_name(
                lastname=item.lastname,
                firstname=item.firstname,
                patronomic=item.patronomic,
            ),
        )

    async def list_staff_punctuality(
        self,
        *,
        startdate: datetime.date | None,
        enddate: datetime.date | None,
    ) -> list[TutorFirstInItem]:
        if self.session_perco is None:
            raise RuntimeError("Perco session is required")
        if self.session_nitro is None or self.session_postgres is None:
            raise RuntimeError("Nitro and Postgres sessions are required")

        if startdate is None:
            startdate = datetime.date.today()
        if enddate is None:
            enddate = datetime.date.today()

        start_dt = datetime.datetime.combine(startdate, datetime.time.min).replace(microsecond=0)
        end_dt = datetime.datetime.combine(enddate, datetime.time(23, 59, 0)).replace(microsecond=0)
        first_in_rows = await self._monitoring_dao().get_staff_first_in_rows(
            start_dt=start_dt,
            end_dt=end_dt,
        )
        active_staff_rows = await self._load_active_staff_rows()
        active_staff_by_platonus: dict[int, dict[str, object]] = {}
        for staff_row in active_staff_rows:
            pid = staff_row.get("platonus_id")
            if pid is None:
                continue
            active_staff_by_platonus[int(pid)] = staff_row

        existing_platonus_ids: set[int] = set()
        merged_rows: list[dict[str, object]] = []
        for row in first_in_rows:
            pid = row.get("platonus_id")
            if pid is None:
                continue
            ipid = int(pid)
            staff_row = active_staff_by_platonus.get(ipid)
            if staff_row is not None and row.get("absence_status") is None:
                row["absence_status"] = staff_row.get("absence_status")
            if staff_row is not None and row.get("rate") is None:
                row["rate"] = staff_row.get("rate")
            existing_platonus_ids.add(ipid)
            merged_rows.append(row)

        for staff_row in active_staff_rows:
            pid = staff_row.get("platonus_id")
            if pid is None:
                continue
            ipid = int(pid)
            if ipid in existing_platonus_ids:
                continue
            merged_rows.append(
                {
                    "platonus_id": ipid,
                    "lastname": staff_row.get("lastname"),
                    "firstname": staff_row.get("firstname"),
                    "patronomic": staff_row.get("patronomic"),
                    "absence_status": staff_row.get("absence_status"),
                    "structural_subdivision_name": staff_row.get("structural_subdivision_name"),
                    "position_name": staff_row.get("position_name"),
                    "rate": staff_row.get("rate"),
                    "createdate": None,
                    "perco_status_name": "—",
                }
            )

        platonus_ids = [
            int(row["platonus_id"])
            for row in merged_rows
            if row.get("platonus_id") is not None
        ]
        user_by_platonus = await self._platonus_to_user_id_map(platonus_ids)
        user_ids = [uid for uid in user_by_platonus.values() if uid is not None]
        schedules_by_user = await self._load_custom_schedules(
            user_ids=user_ids,
            start_date=startdate,
            end_date=enddate,
        )

        data: list[dict[str, object]] = []
        for row in merged_rows:
            item = dict(row)
            pid = item.get("platonus_id")
            user_id = user_by_platonus.get(int(pid)) if pid is not None else None
            item["user_id"] = user_id
            createdate = item.get("createdate")
            if isinstance(createdate, datetime.datetime):
                shift_start_time, shift_end_time, is_custom_schedule = self._resolve_schedule(
                    user_id=user_id,
                    access_date=createdate.date(),
                    schedules_by_user=schedules_by_user,
                )
                item["arrival_status"] = self._calculate_arrival_status(
                    first_in_datetime=createdate,
                    shift_start_time=shift_start_time,
                )
                item["work_schedule"] = (
                    f"{self._format_time(shift_start_time)} - {self._format_time(shift_end_time)}"
                )
                item["work_schedule_type"] = "CUSTOM" if is_custom_schedule else "DEFAULT"
            else:
                shift_start_time, shift_end_time, is_custom_schedule = self._resolve_schedule(
                    user_id=user_id,
                    access_date=enddate,
                    schedules_by_user=schedules_by_user,
                )
                item["arrival_status"] = None
                item["work_schedule"] = (
                    f"{self._format_time(shift_start_time)} - {self._format_time(shift_end_time)}"
                )
                item["work_schedule_type"] = "CUSTOM" if is_custom_schedule else "DEFAULT"
            item["lastname"] = normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
            item["firstname"] = normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
            item["patronomic"] = normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
            item["absence_status"] = localize_absence_status(item.get("absence_status"), "ru")  # type: ignore[arg-type]
            item["structural_subdivision_name"] = uppercase_first(  # type: ignore[arg-type]
                item.get("structural_subdivision_name")
            )
            item["position_name"] = uppercase_first(item.get("position_name"))  # type: ignore[arg-type]
            item["rate"] = float(item.get("rate")) if item.get("rate") is not None else None
            data.append(item)

        return [TutorFirstInItem.model_validate(item) for item in data]

    async def export_staff_punctuality_excel(
        self,
        *,
        startdate: datetime.date | None,
        enddate: datetime.date | None,
        arrival_status: str | None,
        schedule_type: str | None,
        perco_status_name: str | None,
        search: str | None,
    ) -> bytes:
        rows = await self.list_staff_punctuality(startdate=startdate, enddate=enddate)

        filtered_rows = rows
        status_filter = (arrival_status or "ALL").strip()
        if status_filter != "ALL":
            if status_filter == "ABSENT":
                filtered_rows = [
                    row for row in filtered_rows if row.createdate is None or row.arrival_status is None
                ]
            else:
                try:
                    arrival_status_enum = ArrivalStatus(status_filter)
                except ValueError:
                    arrival_status_enum = None
                if arrival_status_enum is not None:
                    filtered_rows = [row for row in filtered_rows if row.arrival_status == arrival_status_enum]

        schedule_filter = (schedule_type or "ALL").strip()
        if schedule_filter != "ALL":
            try:
                schedule_type_enum = WorkScheduleType(schedule_filter)
            except ValueError:
                schedule_type_enum = None
            if schedule_type_enum is not None:
                filtered_rows = [
                    row
                    for row in filtered_rows
                    if (row.work_schedule_type or WorkScheduleType.DEFAULT) == schedule_type_enum
                ]

        perco_filter = (perco_status_name or "ALL").strip()
        if perco_filter != "ALL":
            filtered_rows = [row for row in filtered_rows if (row.perco_status_name or "") == perco_filter]

        query = (search or "").strip().lower()
        if query:

            def _matches_search(row: TutorFirstInItem) -> bool:
                full_name = build_full_name(
                    lastname=row.lastname,
                    firstname=row.firstname,
                    patronomic=row.patronomic,
                ).lower()
                dept = (row.structural_subdivision_name or "").lower()
                status = str(row.arrival_status or "").lower()
                perco_status = str(row.perco_status_name or "").lower()
                schedule = str(row.work_schedule or "").lower()
                return (
                    query in full_name
                    or query in dept
                    or query in status
                    or query in perco_status
                    or query in schedule
                )

            filtered_rows = [row for row in filtered_rows if _matches_search(row)]

        prepared_rows: list[dict[str, object]] = []
        for row in filtered_rows:
            prepared_rows.append(
                {
                    "TutorID": row.platonus_id,
                    "ФИО": build_full_name(
                        lastname=row.lastname,
                        firstname=row.firstname,
                        patronomic=row.patronomic,
                    ),
                    "Подразделение": row.structural_subdivision_name,
                    "Должность": row.position_name,
                    "Ставка": row.rate,
                    "Статус": row.absence_status or "Штатный режим",
                    "Дата первого входа": (
                        row.createdate.strftime("%Y-%m-%d %H:%M:%S")
                        if isinstance(row.createdate, datetime.datetime)
                        else None
                    ),
                    "Статус PERCo": row.perco_status_name,
                    "График работы": row.work_schedule,
                }
            )

        prepared_rows.sort(key=lambda row: str(row.get("ФИО") or ""))
        columns = [
            "TutorID",
            "ФИО",
            "Подразделение",
            "Должность",
            "Ставка",
            "Статус",
            "Дата первого входа",
            "Статус PERCo",
            "График работы",
        ]
        df = pd.DataFrame(prepared_rows, columns=columns)
        html_table = df.to_html(index=False, na_rep="", border=1, justify="left")
        html_doc = f"""<html>
<head><meta charset="utf-8" /></head>
<body>{html_table}</body>
</html>"""
        return html_doc.encode("utf-8-sig")

    async def get_employee_punctuality_stats(
        self,
        *,
        platonus_id: int,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> EmployeePunctualityStatsItem:
        if self.session_perco is None:
            raise RuntimeError("Perco session is required")
        if self.session_nitro is None or self.session_postgres is None:
            raise RuntimeError("Nitro and Postgres sessions are required")
        if end_date < start_date:
            raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")
        staff_row = await self._monitoring_dao().get_staff_brief_row(platonus_id)
        if staff_row is None:
            raise HTTPException(status_code=404, detail="Employee not found")

        start_dt = datetime.datetime.combine(start_date, datetime.time.min).replace(microsecond=0)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max).replace(microsecond=0)
        first_in_rows = await self._monitoring_dao().get_employee_first_in_rows_by_day(
            platonus_id=platonus_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        first_in_by_day: dict[datetime.date, datetime.datetime] = {}
        for row in first_in_rows:
            access_date = row.get("access_date")
            first_in_datetime = row.get("first_in_datetime")
            if isinstance(access_date, datetime.date) and isinstance(first_in_datetime, datetime.datetime):
                first_in_by_day[access_date] = first_in_datetime

        working_hours = await self._monitoring_dao().get_working_hours_sum(
            platonus_id=platonus_id,
            start_date=start_date,
            end_date=end_date,
        )

        user_id = await self._user_id_for_tutor(platonus_id)
        schedules_by_user = await self._load_custom_schedules(
            user_ids=[user_id] if user_id is not None else [],
            start_date=start_date,
            end_date=end_date,
        )

        before_shift_start_count = 0
        within_grace_period_count = 0
        late_count = 0
        no_show_count = 0
        for work_day in self._iter_weekdays(start_date, end_date):
            first_in_datetime = first_in_by_day.get(work_day)
            if first_in_datetime is None:
                no_show_count += 1
                continue

            shift_start_time, _, _ = self._resolve_schedule(
                user_id=user_id,
                access_date=work_day,
                schedules_by_user=schedules_by_user,
            )
            arrival_status = self._calculate_arrival_status(
                first_in_datetime=first_in_datetime,
                shift_start_time=shift_start_time,
            )
            if arrival_status == ArrivalStatus.BEFORE_SHIFT_START:
                before_shift_start_count += 1
            elif arrival_status == ArrivalStatus.WITHIN_GRACE_PERIOD:
                within_grace_period_count += 1
            elif arrival_status == ArrivalStatus.LATE:
                late_count += 1

        staff_item = dict(staff_row)
        lastname = normalize_name_part(staff_item.get("lastname"))  # type: ignore[arg-type]
        firstname = normalize_name_part(staff_item.get("firstname"))  # type: ignore[arg-type]
        patronomic = normalize_name_part(staff_item.get("patronomic"))  # type: ignore[arg-type]
        return EmployeePunctualityStatsItem.model_validate(
            {
                "platonus_id": platonus_id,
                "user_id": user_id,
                "full_name": build_full_name(
                    lastname=lastname,
                    firstname=firstname,
                    patronomic=patronomic,
                ),
                "structural_subdivision_id": staff_item.get("structural_subdivision_id"),
                "structural_subdivision_name": uppercase_first(  # type: ignore[arg-type]
                    staff_item.get("structural_subdivision_name")
                ),
                "position_name": uppercase_first(staff_item.get("position_name")),  # type: ignore[arg-type]
                "rate": float(staff_item.get("rate")) if staff_item.get("rate") is not None else None,
                "before_shift_start_count": before_shift_start_count,
                "within_grace_period_count": within_grace_period_count,
                "late_count": late_count,
                "no_show_count": no_show_count,
                "working_hours": round(working_hours, 2),
            }
        )

    async def list_active_employees_punctuality_stats(
        self,
        *,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[EmployeePunctualityStatsItem]:
        if self.session_perco is None:
            raise RuntimeError("Perco session is required")
        if self.session_nitro is None or self.session_postgres is None:
            raise RuntimeError("Nitro and Postgres sessions are required")
        if end_date < start_date:
            raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

        active_staff_rows = await self._load_active_staff_rows()
        if not active_staff_rows:
            return []

        platonus_ids = [
            int(row["platonus_id"])
            for row in active_staff_rows
            if row.get("platonus_id") is not None
        ]
        if not platonus_ids:
            return []

        start_dt = datetime.datetime.combine(start_date, datetime.time.min).replace(microsecond=0)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max).replace(microsecond=0)
        first_in_rows = await self._monitoring_dao().get_first_in_by_person_day(
            platonus_ids=platonus_ids,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        first_in_by_person_day: dict[tuple[int, datetime.date], datetime.datetime] = {}
        for row in first_in_rows:
            personid = row.get("personid")
            access_date = row.get("access_date")
            first_in_datetime = row.get("first_in_datetime")
            if (
                personid is None
                or not isinstance(access_date, datetime.date)
                or not isinstance(first_in_datetime, datetime.datetime)
            ):
                continue
            first_in_by_person_day[(int(personid), access_date)] = first_in_datetime

        working_hours_by_person = await self._monitoring_dao().get_working_hours_by_person(
            platonus_ids=platonus_ids,
            start_date=start_date,
            end_date=end_date,
        )

        user_by_platonus = await self._platonus_to_user_id_map(platonus_ids)
        user_ids = [uid for uid in user_by_platonus.values() if uid is not None]
        schedules_by_user = await self._load_custom_schedules(
            user_ids=user_ids,
            start_date=start_date,
            end_date=end_date,
        )
        work_days = self._iter_weekdays(start_date, end_date)

        items: list[EmployeePunctualityStatsItem] = []
        for staff_row in active_staff_rows:
            pid_raw = staff_row.get("platonus_id")
            if pid_raw is None:
                continue
            platonus_id = int(pid_raw)
            user_id = user_by_platonus.get(platonus_id)

            before_shift_start_count = 0
            within_grace_period_count = 0
            late_count = 0
            no_show_count = 0

            for work_day in work_days:
                first_in_datetime = first_in_by_person_day.get((platonus_id, work_day))
                if first_in_datetime is None:
                    no_show_count += 1
                    continue

                shift_start_time, _, _ = self._resolve_schedule(
                    user_id=user_id,
                    access_date=work_day,
                    schedules_by_user=schedules_by_user,
                )
                arrival_status = self._calculate_arrival_status(
                    first_in_datetime=first_in_datetime,
                    shift_start_time=shift_start_time,
                )
                if arrival_status == ArrivalStatus.BEFORE_SHIFT_START:
                    before_shift_start_count += 1
                elif arrival_status == ArrivalStatus.WITHIN_GRACE_PERIOD:
                    within_grace_period_count += 1
                elif arrival_status == ArrivalStatus.LATE:
                    late_count += 1

            lastname = normalize_name_part(staff_row.get("lastname"))  # type: ignore[arg-type]
            firstname = normalize_name_part(staff_row.get("firstname"))  # type: ignore[arg-type]
            patronomic = normalize_name_part(staff_row.get("patronomic"))  # type: ignore[arg-type]
            items.append(
                EmployeePunctualityStatsItem.model_validate(
                    {
                        "platonus_id": platonus_id,
                        "user_id": user_id,
                        "full_name": build_full_name(
                            lastname=lastname,
                            firstname=firstname,
                            patronomic=patronomic,
                        ),
                        "structural_subdivision_id": staff_row.get("structural_subdivision_id"),
                        "structural_subdivision_name": uppercase_first(  # type: ignore[arg-type]
                            staff_row.get("structural_subdivision_name")
                        ),
                        "position_name": uppercase_first(staff_row.get("position_name")),  # type: ignore[arg-type]
                        "rate": float(staff_row.get("rate")) if staff_row.get("rate") is not None else None,
                        "perco_status_name": staff_row.get("perco_status_name") or "—",
                        "before_shift_start_count": before_shift_start_count,
                        "within_grace_period_count": within_grace_period_count,
                        "late_count": late_count,
                        "no_show_count": no_show_count,
                        "working_hours": round(working_hours_by_person.get(platonus_id, 0.0), 2),
                    }
                )
            )

        return sorted(items, key=lambda item: item.full_name)

    @staticmethod
    def _format_display_date(value: datetime.date) -> str:
        return value.strftime("%d.%m.%Y")

    async def _collect_late_arrival_rows_for_period(
        self,
        *,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[dict[str, object]]:
        if self.session_perco is None:
            raise RuntimeError("Perco session is required")
        if self.session_nitro is None or self.session_postgres is None:
            raise RuntimeError("Nitro and Postgres sessions are required")

        active_staff_rows = await self._load_active_staff_rows()
        if not active_staff_rows:
            return []

        platonus_ids = [
            int(row["platonus_id"])
            for row in active_staff_rows
            if row.get("platonus_id") is not None
        ]
        if not platonus_ids:
            return []

        start_dt = datetime.datetime.combine(start_date, datetime.time.min).replace(microsecond=0)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max).replace(microsecond=0)
        first_in_rows = await self._monitoring_dao().get_first_in_by_person_day(
            platonus_ids=platonus_ids,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        first_in_by_person_day: dict[tuple[int, datetime.date], datetime.datetime] = {}
        for row in first_in_rows:
            personid = row.get("personid")
            access_date = row.get("access_date")
            first_in_datetime = row.get("first_in_datetime")
            if (
                personid is None
                or not isinstance(access_date, datetime.date)
                or not isinstance(first_in_datetime, datetime.datetime)
            ):
                continue
            first_in_by_person_day[(int(personid), access_date)] = first_in_datetime

        user_by_platonus = await self._platonus_to_user_id_map(platonus_ids)
        user_ids = [uid for uid in user_by_platonus.values() if uid is not None]
        schedules_by_user = await self._load_custom_schedules(
            user_ids=user_ids,
            start_date=start_date,
            end_date=end_date,
        )
        work_days = self._iter_weekdays(start_date, end_date)

        prepared_rows: list[dict[str, object]] = []
        for staff_row in active_staff_rows:
            pid_raw = staff_row.get("platonus_id")
            if pid_raw is None:
                continue
            platonus_id = int(pid_raw)
            user_id = user_by_platonus.get(platonus_id)

            lastname = normalize_name_part(staff_row.get("lastname"))  # type: ignore[arg-type]
            firstname = normalize_name_part(staff_row.get("firstname"))  # type: ignore[arg-type]
            patronomic = normalize_name_part(staff_row.get("patronomic"))  # type: ignore[arg-type]
            full_name = build_full_name(
                lastname=lastname,
                firstname=firstname,
                patronomic=patronomic,
            )
            structural_subdivision_id = staff_row.get("structural_subdivision_id")
            structural_subdivision_name = uppercase_first(staff_row.get("structural_subdivision_name"))  # type: ignore[arg-type]
            position_name = uppercase_first(staff_row.get("position_name"))  # type: ignore[arg-type]
            rate = float(staff_row.get("rate")) if staff_row.get("rate") is not None else None
            employment_status = localize_absence_status(staff_row.get("absence_status"), "ru") or "Штатный режим"

            for work_day in work_days:
                first_in_datetime = first_in_by_person_day.get((platonus_id, work_day))
                if first_in_datetime is None:
                    continue

                shift_start_time, shift_end_time, _ = self._resolve_schedule(
                    user_id=user_id,
                    access_date=work_day,
                    schedules_by_user=schedules_by_user,
                )
                arrival_status = self._calculate_arrival_status(
                    first_in_datetime=first_in_datetime,
                    shift_start_time=shift_start_time,
                )
                if arrival_status != ArrivalStatus.LATE:
                    continue

                prepared_rows.append(
                    {
                        "TutorID": platonus_id,
                        "ФИО": full_name,
                        "structural_subdivision_id": structural_subdivision_id,
                        "Подразделение": structural_subdivision_name,
                        "Должность": position_name,
                        "Ставка": rate,
                        "Статус": employment_status,
                        "Дата и время первого входа": first_in_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                        "first_in_sort": first_in_datetime,
                        "График работы": (
                            f"{self._format_time(shift_start_time)} - {self._format_time(shift_end_time)}"
                        ),
                        "Примечание": "",
                    }
                )

        prepared_rows.sort(
            key=lambda row: (
                str(row.get("ФИО") or ""),
                row.get("first_in_sort") or datetime.datetime.min,
            )
        )
        return prepared_rows

    async def export_staff_punctuality_period_late_excel(
        self,
        *,
        start_date: datetime.date,
        end_date: datetime.date,
        structural_subdivision_id: int | None,
        search: str | None,
    ) -> bytes:
        if end_date < start_date:
            raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

        prepared_rows = await self._collect_late_arrival_rows_for_period(
            start_date=start_date,
            end_date=end_date,
        )

        if structural_subdivision_id is not None:
            prepared_rows = [
                row
                for row in prepared_rows
                if row.get("structural_subdivision_id") == structural_subdivision_id
            ]

        query = (search or "").strip().lower()
        if query:
            prepared_rows = [
                row
                for row in prepared_rows
                if query in str(row.get("ФИО") or "").lower()
                or query in str(row.get("Подразделение") or "").lower()
                or query in str(row.get("Должность") or "").lower()
                or query in str(row.get("Статус") or "").lower()
            ]

        for index, row in enumerate(prepared_rows, start=1):
            row["№"] = index

        columns = [
            "№",
            "TutorID",
            "ФИО",
            "Подразделение",
            "Должность",
            "Ставка",
            "Статус",
            "Дата и время первого входа",
            "График работы",
            "Примечание",
        ]
        export_rows = [{column: row.get(column) for column in columns} for row in prepared_rows]
        df = pd.DataFrame(export_rows, columns=columns)
        html_table = df.to_html(index=False, na_rep="", border=1, justify="left")

        period_label = (
            f"{self._format_display_date(start_date)}-{self._format_display_date(end_date)}"
        )
        letter_date = self._format_display_date(end_date)
        header_html = f"""<table border="0">
<tbody>
<tr>
  <td colspan="5"></td>
  <td colspan="5">«Шәкәрім университеті» КеАҚ<br/>Басқарма төрағасы – ректор<br/>Д.Орынбековке</td>
</tr>
<tr>
  <td colspan="2"></td>
  <td colspan="3">Қызметтік хат<br/>{letter_date}</td>
  <td colspan="5"></td>
</tr>
<tr><td colspan="10"><br/></td></tr>
<tr>
  <td colspan="10">
    {period_label} ж. аралығында жұмыс уақытынан кешігіп келгендер тізімі ұсынылады.
    Қызметкерлердің еңбек тәртібін бұзуларына байланысты жұмысқа кешігулерін ескере отырып,
    түсініктеме алып, шара қолдануды қарастыруыңызды сұраймын.
  </td>
</tr>
<tr><td colspan="10"><br/></td></tr>
</tbody>
</table>"""
        html_doc = f"""<html>
<head><meta charset="utf-8" /></head>
<body>{header_html}{html_table}</body>
</html>"""
        return html_doc.encode("utf-8-sig")
