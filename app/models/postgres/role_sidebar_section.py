from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class RoleSidebarSection(PostgresBase, TimestampMixin):
    __tablename__ = 'role_sidebar_sections'

    role_id: Mapped[int] = mapped_column(
        ForeignKey('roles.id', ondelete='CASCADE'),
        primary_key=True
    )

    section_key: Mapped[str] = mapped_column(
        String(100),
        ForeignKey('sidebar_sections.key', ondelete='CASCADE'),
        primary_key=True
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="sidebar_sections"
    )

    section: Mapped["SidebarSection"] = relationship(
        "SidebarSection",
        back_populates="role_sections",
        lazy="joined"
    )

    def __repr__(self):
        return f"<RoleSidebarSection role_id={self.role_id} section_key={self.section_key!r}>"

    def __str__(self):
        if hasattr(self, "section") and self.section is not None:
            return f"{self.role_id} → {self.section.name_ru}"
        return f"role_id={self.role_id} section_key={self.section_key}"
