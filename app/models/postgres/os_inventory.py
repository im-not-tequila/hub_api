from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class OsImportSnapshot(PostgresBase, TimestampMixin):
    """Полная выгрузка из 1С на момент импорта."""

    __tablename__ = "os_import_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        index=True,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )

    holdings: Mapped[list["OsSnapshotHolding"]] = relationship(
        "OsSnapshotHolding",
        back_populates="snapshot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OsResponsiblePerson(PostgresBase, TimestampMixin):
    """МОЛ из 1С. Без привязки к users — поиск по ИИН в интерфейсе."""

    __tablename__ = "os_responsible_persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    external_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        comment="ID МОЛ в 1С (поле ID из выгрузки)",
    )

    iin: Mapped[str | None] = mapped_column(
        String(12),
        nullable=True,
        index=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    holdings: Mapped[list["OsSnapshotHolding"]] = relationship(
        "OsSnapshotHolding",
        back_populates="person",
        lazy="selectin",
    )


class OsFixedAsset(PostgresBase, TimestampMixin):
    """Основное средство. Бизнес-ключ — инвентарный номер."""

    __tablename__ = "os_fixed_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    inventory_number: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        unique=True,
        index=True,
        comment="Инвентарный номер (par.inv)",
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    acquisition_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    holdings: Mapped[list["OsSnapshotHolding"]] = relationship(
        "OsSnapshotHolding",
        back_populates="asset",
        lazy="selectin",
    )


class OsSnapshotHolding(PostgresBase):
    """Кто чем владел в конкретном снимке выгрузки."""

    __tablename__ = "os_snapshot_holdings"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "person_id",
            "asset_id",
            name="uq_os_snapshot_holdings_snapshot_person_asset",
        ),
        Index(
            "ix_os_snapshot_holdings_snapshot_person",
            "snapshot_id",
            "person_id",
        ),
        Index(
            "ix_os_snapshot_holdings_snapshot_asset",
            "snapshot_id",
            "asset_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    snapshot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("os_import_snapshots.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    person_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("os_responsible_persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    asset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("os_fixed_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    snapshot: Mapped["OsImportSnapshot"] = relationship(
        "OsImportSnapshot",
        back_populates="holdings",
    )

    person: Mapped["OsResponsiblePerson"] = relationship(
        "OsResponsiblePerson",
        back_populates="holdings",
    )

    asset: Mapped["OsFixedAsset"] = relationship(
        "OsFixedAsset",
        back_populates="holdings",
    )
