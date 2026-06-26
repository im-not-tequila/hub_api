from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OsAssetParamsSchema(BaseModel):
    inv: str
    date: str = ""
    price: str = ""


class OsAssetItemSchema(BaseModel):
    OS: str
    par: OsAssetParamsSchema


class OsMolRecordSchema(BaseModel):
    MOL: str
    ID: str
    IIN: str = ""
    OS: list[OsAssetItemSchema] = Field(default_factory=list)


class OsImportRequest(BaseModel):
    records: list[OsMolRecordSchema] | None = None


class OsImportStatsResponse(BaseModel):
    persons_count: int
    assets_count: int
    holdings_count: int
    transfers_count: int
    removed_count: int
    added_count: int


class OsImportResponse(BaseModel):
    snapshot_id: int
    imported_at: datetime
    stats: OsImportStatsResponse


class OsHoldingResponse(BaseModel):
    inventory_number: str
    name: str
    acquisition_date: date | None
    price: Decimal | None
    mol_name: str
    mol_external_id: str


class OsCurrentSnapshotResponse(BaseModel):
    id: int
    imported_at: datetime
    persons_count: int
    holdings_count: int
