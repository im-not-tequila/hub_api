from __future__ import annotations

import datetime
from typing import Literal

from fastapi import HTTPException
import pandas as pd
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.monitoring.schemas import (
    ArrivalStatus,
    EmployeePunctualityStatsItem,
    EmployeeWorkScheduleCreateUpdate,
    EmployeeWorkScheduleItem,
    EmployeeAccessLogItem,
    TutorDetailItem,
    TutorFirstInItem,
    TutorListItem,
    WorkScheduleType,
)
from app.dao.migrate_user import MigrateUserMysqlToPostgres
from app.models.mysql.perco.control import Control
from app.models.mysql.perco.personcontrol import Personcontrol
from app.models.mysql.perco.persontabel import Persontabel
from app.models.postgres.employee_custom_schedule import EmployeeCustomSchedule
from app.models.postgres import User as UserModel

AbsenceLang = Literal["ru", "kz", "en"]
DEFAULT_SHIFT_START_TIME = datetime.time(hour=8, minute=30)
DEFAULT_SHIFT_END_TIME = datetime.time(hour=17, minute=30)
ARRIVAL_GRACE_MINUTES = 5


def _normalize_name_part(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None

    def cap_segment(s: str) -> str:
        s = s.strip()
        if not s:
            return ""
        s = s.lower()
        return s[:1].upper() + s[1:]

    parts: list[str] = []
    for word in value.split():
        hy_parts = word.split("-")
        parts.append("-".join(cap_segment(p) for p in hy_parts if p != ""))
    return " ".join(p for p in parts if p != "")


def _localize_absence_status(code: str | None, lang: AbsenceLang) -> str | None:
    if code is None:
        return None
    code = str(code).strip()
    if not code:
        return None

    mapping: dict[AbsenceLang, dict[str, str]] = {
        "ru": {
            "1000": "Командировка",
            "2000": "Трудовой отпуск",
            "3000": "Экологический отпуск",
            "4000": "Декретный отпуск",
            "5000": "Отпуск без содержания",
            "6000": "Отгул",
            "9000": "Больничный",
            "9999": "ПР",
        },
        "kz": {
            "1000": "Іссапар",
            "2000": "Еңбек демалысы",
            "3000": "Экологиялық демалыс",
            "4000": "Декреттік демалыс",
            "5000": "Жалақысыз демалыс",
            "6000": "Отгул",
            "9000": "Ауру қағазы",
            "9999": "ПР",
        },
        "en": {
            "1000": "Business trip",
            "2000": "Annual leave",
            "3000": "Ecological leave",
            "4000": "Maternity leave",
            "5000": "Unpaid leave",
            "6000": "Day off",
            "9000": "Sick leave",
            "9999": "AWOL",
        },
    }
    return mapping.get(lang, {}).get(code, code)


def _uppercase_first(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value[:1].upper() + value[1:]


def _build_full_name(*, lastname: str | None, firstname: str | None, patronomic: str | None) -> str:
    return " ".join(part for part in [lastname, firstname, patronomic] if part).strip()


class MonitoringService:
    def __init__(
        self,
        *,
        session_nitro: AsyncSession | None = None,
        session_perco: AsyncSession | None = None,
        session_postgres: AsyncSession | None = None,
    ):
        self.session_nitro = session_nitro
        self.session_perco = session_perco
        self.session_postgres = session_postgres

    async def _platonus_to_user_id_map(self, platonus_ids: list[int]) -> dict[int, int]:
        """
        Сопоставляет TutorID (platonus_id) с users.id только для сотрудников (is_student=False).
        Данные мониторинга — из nitro.tutors; студентов не ищем и не создаём.
        """
        if self.session_nitro is None or self.session_postgres is None:
            raise RuntimeError("Nitro and Postgres sessions are required for user_id resolution")
        unique = list(dict.fromkeys(pid for pid in platonus_ids if pid is not None))
        if not unique:
            return {}
        stmt = (
            select(UserModel.id, UserModel.platonus_id)
            .where(UserModel.platonus_id.in_(unique))
            .where(UserModel.is_student.is_(False))
        )
        result = await self.session_postgres.execute(stmt)
        mapping: dict[int, int] = {}
        for uid, platonus_id in result.all():
            if platonus_id is not None:
                mapping[int(platonus_id)] = int(uid)
        missing = [pid for pid in unique if pid not in mapping]
        if missing:
            created = await MigrateUserMysqlToPostgres(
                session_nitro=self.session_nitro,
                session_postgres=self.session_postgres,
            ).migrate_tutors_by_ids(missing)
            mapping.update(created)
        return mapping

    async def _user_id_for_tutor(self, platonus_id: int) -> int | None:
        m = await self._platonus_to_user_id_map([platonus_id])
        return m.get(platonus_id)

    async def _load_active_staff_rows(self) -> list[dict[str, object]]:
        if self.session_nitro is None:
            raise RuntimeError("Nitro session is required")

        sql = text(
            """
            SELECT
                t.TutorID AS platonus_id,
                t.iinplt AS iin,
                t.lastname as lastname,
                t.firstname as firstname,
                t.patronymic as patronomic,
                abs.type AS absence_status,
                t.departmentid AS structural_subdivision_id,
                s.nameru AS structural_subdivision_name,
                t.mobilePhone AS mobile_phone,
                t.ismarried AS is_married,
                t.adress AS address,
                t.BirthDate AS birth_date,
                n.NameRU AS nationality,
                t.rate AS rate,
                p.NameRU AS position_name
            FROM nitro.tutors t
                LEFT JOIN nitro.structural_subdivision s ON t.departmentid = s.id
                LEFT JOIN nitro.center_nationalities n ON t.NationID = n.Id
                LEFT JOIN nitro.tutor_positions p ON t.job_title_int = p.ID
                LEFT JOIN perco.absence abs
                    ON t.TutorID = abs.ID
                    AND abs.Data1 <> '0001-01-01'
                    AND abs.Data2 <> '0001-01-01'
                    AND CURDATE() BETWEEN abs.Data1 AND abs.Data2
            WHERE t.deleted = 0
            AND t.has_access = 1
            AND t.departmentid IS NOT NULL
            AND t.departmentid != 0
            AND s.subdivision_type IN (0, 1, 2, 3)
            AND t.job_title_int <> 103
            AND t.TutorID not in (6153,6171)
            GROUP BY
                t.TutorID, t.iinplt, s.id, s.nameru, t.departmentid, t.mobilePhone,
                t.ismarried, t.adress, t.BirthDate, t.rate, p.NameRU, t.subdivisionid, n.NameRU;
            """
        )
        result = await self.session_nitro.execute(sql)
        return [dict(row) for row in result.mappings().all()]

    async def _resolve_staff_user_id_or_404(self, *, platonus_id: int) -> int:
        user_id = await self._user_id_for_tutor(platonus_id)
        if user_id is None:
            raise HTTPException(status_code=404, detail="Employee user not found")
        return user_id

    async def _load_custom_schedules(
        self,
        *,
        user_ids: list[int],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> dict[int, list[EmployeeCustomSchedule]]:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        unique_user_ids = sorted({uid for uid in user_ids if uid is not None})
        if not unique_user_ids:
            return {}

        stmt = (
            select(EmployeeCustomSchedule)
            .where(EmployeeCustomSchedule.user_id.in_(unique_user_ids))
            .where(EmployeeCustomSchedule.start_date <= end_date)
            .where(
                or_(
                    EmployeeCustomSchedule.end_date.is_(None),
                    EmployeeCustomSchedule.end_date >= start_date,
                )
            )
            .order_by(
                EmployeeCustomSchedule.user_id.asc(),
                EmployeeCustomSchedule.start_date.desc(),
                EmployeeCustomSchedule.created_at.desc(),
            )
        )
        result = await self.session_postgres.execute(stmt)
        schedules: dict[int, list[EmployeeCustomSchedule]] = {}
        for schedule in result.scalars().all():
            schedules.setdefault(int(schedule.user_id), []).append(schedule)
        return schedules

    @staticmethod
    def _calculate_arrival_status(
        *,
        first_in_datetime: datetime.datetime | None,
        shift_start_time: datetime.time,
    ) -> str | None:
        if first_in_datetime is None:
            return None
        first_in_time = first_in_datetime.time()
        shift_start_dt = datetime.datetime.combine(first_in_datetime.date(), shift_start_time)
        grace_deadline = (shift_start_dt + datetime.timedelta(minutes=ARRIVAL_GRACE_MINUTES)).time()

        if first_in_time < shift_start_time:
            return "BEFORE_SHIFT_START"
        if first_in_time <= grace_deadline:
            return "WITHIN_GRACE_PERIOD"
        return "LATE"

    @staticmethod
    def _resolve_schedule(
        *,
        user_id: int | None,
        access_date: datetime.date,
        schedules_by_user: dict[int, list[EmployeeCustomSchedule]],
    ) -> tuple[datetime.time, datetime.time, bool]:
        if user_id is None:
            return DEFAULT_SHIFT_START_TIME, DEFAULT_SHIFT_END_TIME, False
        for schedule in schedules_by_user.get(user_id, []):
            if schedule.start_date <= access_date and (
                schedule.end_date is None or schedule.end_date >= access_date
            ):
                return schedule.work_start_time, schedule.work_end_time, True
        return DEFAULT_SHIFT_START_TIME, DEFAULT_SHIFT_END_TIME, False

    @staticmethod
    def _format_time(value: datetime.time) -> str:
        return value.strftime("%H:%M")

    @staticmethod
    def _iter_weekdays(start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
        days: list[datetime.date] = []
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                days.append(current)
            current += datetime.timedelta(days=1)
        return days

    async def list_employees_staff(self, *, lang: AbsenceLang) -> list[TutorListItem]:
        if self.session_nitro is None:
            raise RuntimeError("Nitro session is required")
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")

        rows = await self._load_active_staff_rows()

        platonus_ids = [int(row["platonus_id"]) for row in rows if row.get("platonus_id") is not None]
        user_by_platonus = await self._platonus_to_user_id_map(platonus_ids)

        data: list[dict[str, object]] = []
        for row in rows:
            item = dict(row)
            pid = int(item["platonus_id"])  # type: ignore[arg-type]
            item["user_id"] = user_by_platonus.get(pid)
            item["lastname"] = _normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
            item["firstname"] = _normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
            item["patronomic"] = _normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
            item["absence_status"] = _localize_absence_status(item.get("absence_status"), lang)  # type: ignore[arg-type]
            item["structural_subdivision_name"] = _uppercase_first(  # type: ignore[arg-type]
                item.get("structural_subdivision_name")
            )
            item["position_name"] = _uppercase_first(item.get("position_name"))  # type: ignore[arg-type]
            data.append(item)

        return [TutorListItem.model_validate(item) for item in data]

    async def export_employees_staff_excel(
        self,
        *,
        structural_subdivision_id: int | None,
        search: str | None,
    ) -> bytes:
        rows = await self._load_active_staff_rows()
        prepared_rows: list[dict[str, object]] = []
        for row in rows:
            item = dict(row)
            lastname = _normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
            firstname = _normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
            patronomic = _normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
            structural_subdivision_name = _uppercase_first(  # type: ignore[arg-type]
                item.get("structural_subdivision_name")
            )
            position_name = _uppercase_first(item.get("position_name"))  # type: ignore[arg-type]
            nationality = _uppercase_first(item.get("nationality"))  # type: ignore[arg-type]
            birth_date = item.get("birth_date")
            employment_status = _localize_absence_status(item.get("absence_status"), "ru")  # type: ignore[arg-type]
            is_married_raw = item.get("is_married")
            if is_married_raw == 1:
                married_status = "Женат/замужем"
            elif is_married_raw == 2:
                married_status = "Не женат/не замужем"
            elif is_married_raw is None:
                married_status = None
            else:
                married_status = str(is_married_raw)
            prepared_rows.append(
                {
                    "Идентификатор сотрудника (TutorID)": item.get("platonus_id"),
                    "structural_subdivision_id": item.get("structural_subdivision_id"),
                    "ФИО": _build_full_name(
                        lastname=lastname,
                        firstname=firstname,
                        patronomic=patronomic,
                    ),
                    "ИИН": item.get("iin"),
                    "Подразделение": structural_subdivision_name,
                    "Должность": position_name,
                    "Мобильный телефон": item.get("mobile_phone"),
                    "Семейное положение": married_status,
                    "Адрес": item.get("address"),
                    "Дата рождения": birth_date.isoformat() if isinstance(birth_date, datetime.date) else None,
                    "Национальность": nationality,
                    "Ставка": item.get("rate"),
                    "Статус": employment_status or "Штатный режим",
                }
            )

        if structural_subdivision_id is not None:
            prepared_rows = [
                row for row in prepared_rows
                if row.get("structural_subdivision_id") == structural_subdivision_id
            ]

        query = (search or "").strip().lower()
        if query:
            prepared_rows = [
                row for row in prepared_rows
                if query in str(row.get("ФИО") or "").lower()
                or query in str(row.get("Подразделение") or "").lower()
                or query in str(row.get("Должность") or "").lower()
            ]

        prepared_rows.sort(key=lambda row: str(row.get("ФИО") or ""))

        columns = [
            "Идентификатор сотрудника (TutorID)",
            "ИИН",
            "ФИО",
            "Подразделение",
            "Должность",
            "Мобильный телефон",
            "Семейное положение",
            "Адрес",
            "Дата рождения",
            "Национальность",
            "Ставка",
            "Статус",
        ]
        df = pd.DataFrame(prepared_rows, columns=columns)
        html_table = df.to_html(index=False, na_rep="", border=1, justify="left")
        html_doc = f"""<html>
<head><meta charset="utf-8" /></head>
<body>{html_table}</body>
</html>"""
        return html_doc.encode("utf-8-sig")

    async def get_employee_staff(
        self,
        *,
        platonus_id: int,
        lang: AbsenceLang,
    ) -> TutorDetailItem:
        if self.session_nitro is None:
            raise RuntimeError("Nitro session is required")
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")

        sql = text(
            """
            SELECT t.iinplt      AS iin,
                   t.TutorID     AS platonus_id,
                   t.lastname    as lastname,
                   t.firstname   as firstname,
                   t.patronymic  as patronomic,
                   abs.type      AS absence_status,
                   s.nameru      AS structural_subdivision_name,
                   t.mobilePhone AS mobile_phone,
                   t.ismarried   AS is_married,
                   t.adress      AS address,
                   t.BirthDate   AS birth_date,
                   t.rate        AS rate,
                   n.NameRU      AS nationality,
                   p.NameRU      AS position_name
            FROM nitro.tutors t
                     LEFT JOIN nitro.structural_subdivision s ON t.departmentid = s.id
                     LEFT JOIN nitro.center_nationalities n ON t.NationID = n.Id
                     LEFT JOIN nitro.tutor_positions p ON t.job_title_int = p.ID
                     LEFT JOIN perco.absence abs
                               ON t.TutorID = abs.ID
                                   AND abs.Data1 <> '0001-01-01'
                                   AND abs.Data2 <> '0001-01-01'
                                   AND CURDATE() BETWEEN abs.Data1 AND abs.Data2
            WHERE t.TutorID = :platonus_id
            LIMIT 1
            """
        )

        result = await self.session_nitro.execute(sql, {"platonus_id": platonus_id})
        row = result.mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Employee not found")

        item = dict(row)
        item["lastname"] = _normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
        item["firstname"] = _normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
        item["patronomic"] = _normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
        item["absence_status"] = _localize_absence_status(item.get("absence_status"), lang)  # type: ignore[arg-type]
        item["structural_subdivision_name"] = _uppercase_first(  # type: ignore[arg-type]
            item.get("structural_subdivision_name")
        )
        item["position_name"] = _uppercase_first(item.get("position_name"))  # type: ignore[arg-type]
        item["user_id"] = await self._user_id_for_tutor(platonus_id)
        return TutorDetailItem.model_validate(item)

    async def list_employee_access_logs(
        self,
        *,
        platonus_id: int,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> list[EmployeeAccessLogItem]:
        if self.session_perco is None:
            raise RuntimeError("Perco session is required")

        start_dt = datetime.datetime.combine(start_date, datetime.time.min)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max).replace(microsecond=0)

        stmt = (
            select(
                Control.name.label("control_name"),
                Personcontrol.createdate,
                Personcontrol.inoutdata,
            )
            .join(Control, Personcontrol.turniketid == Control.turniketid)
            .where(Personcontrol.personid == platonus_id)
            .where(Personcontrol.createdate > start_dt)
            .where(Personcontrol.createdate < end_dt)
            .order_by(Personcontrol.createdate.asc())
        )
        result = await self.session_perco.execute(stmt)
        rows = result.mappings().all()
        return [EmployeeAccessLogItem.model_validate(row) for row in rows]

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

        sql = text(
            """
            SELECT ts.TutorID   AS platonus_id,
                   t.lastname   as lastname,
                   t.firstname  as firstname,
                   t.patronymic as patronomic,
                   abs.type     AS absence_status,
                   s.nameru     AS structural_subdivision_name,
                   tp.NameRU    as position_name,
                   p.createdate,
                   st.name      AS perco_status_name
            FROM perco.personcontrols p
                     LEFT JOIN nitrosgu.tutor_structuralsubdivision ts
                               ON p.personid = ts.TutorID
                     LEFT JOIN nitro.tutors t
                               ON ts.TutorID = t.TutorID
                     LEFT JOIN perco.absence abs
                               ON ts.TutorID = abs.ID
                                   AND abs.Data1 <> '0001-01-01'
                                   AND abs.Data2 <> '0001-01-01'
                                   AND CURDATE() BETWEEN abs.Data1 AND abs.Data2
                     LEFT JOIN nitro.structural_subdivision s
                               ON ts.subdivisionid = s.id
                     LEFT JOIN nitro.tutor_positions tp ON t.job_title_int = tp.ID
                     INNER JOIN (SELECT personid, MIN(createdate) AS min_createdate
                                 FROM perco.personcontrols
                                 WHERE createdate > :startdate
                                   AND createdate < :enddate
                                   AND inoutdata = 'in'
                                 GROUP BY personid) AS min_dates
                                ON p.personid = min_dates.personid
                                    AND p.createdate = min_dates.min_createdate,
                 perco.status st
            WHERE ts.deleted = 0
              AND ts.type = st.id
            GROUP BY ts.TutorID
            """
        )

        result = await self.session_perco.execute(
            sql,
            {
                "startdate": start_dt,
                "enddate": end_dt,
            },
        )
        first_in_rows = [dict(row) for row in result.mappings().all()]
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
            item["lastname"] = _normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
            item["firstname"] = _normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
            item["patronomic"] = _normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
            item["absence_status"] = _localize_absence_status(item.get("absence_status"), "ru")  # type: ignore[arg-type]
            item["structural_subdivision_name"] = _uppercase_first(  # type: ignore[arg-type]
                item.get("structural_subdivision_name")
            )
            item["position_name"] = _uppercase_first(item.get("position_name"))  # type: ignore[arg-type]
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
                    row for row in filtered_rows
                    if row.createdate is None or row.arrival_status is None
                ]
            else:
                try:
                    arrival_status_enum = ArrivalStatus(status_filter)
                except ValueError:
                    arrival_status_enum = None
                if arrival_status_enum is not None:
                    filtered_rows = [
                        row for row in filtered_rows
                        if row.arrival_status == arrival_status_enum
                    ]

        schedule_filter = (schedule_type or "ALL").strip()
        if schedule_filter != "ALL":
            try:
                schedule_type_enum = WorkScheduleType(schedule_filter)
            except ValueError:
                schedule_type_enum = None
            if schedule_type_enum is not None:
                filtered_rows = [
                    row for row in filtered_rows
                    if (row.work_schedule_type or WorkScheduleType.DEFAULT) == schedule_type_enum
                ]

        perco_filter = (perco_status_name or "ALL").strip()
        if perco_filter != "ALL":
            filtered_rows = [
                row for row in filtered_rows
                if (row.perco_status_name or "") == perco_filter
            ]

        query = (search or "").strip().lower()
        if query:
            def _matches_search(row: TutorFirstInItem) -> bool:
                full_name = _build_full_name(
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
                    "ФИО": _build_full_name(
                        lastname=row.lastname,
                        firstname=row.firstname,
                        patronomic=row.patronomic,
                    ),
                    "Подразделение": row.structural_subdivision_name,
                    "Должность": row.position_name,
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

        sql = text(
            """
            SELECT
                t.TutorID AS platonus_id,
                t.lastname AS lastname,
                t.firstname AS firstname,
                t.patronymic AS patronomic,
                s.nameru AS structural_subdivision_name,
                p.NameRU AS position_name
            FROM nitro.tutors t
            LEFT JOIN nitro.structural_subdivision s ON t.departmentid = s.id
            LEFT JOIN nitro.tutor_positions p ON t.job_title_int = p.ID
            WHERE t.TutorID = :platonus_id
            LIMIT 1
            """
        )
        staff_result = await self.session_nitro.execute(sql, {"platonus_id": platonus_id})
        staff_row = staff_result.mappings().first()
        if staff_row is None:
            raise HTTPException(status_code=404, detail="Employee not found")

        start_dt = datetime.datetime.combine(start_date, datetime.time.min).replace(microsecond=0)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max).replace(microsecond=0)
        first_in_sql = text(
            """
            SELECT DATE(p.createdate) AS access_date, MIN(p.createdate) AS first_in_datetime
            FROM perco.personcontrols p
            WHERE p.personid = :platonus_id
              AND p.inoutdata = 'in'
              AND p.createdate >= :start_dt
              AND p.createdate <= :end_dt
            GROUP BY DATE(p.createdate)
            """
        )
        first_in_result = await self.session_perco.execute(
            first_in_sql,
            {
                "platonus_id": platonus_id,
                "start_dt": start_dt,
                "end_dt": end_dt,
            },
        )
        first_in_by_day: dict[datetime.date, datetime.datetime] = {}
        for row in first_in_result.mappings().all():
            access_date = row.get("access_date")
            first_in_datetime = row.get("first_in_datetime")
            if isinstance(access_date, datetime.date) and isinstance(first_in_datetime, datetime.datetime):
                first_in_by_day[access_date] = first_in_datetime

        working_hours_stmt = (
            select(func.sum(Persontabel.hoursum))
            .where(Persontabel.personid == platonus_id)
            .where(Persontabel.curdate >= start_date)
            .where(Persontabel.curdate <= end_date)
        )
        working_hours_result = await self.session_perco.execute(working_hours_stmt)
        working_hours_raw = working_hours_result.scalar_one_or_none()
        working_hours = float(working_hours_raw) if working_hours_raw is not None else 0.0

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
        lastname = _normalize_name_part(staff_item.get("lastname"))  # type: ignore[arg-type]
        firstname = _normalize_name_part(staff_item.get("firstname"))  # type: ignore[arg-type]
        patronomic = _normalize_name_part(staff_item.get("patronomic"))  # type: ignore[arg-type]
        return EmployeePunctualityStatsItem.model_validate(
            {
                "platonus_id": platonus_id,
                "user_id": user_id,
                "full_name": _build_full_name(
                    lastname=lastname,
                    firstname=firstname,
                    patronomic=patronomic,
                ),
                "structural_subdivision_id": staff_item.get("structural_subdivision_id"),
                "structural_subdivision_name": _uppercase_first(  # type: ignore[arg-type]
                    staff_item.get("structural_subdivision_name")
                ),
                "position_name": _uppercase_first(staff_item.get("position_name")),  # type: ignore[arg-type]
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
        stmt = (
            select(
                Personcontrol.personid.label("personid"),
                func.date(Personcontrol.createdate).label("access_date"),
                func.min(Personcontrol.createdate).label("first_in_datetime"),
            )
            .where(Personcontrol.inoutdata == "in")
            .where(Personcontrol.personid.in_(platonus_ids))
            .where(Personcontrol.createdate >= start_dt)
            .where(Personcontrol.createdate <= end_dt)
            .group_by(
                Personcontrol.personid,
                func.date(Personcontrol.createdate),
            )
        )
        first_in_result = await self.session_perco.execute(stmt)
        first_in_by_person_day: dict[tuple[int, datetime.date], datetime.datetime] = {}
        for row in first_in_result.mappings().all():
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

        working_hours_stmt = (
            select(
                Persontabel.personid.label("personid"),
                func.sum(Persontabel.hoursum).label("working_hours"),
            )
            .where(Persontabel.personid.in_(platonus_ids))
            .where(Persontabel.curdate >= start_date)
            .where(Persontabel.curdate <= end_date)
            .group_by(Persontabel.personid)
        )
        working_hours_result = await self.session_perco.execute(working_hours_stmt)
        working_hours_by_person: dict[int, float] = {}
        for row in working_hours_result.mappings().all():
            personid = row.get("personid")
            working_hours_raw = row.get("working_hours")
            if personid is None:
                continue
            working_hours_by_person[int(personid)] = (
                float(working_hours_raw) if working_hours_raw is not None else 0.0
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

            lastname = _normalize_name_part(staff_row.get("lastname"))  # type: ignore[arg-type]
            firstname = _normalize_name_part(staff_row.get("firstname"))  # type: ignore[arg-type]
            patronomic = _normalize_name_part(staff_row.get("patronomic"))  # type: ignore[arg-type]
            items.append(
                EmployeePunctualityStatsItem.model_validate(
                    {
                        "platonus_id": platonus_id,
                        "user_id": user_id,
                        "full_name": _build_full_name(
                            lastname=lastname,
                            firstname=firstname,
                            patronomic=patronomic,
                        ),
                        "structural_subdivision_id": staff_row.get("structural_subdivision_id"),
                        "structural_subdivision_name": _uppercase_first(  # type: ignore[arg-type]
                            staff_row.get("structural_subdivision_name")
                        ),
                        "position_name": _uppercase_first(staff_row.get("position_name")),  # type: ignore[arg-type]
                        "before_shift_start_count": before_shift_start_count,
                        "within_grace_period_count": within_grace_period_count,
                        "late_count": late_count,
                        "no_show_count": no_show_count,
                        "working_hours": round(working_hours_by_person.get(platonus_id, 0.0), 2),
                    }
                )
            )

        return sorted(items, key=lambda item: item.full_name)

    async def list_employee_work_schedules(
        self,
        *,
        platonus_id: int,
    ) -> list[EmployeeWorkScheduleItem]:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        user_id = await self._resolve_staff_user_id_or_404(platonus_id=platonus_id)
        stmt = (
            select(EmployeeCustomSchedule)
            .where(EmployeeCustomSchedule.user_id == user_id)
            .order_by(
                EmployeeCustomSchedule.start_date.desc(),
                EmployeeCustomSchedule.id.desc(),
            )
        )
        result = await self.session_postgres.execute(stmt)
        rows = result.scalars().all()
        return [
            EmployeeWorkScheduleItem.model_validate(
                {
                    "id": row.id,
                    "user_id": row.user_id,
                    "start_date": row.start_date,
                    "end_date": row.end_date,
                    "work_start_time": row.work_start_time,
                    "work_end_time": row.work_end_time,
                }
            )
            for row in rows
        ]

    async def create_employee_work_schedule(
        self,
        *,
        platonus_id: int,
        payload: EmployeeWorkScheduleCreateUpdate,
    ) -> EmployeeWorkScheduleItem:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        user_id = await self._resolve_staff_user_id_or_404(platonus_id=platonus_id)
        if payload.end_date is not None and payload.end_date < payload.start_date:
            raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

        schedule = EmployeeCustomSchedule(
            user_id=user_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            work_start_time=payload.work_start_time,
            work_end_time=payload.work_end_time,
        )
        self.session_postgres.add(schedule)
        await self.session_postgres.commit()
        await self.session_postgres.refresh(schedule)
        return EmployeeWorkScheduleItem.model_validate(
            {
                "id": schedule.id,
                "user_id": schedule.user_id,
                "start_date": schedule.start_date,
                "end_date": schedule.end_date,
                "work_start_time": schedule.work_start_time,
                "work_end_time": schedule.work_end_time,
            }
        )

    async def update_employee_work_schedule(
        self,
        *,
        platonus_id: int,
        schedule_id: int,
        payload: EmployeeWorkScheduleCreateUpdate,
    ) -> EmployeeWorkScheduleItem:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        user_id = await self._resolve_staff_user_id_or_404(platonus_id=platonus_id)
        if payload.end_date is not None and payload.end_date < payload.start_date:
            raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

        stmt = (
            select(EmployeeCustomSchedule)
            .where(EmployeeCustomSchedule.id == schedule_id)
            .where(EmployeeCustomSchedule.user_id == user_id)
            .limit(1)
        )
        result = await self.session_postgres.execute(stmt)
        schedule = result.scalars().first()
        if schedule is None:
            raise HTTPException(status_code=404, detail="Work schedule not found")

        schedule.start_date = payload.start_date
        schedule.end_date = payload.end_date
        schedule.work_start_time = payload.work_start_time
        schedule.work_end_time = payload.work_end_time
        await self.session_postgres.commit()
        await self.session_postgres.refresh(schedule)
        return EmployeeWorkScheduleItem.model_validate(
            {
                "id": schedule.id,
                "user_id": schedule.user_id,
                "start_date": schedule.start_date,
                "end_date": schedule.end_date,
                "work_start_time": schedule.work_start_time,
                "work_end_time": schedule.work_end_time,
            }
        )

    async def delete_employee_work_schedule(
        self,
        *,
        platonus_id: int,
        schedule_id: int,
    ) -> None:
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        user_id = await self._resolve_staff_user_id_or_404(platonus_id=platonus_id)
        stmt = (
            select(EmployeeCustomSchedule)
            .where(EmployeeCustomSchedule.id == schedule_id)
            .where(EmployeeCustomSchedule.user_id == user_id)
            .limit(1)
        )
        result = await self.session_postgres.execute(stmt)
        schedule = result.scalars().first()
        if schedule is None:
            raise HTTPException(status_code=404, detail="Work schedule not found")

        await self.session_postgres.delete(schedule)
        await self.session_postgres.commit()

