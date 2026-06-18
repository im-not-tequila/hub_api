from sqlalchemy import Integer, Boolean, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class SidebarSection(PostgresBase, TimestampMixin):
    __tablename__ = 'sidebar_sections'

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="Уникальный slug-ключ раздела, напр. 'docs', 'chat', 'monitoring'"
    )

    name_ru: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    path: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Маршрут Vue Router, если раздел является конечным узлом"
    )

    parent_key: Mapped[str | None] = mapped_column(
        String(100),
        ForeignKey('sidebar_sections.key', ondelete='SET NULL'),
        nullable=True,
        comment="Ключ родительского раздела для вложенных пунктов меню"
    )

    order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Порядок отображения внутри группы"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )

    children: Mapped[list["SidebarSection"]] = relationship(
        "SidebarSection",
        primaryjoin="SidebarSection.parent_key == SidebarSection.key",
        foreign_keys="SidebarSection.parent_key",
        back_populates="parent",
        lazy="selectin"
    )

    parent: Mapped["SidebarSection | None"] = relationship(
        "SidebarSection",
        primaryjoin="SidebarSection.parent_key == SidebarSection.key",
        foreign_keys="SidebarSection.parent_key",
        back_populates="children",
        remote_side="SidebarSection.key"
    )

    role_sections: Mapped[list["RoleSidebarSection"]] = relationship(
        "RoleSidebarSection",
        back_populates="section",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<SidebarSection key={self.key!r} name_ru={self.name_ru!r}>"

    def __str__(self):
        return f"{self.key} — {self.name_ru}"
