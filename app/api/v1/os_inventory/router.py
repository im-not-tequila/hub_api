from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth.deps import get_current_user
from app.core.settings import get_settings
from app.db.session import get_nitro_session, get_postgres_session
from app.models.postgres import User as UserModel
from app.services.os_inventory import OsInventoryService

from .schemas import (
    OsCurrentSnapshotResponse,
    OsHoldingResponse,
    OsImportResponse,
    OsImportStatsResponse,
    OsMolRecordSchema,
)

router = APIRouter()
settings = get_settings()


def _get_os_inventory_service(
    session_postgres: AsyncSession = Depends(get_postgres_session),
    session_nitro: AsyncSession = Depends(get_nitro_session),
) -> OsInventoryService:
    return OsInventoryService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
    )


def _verify_import_secret(x_os_import_secret: str | None = Header(default=None)) -> None:
    if not settings.SSO_SECRET:
        return
    if x_os_import_secret != settings.SSO_SECRET:
        raise HTTPException(status_code=403, detail="Invalid import secret")


@router.post(
    "/import",
    response_model=OsImportResponse,
    summary="Импорт выгрузки ОС из 1С",
)
async def import_os_snapshot(
    records: list[OsMolRecordSchema],
    _: None = Depends(_verify_import_secret),
    service: OsInventoryService = Depends(_get_os_inventory_service),
):
    """
    Принимает JSON-массив МОЛ в формате выгрузки 1С.
    При наличии SSO_SECRET в .env требуется заголовок X-Os-Import-Secret.
    """
    payload = [record.model_dump() for record in records]
    snapshot, stats = await service.import_snapshot(payload)

    return OsImportResponse(
        snapshot_id=snapshot.id,
        imported_at=snapshot.imported_at,
        stats=OsImportStatsResponse(
            persons_count=stats.persons_count,
            assets_count=stats.assets_count,
            holdings_count=stats.holdings_count,
            transfers_count=stats.transfers_count,
            removed_count=stats.removed_count,
            added_count=stats.added_count,
        ),
    )


@router.get(
    "/me/holdings",
    response_model=list[OsHoldingResponse],
    summary="Имущество текущего пользователя (ИИН из Platonus)",
)
async def get_my_holdings(
    current_user: UserModel = Depends(get_current_user),
    service: OsInventoryService = Depends(_get_os_inventory_service),
):
    holdings = await service.get_holdings_for_user(current_user)
    return [OsHoldingResponse(**item) for item in holdings]


@router.get(
    "/holdings",
    response_model=list[OsHoldingResponse],
    summary="Имущество сотрудника по ИИН (актуальный снимок)",
)
async def get_holdings_by_iin(
    iin: str,
    current_user: UserModel = Depends(get_current_user),
    service: OsInventoryService = Depends(_get_os_inventory_service),
):
    _ = current_user
    holdings = await service.get_holdings_by_iin(iin)
    return [OsHoldingResponse(**item) for item in holdings]


@router.get(
    "/snapshots/current",
    response_model=OsCurrentSnapshotResponse | None,
    summary="Информация об актуальном снимке выгрузки",
)
async def get_current_snapshot(
    current_user: UserModel = Depends(get_current_user),
    service: OsInventoryService = Depends(_get_os_inventory_service),
):
    _ = current_user
    info = await service.get_current_snapshot_info()
    if info is None:
        return None
    return OsCurrentSnapshotResponse(**info)
