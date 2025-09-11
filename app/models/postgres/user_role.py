from sqlalchemy import Table, Column, ForeignKey, UniqueConstraint
from app.db.postgres_connection import PostgresBase

user_roles = Table(
    "user_roles",
    PostgresBase.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    UniqueConstraint("user_id", "role_id", name="uq_user_role")
)