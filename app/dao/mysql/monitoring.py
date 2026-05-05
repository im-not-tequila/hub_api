import datetime

from sqlalchemy import MetaData, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mysql.nitro import (
    Cafedra,
    CenterNationality,
    StructuralSubdivision,
    Tutor,
    TutorCafedra,
    TutorPositions,
)
from app.models.mysql.nitrosgu import TutorStructuralsubdivision
from app.models.mysql.perco import Absence, Control, Personcontrol, Persontabel, Status


class MonitoringDAO:
    def __init__(
        self,
        session_nitro: AsyncSession | None = None,
        session_perco: AsyncSession | None = None,
    ):
        self.session_nitro = session_nitro
        self.session_perco = session_perco

        metadata = MetaData()
        # Use schema-qualified table copies to support cross-database joins.
        self.tutors = Tutor.__table__.to_metadata(metadata, schema="nitro")
        self.structural_subdivision = StructuralSubdivision.__table__.to_metadata(metadata, schema="nitro")
        self.center_nationalities = CenterNationality.__table__.to_metadata(metadata, schema="nitro")
        self.tutor_positions = TutorPositions.__table__.to_metadata(metadata, schema="nitro")
        self.cafedras = Cafedra.__table__.to_metadata(metadata, schema="nitro")
        self.tutor_cafedra = TutorCafedra.__table__.to_metadata(metadata, schema="nitro")
        self.absence = Absence.__table__.to_metadata(metadata, schema="perco")
        self.controls = Control.__table__.to_metadata(metadata, schema="perco")
        self.personcontrols = Personcontrol.__table__.to_metadata(metadata, schema="perco")
        self.persontabel = Persontabel.__table__.to_metadata(metadata, schema="perco")
        self.status = Status.__table__.to_metadata(metadata, schema="perco")
        self.tutor_structuralsubdivision = TutorStructuralsubdivision.__table__.to_metadata(
            metadata, schema="nitrosgu"
        )

    def _active_absence_join_condition(self, person_id_column):
        sentinel_date = datetime.date(1, 1, 1)
        return and_(
            person_id_column == self.absence.c.ID,
            self.absence.c.Data1.is_not(None),
            self.absence.c.Data2.is_not(None),
            self.absence.c.Data1 != sentinel_date,
            self.absence.c.Data2 != sentinel_date,
            func.curdate().between(self.absence.c.Data1, self.absence.c.Data2),
        )

    def _session_for_nitro(self) -> AsyncSession:
        # Some endpoints inject only one MySQL session; cross-db SQL still works on that connection.
        if self.session_nitro is not None:
            return self.session_nitro
        if self.session_perco is not None:
            return self.session_perco
        raise RuntimeError("MySQL session is required")

    def _session_for_perco(self) -> AsyncSession:
        if self.session_perco is not None:
            return self.session_perco
        if self.session_nitro is not None:
            return self.session_nitro
        raise RuntimeError("MySQL session is required")

    async def get_active_staff_rows(self) -> list[dict[str, object]]:
        stmt = (
            select(
                self.tutors.c.TutorID.label("platonus_id"),
                self.tutors.c.iinplt.label("iin"),
                self.tutors.c.lastname.label("lastname"),
                self.tutors.c.firstname.label("firstname"),
                self.tutors.c.patronymic.label("patronomic"),
                func.max(self.absence.c.type).label("absence_status"),
                self.tutors.c.departmentid.label("structural_subdivision_id"),
                self.structural_subdivision.c.nameru.label("structural_subdivision_name"),
                self.tutors.c.mobilePhone.label("mobile_phone"),
                self.tutors.c.ismarried.label("is_married"),
                self.tutors.c.adress.label("address"),
                self.tutors.c.BirthDate.label("birth_date"),
                self.center_nationalities.c.NameRU.label("nationality"),
                self.tutors.c.RATE.label("rate"),
                self.tutor_positions.c.NameRU.label("position_name"),
            )
            .select_from(
                self.tutors.outerjoin(
                    self.structural_subdivision,
                    self.tutors.c.departmentid == self.structural_subdivision.c.id,
                )
                .outerjoin(
                    self.center_nationalities,
                    self.tutors.c.NationID == self.center_nationalities.c.Id,
                )
                .outerjoin(
                    self.tutor_positions,
                    self.tutors.c.job_title_int == self.tutor_positions.c.ID,
                )
                .outerjoin(
                    self.absence,
                    self._active_absence_join_condition(self.tutors.c.TutorID),
                )
            )
            .where(self.tutors.c.deleted == 0)
            .where(self.tutors.c.has_access == 1)
            .where(self.tutors.c.departmentid.is_not(None))
            .where(self.tutors.c.departmentid != 0)
            .where(self.structural_subdivision.c.subdivision_type.in_([0, 1, 2, 3]))
            .where(self.tutors.c.job_title_int != 103)
            .where(self.tutors.c.TutorID.not_in([6153, 6171]))
            .group_by(
                self.tutors.c.TutorID,
                self.tutors.c.iinplt,
                self.tutors.c.lastname,
                self.tutors.c.firstname,
                self.tutors.c.patronymic,
                self.tutors.c.departmentid,
                self.structural_subdivision.c.nameru,
                self.tutors.c.mobilePhone,
                self.tutors.c.ismarried,
                self.tutors.c.adress,
                self.tutors.c.BirthDate,
                self.center_nationalities.c.NameRU,
                self.tutors.c.RATE,
                self.tutor_positions.c.NameRU,
            )
        )
        result = await self._session_for_nitro().execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_active_academic_rows(self) -> list[dict[str, object]]:
        stmt = (
            select(
                self.tutors.c.TutorID.label("platonus_id"),
                self.tutors.c.lastname.label("lastname"),
                self.tutors.c.firstname.label("firstname"),
                self.tutors.c.patronymic.label("patronomic"),
                self.cafedras.c.cafedraID.label("cafedra_id"),
                self.cafedras.c.cafedraNameRU.label("cafedra_name_ru"),
                self.cafedras.c.cafedraNameKZ.label("cafedra_name_kz"),
                self.cafedras.c.cafedraNameEN.label("cafedra_name_en"),
                self.tutor_cafedra.c.rate.label("rate"),
                self.tutor_positions.c.NameRU.label("position_name_ru"),
                self.tutor_positions.c.NameKZ.label("position_name_kz"),
                self.tutor_positions.c.NameEN.label("position_name_en"),
            )
            .select_from(
                self.tutors.join(
                    self.tutor_cafedra,
                    self.tutor_cafedra.c.tutorID == self.tutors.c.TutorID,
                )
                .join(
                    self.cafedras,
                    self.tutor_cafedra.c.cafedraid == self.cafedras.c.cafedraID,
                )
                .join(
                    self.tutor_positions,
                    self.tutor_positions.c.ID == self.tutor_cafedra.c.position,
                )
            )
            .where(self.tutors.c.has_access == 1)
            .where(self.tutors.c["del"] == 0)
            .where(self.tutors.c.deleted == 0)
            .where(self.tutor_cafedra.c.rate.is_not(None))
            .where(self.tutor_cafedra.c.rate != 0)
        )
        result = await self._session_for_nitro().execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_employee_staff_row(self, platonus_id: int) -> dict[str, object] | None:
        stmt = (
            select(
                self.tutors.c.iinplt.label("iin"),
                self.tutors.c.TutorID.label("platonus_id"),
                self.tutors.c.lastname.label("lastname"),
                self.tutors.c.firstname.label("firstname"),
                self.tutors.c.patronymic.label("patronomic"),
                func.max(self.absence.c.type).label("absence_status"),
                self.structural_subdivision.c.nameru.label("structural_subdivision_name"),
                self.tutors.c.mobilePhone.label("mobile_phone"),
                self.tutors.c.ismarried.label("is_married"),
                self.tutors.c.adress.label("address"),
                self.tutors.c.BirthDate.label("birth_date"),
                self.tutors.c.RATE.label("rate"),
                self.center_nationalities.c.NameRU.label("nationality"),
                self.tutor_positions.c.NameRU.label("position_name"),
            )
            .select_from(
                self.tutors.outerjoin(
                    self.structural_subdivision,
                    self.tutors.c.departmentid == self.structural_subdivision.c.id,
                )
                .outerjoin(
                    self.center_nationalities,
                    self.tutors.c.NationID == self.center_nationalities.c.Id,
                )
                .outerjoin(
                    self.tutor_positions,
                    self.tutors.c.job_title_int == self.tutor_positions.c.ID,
                )
                .outerjoin(
                    self.absence,
                    self._active_absence_join_condition(self.tutors.c.TutorID),
                )
            )
            .where(self.tutors.c.TutorID == platonus_id)
            .group_by(
                self.tutors.c.iinplt,
                self.tutors.c.TutorID,
                self.tutors.c.lastname,
                self.tutors.c.firstname,
                self.tutors.c.patronymic,
                self.structural_subdivision.c.nameru,
                self.tutors.c.mobilePhone,
                self.tutors.c.ismarried,
                self.tutors.c.adress,
                self.tutors.c.BirthDate,
                self.tutors.c.RATE,
                self.center_nationalities.c.NameRU,
                self.tutor_positions.c.NameRU,
            )
            .limit(1)
        )
        result = await self._session_for_nitro().execute(stmt)
        row = result.mappings().first()
        return dict(row) if row is not None else None

    async def get_employee_academic_rows(self, platonus_id: int) -> list[dict[str, object]]:
        stmt = (
            select(
                self.tutors.c.iinplt.label("iin"),
                self.tutors.c.TutorID.label("platonus_id"),
                self.tutors.c.lastname.label("lastname"),
                self.tutors.c.firstname.label("firstname"),
                self.tutors.c.patronymic.label("patronomic"),
                self.tutors.c.mobilePhone.label("mobile_phone"),
                self.tutors.c.ismarried.label("is_married"),
                self.tutors.c.adress.label("address"),
                self.tutors.c.BirthDate.label("birth_date"),
                self.center_nationalities.c.NameRU.label("nationality"),
                self.cafedras.c.cafedraID.label("cafedra_id"),
                self.cafedras.c.cafedraNameRU.label("cafedra_name_ru"),
                self.cafedras.c.cafedraNameKZ.label("cafedra_name_kz"),
                self.cafedras.c.cafedraNameEN.label("cafedra_name_en"),
                self.tutor_positions.c.NameRU.label("position_name_ru"),
                self.tutor_positions.c.NameKZ.label("position_name_kz"),
                self.tutor_positions.c.NameEN.label("position_name_en"),
                self.tutor_cafedra.c.rate.label("rate"),
            )
            .select_from(
                self.tutors.join(
                    self.tutor_cafedra,
                    self.tutor_cafedra.c.tutorID == self.tutors.c.TutorID,
                )
                .join(
                    self.cafedras,
                    self.tutor_cafedra.c.cafedraid == self.cafedras.c.cafedraID,
                )
                .outerjoin(
                    self.center_nationalities,
                    self.tutors.c.NationID == self.center_nationalities.c.Id,
                )
                .outerjoin(
                    self.tutor_positions,
                    self.tutor_positions.c.ID == self.tutor_cafedra.c.position,
                )
            )
            .where(self.tutors.c.TutorID == platonus_id)
            .where(self.tutors.c.has_access == 1)
            .where(self.tutors.c["del"] == 0)
            .where(self.tutors.c.deleted == 0)
            .where(self.tutor_cafedra.c.rate.is_not(None))
            .where(self.tutor_cafedra.c.rate != 0)
        )
        result = await self._session_for_nitro().execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_staff_first_in_rows(
        self,
        *,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> list[dict[str, object]]:
        min_dates = (
            select(
                self.personcontrols.c.personid.label("personid"),
                func.min(self.personcontrols.c.createdate).label("min_createdate"),
            )
            .where(self.personcontrols.c.createdate > start_dt)
            .where(self.personcontrols.c.createdate < end_dt)
            .where(self.personcontrols.c.inoutdata == "in")
            .group_by(self.personcontrols.c.personid)
            .subquery("min_dates")
        )

        stmt = (
            select(
                self.tutor_structuralsubdivision.c.TutorID.label("platonus_id"),
                self.tutors.c.lastname.label("lastname"),
                self.tutors.c.firstname.label("firstname"),
                self.tutors.c.patronymic.label("patronomic"),
                func.max(self.absence.c.type).label("absence_status"),
                self.structural_subdivision.c.nameru.label("structural_subdivision_name"),
                self.tutor_positions.c.NameRU.label("position_name"),
                self.personcontrols.c.createdate.label("createdate"),
                self.status.c.name.label("perco_status_name"),
            )
            .select_from(
                self.personcontrols.outerjoin(
                    self.tutor_structuralsubdivision,
                    self.personcontrols.c.personid == self.tutor_structuralsubdivision.c.TutorID,
                )
                .outerjoin(self.tutors, self.tutor_structuralsubdivision.c.TutorID == self.tutors.c.TutorID)
                .outerjoin(
                    self.absence,
                    self._active_absence_join_condition(self.tutor_structuralsubdivision.c.TutorID),
                )
                .outerjoin(
                    self.structural_subdivision,
                    self.tutor_structuralsubdivision.c.subdivisionid == self.structural_subdivision.c.id,
                )
                .outerjoin(
                    self.tutor_positions,
                    self.tutors.c.job_title_int == self.tutor_positions.c.ID,
                )
                .join(
                    min_dates,
                    and_(
                        self.personcontrols.c.personid == min_dates.c.personid,
                        self.personcontrols.c.createdate == min_dates.c.min_createdate,
                    ),
                )
                .join(
                    self.status,
                    self.tutor_structuralsubdivision.c.type == self.status.c.id,
                )
            )
            .where(self.tutor_structuralsubdivision.c.deleted == 0)
            .group_by(self.tutor_structuralsubdivision.c.TutorID)
        )
        result = await self._session_for_perco().execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_academic_first_in_rows(
        self,
        *,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> list[dict[str, object]]:
        min_dates = (
            select(
                self.personcontrols.c.personid.label("personid"),
                func.min(self.personcontrols.c.createdate).label("min_createdate"),
            )
            .where(self.personcontrols.c.createdate > start_dt)
            .where(self.personcontrols.c.createdate < end_dt)
            .where(self.personcontrols.c.inoutdata == "in")
            .group_by(self.personcontrols.c.personid)
            .subquery("min_dates")
        )

        stmt = (
            select(
                self.tutor_cafedra.c.tutorID.label("platonus_id"),
                self.tutors.c.lastname.label("lastname"),
                self.tutors.c.firstname.label("firstname"),
                self.tutors.c.patronymic.label("patronomic"),
                self.personcontrols.c.createdate.label("createdate"),
                self.status.c.name.label("perco_status_name"),
                self.cafedras.c.cafedraID.label("cafedra_id"),
                self.cafedras.c.cafedraNameRU.label("cafedra_name_ru"),
                self.tutor_positions.c.NameRU.label("position_name_ru"),
                self.tutor_cafedra.c.rate.label("rate"),
            )
            .select_from(
                self.personcontrols.join(
                    min_dates,
                    and_(
                        self.personcontrols.c.personid == min_dates.c.personid,
                        self.personcontrols.c.createdate == min_dates.c.min_createdate,
                    ),
                )
                .join(
                    self.tutor_cafedra,
                    self.personcontrols.c.personid == self.tutor_cafedra.c.tutorID,
                )
                .join(self.tutors, self.tutor_cafedra.c.tutorID == self.tutors.c.TutorID)
                .join(self.cafedras, self.tutor_cafedra.c.cafedraid == self.cafedras.c.cafedraID)
                .outerjoin(
                    self.tutor_positions,
                    self.tutor_positions.c.ID == self.tutor_cafedra.c.position,
                )
                .join(
                    self.status,
                    self.tutor_cafedra.c.type == self.status.c.id,
                )
            )
            .where(self.tutors.c.has_access == 1)
            .where(self.tutors.c["del"] == 0)
            .where(self.tutors.c.deleted == 0)
            .where(self.tutor_cafedra.c.deleted == 0)
            .where(self.tutor_cafedra.c["del"] == 0)
            .where(self.tutor_cafedra.c.rate.is_not(None))
            .where(self.tutor_cafedra.c.rate != 0)
        )
        result = await self._session_for_perco().execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_staff_brief_row(self, platonus_id: int) -> dict[str, object] | None:
        stmt = (
            select(
                self.tutors.c.TutorID.label("platonus_id"),
                self.tutors.c.lastname.label("lastname"),
                self.tutors.c.firstname.label("firstname"),
                self.tutors.c.patronymic.label("patronomic"),
                self.tutors.c.departmentid.label("structural_subdivision_id"),
                self.structural_subdivision.c.nameru.label("structural_subdivision_name"),
                self.tutor_positions.c.NameRU.label("position_name"),
            )
            .select_from(
                self.tutors.outerjoin(
                    self.structural_subdivision,
                    self.tutors.c.departmentid == self.structural_subdivision.c.id,
                ).outerjoin(
                    self.tutor_positions,
                    self.tutors.c.job_title_int == self.tutor_positions.c.ID,
                )
            )
            .where(self.tutors.c.TutorID == platonus_id)
            .limit(1)
        )
        result = await self._session_for_nitro().execute(stmt)
        row = result.mappings().first()
        return dict(row) if row is not None else None

    async def get_employee_first_in_rows_by_day(
        self,
        *,
        platonus_id: int,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> list[dict[str, object]]:
        stmt = (
            select(
                func.date(self.personcontrols.c.createdate).label("access_date"),
                func.min(self.personcontrols.c.createdate).label("first_in_datetime"),
            )
            .where(self.personcontrols.c.personid == platonus_id)
            .where(self.personcontrols.c.inoutdata == "in")
            .where(self.personcontrols.c.createdate >= start_dt)
            .where(self.personcontrols.c.createdate <= end_dt)
            .group_by(func.date(self.personcontrols.c.createdate))
        )
        result = await self._session_for_perco().execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_employee_access_log_rows(
        self,
        *,
        platonus_id: int,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> list[dict[str, object]]:
        stmt = (
            select(
                self.controls.c.name.label("control_name"),
                self.personcontrols.c.createdate.label("createdate"),
                self.personcontrols.c.inoutdata.label("inoutdata"),
            )
            .select_from(
                self.personcontrols.join(
                    self.controls,
                    self.personcontrols.c.turniketid == self.controls.c.turniketid,
                )
            )
            .where(self.personcontrols.c.personid == platonus_id)
            .where(self.personcontrols.c.createdate > start_dt)
            .where(self.personcontrols.c.createdate < end_dt)
            .order_by(self.personcontrols.c.createdate.asc())
        )
        result = await self._session_for_perco().execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_working_hours_sum(
        self,
        *,
        platonus_id: int,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> float:
        stmt = (
            select(func.sum(self.persontabel.c.hoursum).label("working_hours"))
            .where(self.persontabel.c.personid == platonus_id)
            .where(self.persontabel.c.curdate >= start_date)
            .where(self.persontabel.c.curdate <= end_date)
        )
        result = await self._session_for_perco().execute(stmt)
        working_hours_raw = result.scalar_one_or_none()
        return float(working_hours_raw) if working_hours_raw is not None else 0.0

    async def get_first_in_by_person_day(
        self,
        *,
        platonus_ids: list[int],
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> list[dict[str, object]]:
        if not platonus_ids:
            return []
        stmt = (
            select(
                self.personcontrols.c.personid.label("personid"),
                func.date(self.personcontrols.c.createdate).label("access_date"),
                func.min(self.personcontrols.c.createdate).label("first_in_datetime"),
            )
            .where(self.personcontrols.c.inoutdata == "in")
            .where(self.personcontrols.c.personid.in_(platonus_ids))
            .where(self.personcontrols.c.createdate >= start_dt)
            .where(self.personcontrols.c.createdate <= end_dt)
            .group_by(
                self.personcontrols.c.personid,
                func.date(self.personcontrols.c.createdate),
            )
        )
        result = await self._session_for_perco().execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    async def get_working_hours_by_person(
        self,
        *,
        platonus_ids: list[int],
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> dict[int, float]:
        if not platonus_ids:
            return {}
        stmt = (
            select(
                self.persontabel.c.personid.label("personid"),
                func.sum(self.persontabel.c.hoursum).label("working_hours"),
            )
            .where(self.persontabel.c.personid.in_(platonus_ids))
            .where(self.persontabel.c.curdate >= start_date)
            .where(self.persontabel.c.curdate <= end_date)
            .group_by(self.persontabel.c.personid)
        )
        result = await self._session_for_perco().execute(stmt)
        rows = result.mappings().all()
        output: dict[int, float] = {}
        for row in rows:
            personid = row.get("personid")
            if personid is None:
                continue
            raw_value = row.get("working_hours")
            output[int(personid)] = float(raw_value) if raw_value is not None else 0.0
        return output

