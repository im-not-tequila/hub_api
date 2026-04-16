"""add employee custom schedules

Revision ID: b4a2d770c8e1
Revises: df0b1b02cfef
Create Date: 2026-04-14 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4a2d770c8e1"
down_revision: Union[str, Sequence[str], None] = "df0b1b02cfef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "employee_custom_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("work_start_time", sa.Time(), nullable=False),
        sa.Column("work_end_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_employee_custom_schedules_end_date_gte_start_date",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_employee_custom_schedules_user_id", "employee_custom_schedules", ["user_id"], unique=False)
    op.create_index(
        "ix_employee_custom_schedules_start_date",
        "employee_custom_schedules",
        ["start_date"],
        unique=False,
    )
    op.create_index(
        "ix_employee_custom_schedules_end_date",
        "employee_custom_schedules",
        ["end_date"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_employee_custom_schedules_end_date", table_name="employee_custom_schedules")
    op.drop_index("ix_employee_custom_schedules_start_date", table_name="employee_custom_schedules")
    op.drop_index("ix_employee_custom_schedules_user_id", table_name="employee_custom_schedules")
    op.drop_table("employee_custom_schedules")
