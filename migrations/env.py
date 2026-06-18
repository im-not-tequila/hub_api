import os
import sys
from os.path import dirname, abspath

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from logging.config import fileConfig

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.db.postgres_connection import PostgresBase, DATABASE_URL

# Разрешаем переопределить URL через переменную окружения (удобно для миграций через SSH-туннель)
DATABASE_URL = os.environ.get("DATABASE_URL") or DATABASE_URL
from app.models.postgres.user import User
from app.models.postgres.user_info import UserInfo
from app.models.postgres.role import Role
from app.models.postgres.user_role import UserRole
from app.models.postgres.document import Document
from app.models.postgres.document_type import DocumentType
from app.models.postgres.document_type_group import DocumentTypeGroup
from app.models.postgres.approver import Approver
from app.models.postgres.role_document_type_group import RoleDocumentTypeGroup
from app.models.postgres.executor import Executor
from app.models.postgres.hidden_document import HiddenDocument
from app.models.postgres.travel_funding_source import TravelFundingSource
from app.models.postgres.notification import Notification
from app.models.postgres.sample_document_group import SampleDocumentGroup
from app.models.postgres.sample_document import SampleDocument
from app.models.postgres.custom_document_templates import CustomDocumentTemplate
from app.models.postgres.chat import Chat
from app.models.postgres.chat_message import ChatMessage
from app.models.postgres.chat_message_attachment import ChatMessageAttachment
from app.models.postgres.chat_message_read import ChatMessageRead
from app.models.postgres.chat_message_user_deletion import ChatMessageUserDeletion
from app.models.postgres.chat_participant import ChatParticipant
from app.models.postgres.calendar_event_manager import CalendarEventManager, CalendarEventPlace, CalendarEventType
from app.models.postgres.employee_custom_schedule import EmployeeCustomSchedule


config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)


if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = PostgresBase.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        # prefix="sqlalchemy.",
        poolclass=pool.NullPool
    )

    # connectable = engine_from_config(
    #     config.get_section(config.config_ini_section, {}),
    #     prefix="sqlalchemy.",
    #     poolclass=pool.NullPool,
    # )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
