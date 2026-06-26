from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dao.mysql import StudentDAO, TutorDAO
from app.models.mysql.nitro import Student as StudentModel, Tutor as TutorModel
from app.models.postgres import User as UserModel
from app.models.postgres.os_inventory import (
    OsFixedAsset,
    OsImportSnapshot,
    OsResponsiblePerson,
    OsSnapshotHolding,
)

_SPACE_RE = re.compile(r"[\s\xa0]+")


def normalize_text(value: str) -> str:
    return _SPACE_RE.sub(" ", value or "").strip()


def normalize_external_id(value: str) -> str:
    return normalize_text(value)


def normalize_iin(value: str | None) -> str | None:
    cleaned = re.sub(r"\D", "", value or "")
    return cleaned or None


def normalize_inventory_number(value: str) -> str:
    return re.sub(r"[\s\xa0]", "", value or "").strip()


def parse_acquisition_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def parse_price(value: str | None) -> Decimal | None:
    if not value:
        return None
    cleaned = value.replace("\xa0", "").replace(" ", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def person_key(external_id: str, iin: str | None, full_name: str) -> tuple[str, str | None, str]:
    return external_id, iin, full_name


@dataclass
class ImportStats:
    persons_count: int
    assets_count: int
    holdings_count: int
    transfers_count: int
    removed_count: int
    added_count: int


class OsInventoryService:
    HOLDINGS_BATCH_SIZE = 2000

    def __init__(
        self,
        session_postgres: AsyncSession,
        session_nitro: AsyncSession | None = None,
    ):
        self.session = session_postgres
        self.session_nitro = session_nitro

    async def import_snapshot(self, records: list[dict[str, Any]]) -> tuple[OsImportSnapshot, ImportStats]:
        if not records:
            raise HTTPException(status_code=422, detail="Пустой список МОЛ")

        parsed_records = self._parse_records(records)
        previous_holdings = await self._get_current_holdings_map()

        await self.session.execute(
            update(OsImportSnapshot)
            .where(OsImportSnapshot.is_current.is_(True))
            .values(is_current=False)
        )

        snapshot = OsImportSnapshot(is_current=True)
        self.session.add(snapshot)
        await self.session.flush()

        person_map = await self._ensure_persons(parsed_records)
        asset_map = await self._ensure_assets(parsed_records)
        holdings_count = await self._create_holdings(
            snapshot_id=snapshot.id,
            parsed_records=parsed_records,
            person_map=person_map,
            asset_map=asset_map,
        )

        new_holdings = await self._get_snapshot_holdings_map(snapshot.id)
        transfers_count, removed_count, added_count = self._diff_holdings(previous_holdings, new_holdings)

        await self.session.commit()
        await self.session.refresh(snapshot)

        return snapshot, ImportStats(
            persons_count=len({h[0] for h in self._iter_holdings(parsed_records)}),
            assets_count=len(asset_map),
            holdings_count=holdings_count,
            transfers_count=transfers_count,
            removed_count=removed_count,
            added_count=added_count,
        )

    async def get_holdings_for_user(self, user: UserModel) -> list[dict[str, Any]]:
        iin = await self._resolve_user_iin(user)
        if not iin:
            return []
        return await self._get_holdings_by_iin(iin)

    async def get_holdings_by_iin(self, iin: str) -> list[dict[str, Any]]:
        normalized_iin = normalize_iin(iin)
        if not normalized_iin:
            raise HTTPException(status_code=422, detail="Некорректный ИИН")
        return await self._get_holdings_by_iin(normalized_iin)

    async def _get_holdings_by_iin(self, normalized_iin: str) -> list[dict[str, Any]]:
        snapshot = await self._get_current_snapshot()
        if snapshot is None:
            return []

        stmt = (
            select(OsSnapshotHolding)
            .join(OsResponsiblePerson, OsResponsiblePerson.id == OsSnapshotHolding.person_id)
            .join(OsFixedAsset, OsFixedAsset.id == OsSnapshotHolding.asset_id)
            .where(
                OsSnapshotHolding.snapshot_id == snapshot.id,
                OsResponsiblePerson.iin == normalized_iin,
            )
            .options(
                selectinload(OsSnapshotHolding.person),
                selectinload(OsSnapshotHolding.asset),
            )
            .order_by(OsFixedAsset.inventory_number)
        )
        result = await self.session.execute(stmt)
        holdings = result.scalars().all()

        return [
            {
                "inventory_number": holding.asset.inventory_number,
                "name": holding.asset.name,
                "acquisition_date": holding.asset.acquisition_date,
                "price": holding.asset.price,
                "mol_name": holding.person.full_name,
                "mol_external_id": holding.person.external_id,
            }
            for holding in holdings
        ]

    async def get_current_snapshot_info(self) -> dict[str, Any] | None:
        snapshot = await self._get_current_snapshot()
        if snapshot is None:
            return None

        persons_count = await self.session.scalar(
            select(func.count(func.distinct(OsResponsiblePerson.id)))
            .select_from(OsSnapshotHolding)
            .join(OsResponsiblePerson, OsResponsiblePerson.id == OsSnapshotHolding.person_id)
            .where(OsSnapshotHolding.snapshot_id == snapshot.id)
        )
        holdings_count = await self.session.scalar(
            select(func.count())
            .select_from(OsSnapshotHolding)
            .where(OsSnapshotHolding.snapshot_id == snapshot.id)
        )

        return {
            "id": snapshot.id,
            "imported_at": snapshot.imported_at,
            "persons_count": persons_count or 0,
            "holdings_count": holdings_count or 0,
        }

    def _parse_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        parsed: list[dict[str, Any]] = []

        for record in records:
            mol_name = normalize_text(str(record.get("MOL", "")))
            external_id = normalize_external_id(str(record.get("ID", "")))
            iin = normalize_iin(str(record.get("IIN", "")))

            if not mol_name:
                raise HTTPException(status_code=422, detail="У записи МОЛ отсутствует имя")

            items: list[dict[str, Any]] = []
            for item in record.get("OS") or []:
                if not isinstance(item, dict):
                    continue

                par = item.get("par") or {}
                inventory_number = normalize_inventory_number(str(par.get("inv", "")))
                if not inventory_number:
                    continue

                items.append(
                    {
                        "name": normalize_text(str(item.get("OS", ""))),
                        "inventory_number": inventory_number,
                        "acquisition_date": parse_acquisition_date(str(par.get("date", ""))),
                        "price": parse_price(str(par.get("price", ""))),
                    }
                )

            parsed.append(
                {
                    "external_id": external_id,
                    "iin": iin,
                    "full_name": mol_name,
                    "items": items,
                }
            )

        return parsed

    async def _ensure_persons(self, parsed_records: list[dict[str, Any]]) -> dict[tuple[str, str | None, str], int]:
        keys = {
            person_key(record["external_id"], record["iin"], record["full_name"])
            for record in parsed_records
        }

        result = await self.session.execute(select(OsResponsiblePerson))
        existing = {
            person_key(person.external_id, person.iin, person.full_name): person
            for person in result.scalars().all()
        }

        person_map: dict[tuple[str, str | None, str], int] = {}

        for key in keys:
            person = existing.get(key)
            if person is None:
                person = OsResponsiblePerson(
                    external_id=key[0],
                    iin=key[1],
                    full_name=key[2],
                )
                self.session.add(person)
                existing[key] = person

        await self.session.flush()

        for key, person in existing.items():
            if key in keys:
                person_map[key] = person.id

        return person_map

    async def _ensure_assets(self, parsed_records: list[dict[str, Any]]) -> dict[str, int]:
        assets_data: dict[str, dict[str, Any]] = {}
        for record in parsed_records:
            for item in record["items"]:
                assets_data[item["inventory_number"]] = item

        if not assets_data:
            return {}

        result = await self.session.execute(
            select(OsFixedAsset).where(
                OsFixedAsset.inventory_number.in_(assets_data.keys())
            )
        )
        existing = {asset.inventory_number: asset for asset in result.scalars().all()}

        for inventory_number, item in assets_data.items():
            asset = existing.get(inventory_number)
            if asset is None:
                asset = OsFixedAsset(
                    inventory_number=inventory_number,
                    name=item["name"],
                    acquisition_date=item["acquisition_date"],
                    price=item["price"],
                )
                self.session.add(asset)
                existing[inventory_number] = asset
            else:
                asset.name = item["name"]
                asset.acquisition_date = item["acquisition_date"]
                asset.price = item["price"]

        await self.session.flush()
        return {inventory_number: asset.id for inventory_number, asset in existing.items()}

    async def _create_holdings(
        self,
        *,
        snapshot_id: int,
        parsed_records: list[dict[str, Any]],
        person_map: dict[tuple[str, str | None, str], int],
        asset_map: dict[str, int],
    ) -> int:
        unique_holdings: set[tuple[int, int, int]] = set()

        for person_key_value, asset_inventory_number in self._iter_holdings(parsed_records):
            person_id = person_map[person_key_value]
            asset_id = asset_map[asset_inventory_number]
            unique_holdings.add((snapshot_id, person_id, asset_id))

        holdings_rows = [
            OsSnapshotHolding(snapshot_id=sid, person_id=pid, asset_id=aid)
            for sid, pid, aid in unique_holdings
        ]

        for offset in range(0, len(holdings_rows), self.HOLDINGS_BATCH_SIZE):
            batch = holdings_rows[offset : offset + self.HOLDINGS_BATCH_SIZE]
            self.session.add_all(batch)
            await self.session.flush()

        return len(holdings_rows)

    @staticmethod
    def _iter_holdings(parsed_records: list[dict[str, Any]]):
        for record in parsed_records:
            key = person_key(record["external_id"], record["iin"], record["full_name"])
            for item in record["items"]:
                yield key, item["inventory_number"]

    async def _get_current_snapshot(self) -> OsImportSnapshot | None:
        result = await self.session.execute(
            select(OsImportSnapshot)
            .where(OsImportSnapshot.is_current.is_(True))
            .order_by(OsImportSnapshot.imported_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_current_holdings_map(self) -> dict[int, int]:
        snapshot = await self._get_current_snapshot()
        if snapshot is None:
            return {}
        return await self._get_snapshot_holdings_map(snapshot.id)

    async def _get_snapshot_holdings_map(self, snapshot_id: int) -> dict[int, int]:
        result = await self.session.execute(
            select(OsSnapshotHolding.asset_id, OsSnapshotHolding.person_id).where(
                OsSnapshotHolding.snapshot_id == snapshot_id
            )
        )
        return {asset_id: person_id for asset_id, person_id in result.all()}

    @staticmethod
    def _diff_holdings(
        previous: dict[int, int],
        current: dict[int, int],
    ) -> tuple[int, int, int]:
        transfers = 0
        removed = 0
        added = 0

        all_asset_ids = set(previous) | set(current)

        for asset_id in all_asset_ids:
            old_person = previous.get(asset_id)
            new_person = current.get(asset_id)

            if old_person is None and new_person is not None:
                added += 1
            elif old_person is not None and new_person is None:
                removed += 1
            elif old_person is not None and new_person is not None and old_person != new_person:
                transfers += 1

        return transfers, removed, added

    async def _resolve_user_iin(self, user: UserModel) -> str | None:
        if not user.platonus_id or self.session_nitro is None:
            return None

        if user.is_student:
            student = await StudentDAO(self.session_nitro).get_one_or_none(
                fields=[StudentModel.iinplt],
                filters={StudentModel.StudentID: user.platonus_id},
            )
            return normalize_iin(student.iinplt) if student else None

        tutor = await TutorDAO(self.session_nitro).get_one_or_none(
            fields=[TutorModel.iinplt],
            filters={TutorModel.TutorID: user.platonus_id},
        )
        return normalize_iin(tutor.iinplt) if tutor else None
