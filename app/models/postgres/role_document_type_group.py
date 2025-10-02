from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres_connection import PostgresBase
from .timestamp_mixin import TimestampMixin


class RoleDocumentTypeGroup(PostgresBase, TimestampMixin):
    __tablename__ = "role_document_type_groups"

    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("document_type_groups.id", ondelete="CASCADE"),
        primary_key=True
    )

    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="document_type_groups"
    )

    group: Mapped["DocumentTypeGroup"] = relationship(
        "DocumentTypeGroup",
        back_populates="roles"
    )

    def __repr__(self):
        return f"<RoleDocumentTypeGroup role_id={self.role_id} group_id={self.group_id}>"
