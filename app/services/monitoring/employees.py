from __future__ import annotations

import datetime

import pandas as pd
from fastapi import HTTPException

from app.api.v1.monitoring.schemas import (
    EmployeeAccessLogItem,
    TutorAcademicDetailItem,
    TutorAcademicListItem,
    TutorAcademicPositionRateItem,
    TutorDetailItem,
    TutorListItem,
)
from app.services.monitoring.constants import AbsenceLang
from app.services.monitoring.helpers import (
    build_full_name,
    localize_absence_status,
    normalize_name_part,
    pick_localized_value,
    uppercase_first,
)


class MonitoringEmployeesMixin:
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
            item["lastname"] = normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
            item["firstname"] = normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
            item["patronomic"] = normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
            item["absence_status"] = localize_absence_status(item.get("absence_status"), lang)  # type: ignore[arg-type]
            item["structural_subdivision_name"] = uppercase_first(  # type: ignore[arg-type]
                item.get("structural_subdivision_name")
            )
            item["position_name"] = uppercase_first(item.get("position_name"))  # type: ignore[arg-type]
            data.append(item)

        return [TutorListItem.model_validate(item) for item in data]

    async def list_employees_academic(self, *, lang: AbsenceLang) -> list[TutorAcademicListItem]:
        if self.session_nitro is None:
            raise RuntimeError("Nitro session is required")
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")

        rows = await self._load_active_academic_rows()
        platonus_ids = [int(row["platonus_id"]) for row in rows if row.get("platonus_id") is not None]
        user_by_platonus = await self._platonus_to_user_id_map(platonus_ids)

        grouped: dict[int, dict[str, object]] = {}
        for row in rows:
            platonus_id_raw = row.get("platonus_id")
            if platonus_id_raw is None:
                continue
            platonus_id = int(platonus_id_raw)
            if platonus_id not in grouped:
                grouped[platonus_id] = {
                    "platonus_id": platonus_id,
                    "user_id": user_by_platonus.get(platonus_id),
                    "lastname": normalize_name_part(row.get("lastname")),  # type: ignore[arg-type]
                    "firstname": normalize_name_part(row.get("firstname")),  # type: ignore[arg-type]
                    "patronomic": normalize_name_part(row.get("patronomic")),  # type: ignore[arg-type]
                    "positions": [],
                }

            rate_raw = row.get("rate")
            grouped[platonus_id]["positions"].append(  # type: ignore[index]
                TutorAcademicPositionRateItem.model_validate(
                    {
                        "cafedra_id": row.get("cafedra_id"),
                        "cafedra_name": pick_localized_value(
                            lang=lang,
                            ru=row.get("cafedra_name_ru"),  # type: ignore[arg-type]
                            kz=row.get("cafedra_name_kz"),  # type: ignore[arg-type]
                            en=row.get("cafedra_name_en"),  # type: ignore[arg-type]
                        ),
                        "position_name": pick_localized_value(
                            lang=lang,
                            ru=row.get("position_name_ru"),  # type: ignore[arg-type]
                            kz=row.get("position_name_kz"),  # type: ignore[arg-type]
                            en=row.get("position_name_en"),  # type: ignore[arg-type]
                        ),
                        "rate": float(rate_raw) if rate_raw is not None else None,
                    }
                )
            )

        items = [TutorAcademicListItem.model_validate(item) for item in grouped.values()]
        return sorted(
            items,
            key=lambda item: build_full_name(
                lastname=item.lastname,
                firstname=item.firstname,
                patronomic=item.patronomic,
            ),
        )

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
            lastname = normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
            firstname = normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
            patronomic = normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
            structural_subdivision_name = uppercase_first(  # type: ignore[arg-type]
                item.get("structural_subdivision_name")
            )
            position_name = uppercase_first(item.get("position_name"))  # type: ignore[arg-type]
            nationality = uppercase_first(item.get("nationality"))  # type: ignore[arg-type]
            birth_date = item.get("birth_date")
            employment_status = localize_absence_status(item.get("absence_status"), "ru")  # type: ignore[arg-type]
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
                    "ФИО": build_full_name(
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
                row for row in prepared_rows if row.get("structural_subdivision_id") == structural_subdivision_id
            ]

        query = (search or "").strip().lower()
        if query:
            prepared_rows = [
                row
                for row in prepared_rows
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
        row = await self._monitoring_dao().get_employee_staff_row(platonus_id)
        if not row:
            raise HTTPException(status_code=404, detail="Employee not found")

        item = dict(row)
        item["lastname"] = normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
        item["firstname"] = normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
        item["patronomic"] = normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
        item["absence_status"] = localize_absence_status(item.get("absence_status"), lang)  # type: ignore[arg-type]
        item["structural_subdivision_name"] = uppercase_first(  # type: ignore[arg-type]
            item.get("structural_subdivision_name")
        )
        item["position_name"] = uppercase_first(item.get("position_name"))  # type: ignore[arg-type]
        item["user_id"] = await self._user_id_for_tutor(platonus_id)
        return TutorDetailItem.model_validate(item)

    async def get_employee_academic(
        self,
        *,
        platonus_id: int,
        lang: AbsenceLang,
    ) -> TutorAcademicDetailItem:
        if self.session_nitro is None:
            raise RuntimeError("Nitro session is required")
        if self.session_postgres is None:
            raise RuntimeError("Postgres session is required")
        rows = await self._monitoring_dao().get_employee_academic_rows(platonus_id)
        if not rows:
            raise HTTPException(status_code=404, detail="Employee not found")

        first_row = rows[0]
        positions: list[TutorAcademicPositionRateItem] = []
        for row in rows:
            rate_raw = row.get("rate")
            positions.append(
                TutorAcademicPositionRateItem.model_validate(
                    {
                        "cafedra_id": row.get("cafedra_id"),
                        "cafedra_name": pick_localized_value(
                            lang=lang,
                            ru=row.get("cafedra_name_ru"),  # type: ignore[arg-type]
                            kz=row.get("cafedra_name_kz"),  # type: ignore[arg-type]
                            en=row.get("cafedra_name_en"),  # type: ignore[arg-type]
                        ),
                        "position_name": pick_localized_value(
                            lang=lang,
                            ru=row.get("position_name_ru"),  # type: ignore[arg-type]
                            kz=row.get("position_name_kz"),  # type: ignore[arg-type]
                            en=row.get("position_name_en"),  # type: ignore[arg-type]
                        ),
                        "rate": float(rate_raw) if rate_raw is not None else None,
                    }
                )
            )

        item = dict(first_row)
        item["lastname"] = normalize_name_part(item.get("lastname"))  # type: ignore[arg-type]
        item["firstname"] = normalize_name_part(item.get("firstname"))  # type: ignore[arg-type]
        item["patronomic"] = normalize_name_part(item.get("patronomic"))  # type: ignore[arg-type]
        item["nationality"] = uppercase_first(item.get("nationality"))  # type: ignore[arg-type]
        item["positions"] = positions
        item["user_id"] = await self._user_id_for_tutor(platonus_id)
        return TutorAcademicDetailItem.model_validate(item)

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
        rows = await self._monitoring_dao().get_employee_access_log_rows(
            platonus_id=platonus_id,
            start_dt=start_dt,
            end_dt=end_dt,
        )
        return [EmployeeAccessLogItem.model_validate(row) for row in rows]
