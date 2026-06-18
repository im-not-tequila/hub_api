"""add sidebar sections and role access

Revision ID: c1d2e3f4a5b6
Revises: a3f7e1d0c5b2
Create Date: 2026-06-17 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "a3f7e1d0c5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SIDEBAR_SECTIONS = [
    # key, name_ru, path, parent_key, order
    ("docs",                           "Документы",              "/docs",                          None,         1),
    ("monitoring",                     "Мониторинг персонала",   None,                             None,         2),
    ("monitoring_staff",               "Сотрудники",             None,                             "monitoring", 1),
    ("monitoring_staff_all",           "Все сотрудники",         "/monitoring/staff/all",          "monitoring_staff", 1),
    ("monitoring_staff_punctuality",   "Пунктуальность",         "/monitoring/staff/punctuality",  "monitoring_staff", 2),
    ("monitoring_academic",            "ППС",                    None,                             "monitoring", 2),
    ("monitoring_academic_all",        "Все ППС",                "/monitoring/academic/all",       "monitoring_academic", 1),
    ("monitoring_academic_punctuality","Пунктуальность",         "/monitoring/academic/punctuality","monitoring_academic", 2),
    ("visit_history",                  "Журнал посещений",       "/visit-history",                 None,         3),
    ("sample_documents",               "Образцы документов",     "/sample-documents",              None,         4),
    ("normative_documents",            "Нормативные документы",  "/normative-documents",           None,         5),
    ("work_tabel",                     "Рабочий табель",         "/work-tabel",                    None,         6),
    ("chat",                           "Чат",                    "/chat",                          None,         7),
    ("events_calendar",                "Календарь событий",      "/events-calendar",               None,         8),
]


def upgrade() -> None:
    op.create_table(
        'sidebar_sections',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('name_ru', sa.String(200), nullable=False),
        sa.Column('path', sa.String(300), nullable=True),
        sa.Column('parent_key', sa.String(100), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_key'], ['sidebar_sections.key'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )

    op.create_table(
        'role_sidebar_sections',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('section_key', sa.String(100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['section_key'], ['sidebar_sections.key'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'section_key'),
    )

    sidebar_sections_table = sa.table(
        'sidebar_sections',
        sa.column('key', sa.String),
        sa.column('name_ru', sa.String),
        sa.column('path', sa.String),
        sa.column('parent_key', sa.String),
        sa.column('order', sa.Integer),
        sa.column('is_active', sa.Boolean),
    )

    op.bulk_insert(sidebar_sections_table, [
        {
            'key': key,
            'name_ru': name_ru,
            'path': path,
            'parent_key': parent_key,
            'order': order,
            'is_active': True,
        }
        for key, name_ru, path, parent_key, order in SIDEBAR_SECTIONS
    ])


def downgrade() -> None:
    op.drop_table('role_sidebar_sections')
    op.drop_table('sidebar_sections')
