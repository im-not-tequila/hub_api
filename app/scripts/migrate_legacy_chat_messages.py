from __future__ import annotations

import argparse
import asyncio
import html
import mimetypes
import socket
import subprocess
import time
import uuid
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import aiofiles
import httpx
from sqlalchemy import bindparam, select, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_settings
from app.core.ssh_mysql_port import get_ssh_mysql_local_port
from app.core.ssh_postgres_port import get_ssh_postgres_local_port


LEGACY_DOWNLOAD_URL = "https://hub.shakarim.kz/mod/download.php?aid={aid}"
VALID_PLATONUS_MIN = 1
VALID_PLATONUS_MAX = 9999


class _HtmlToTextParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "br", "li", "tr"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(data)

    def get_text(self) -> str:
        raw = html.unescape("".join(self.parts))
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        return "\n".join(line for line in lines if line).strip()


@dataclass
class LegacyRow:
    mailtoid: int
    mailid: int
    mailfrom: int
    mailto: int
    maildate: Any
    mailtheme: str | None
    mailbody: str | None
    maildateread: Any
    status: int


@dataclass
class LegacyAttachment:
    aid: int
    mailid: int
    mailfiles: str


@dataclass
class DownloadedAttachment:
    aid: int
    original_name: str
    storage_key: str
    mime_type: str
    size_bytes: int
    type: str


class SshTunnelManager:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.processes: list[subprocess.Popen] = []
        self.mysql_port = self.settings.MYSQL_PORT
        self.postgres_port = self.settings.PG_PORT

    def start(self) -> None:
        if not self.settings.ssh_enabled:
            return

        self.mysql_port = get_ssh_mysql_local_port()
        self.postgres_port = get_ssh_postgres_local_port()
        self._start_tunnel(
            local_port=self.mysql_port,
            remote_host=self.settings.MYSQL_HOST,
            remote_port=self.settings.MYSQL_PORT,
            label="mysql",
        )
        self._start_tunnel(
            local_port=self.postgres_port,
            remote_host=self.settings.PG_HOST,
            remote_port=self.settings.PG_PORT,
            label="postgres",
        )

    def stop(self) -> None:
        for proc in self.processes:
            proc.terminate()
            with suppress(Exception):
                proc.wait(timeout=5)
            if proc.poll() is None:
                proc.kill()

    def _start_tunnel(self, *, local_port: int, remote_host: str, remote_port: int, label: str) -> None:
        command = [
            "ssh",
            "-p",
            str(self.settings.SSH_PORT or 22),
            "-o",
            "ExitOnForwardFailure=yes",
            "-N",
            "-L",
            f"127.0.0.1:{local_port}:{remote_host}:{remote_port}",
            f"{self.settings.SSH_USER}@{self.settings.SSH_HOST}",
        ]
        if self.settings.SSH_KEY_PATH:
            command[1:1] = ["-i", self.settings.SSH_KEY_PATH]

        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        self.processes.append(proc)
        self._wait_for_port(local_port, label, proc)

    @staticmethod
    def _wait_for_port(port: int, label: str, proc: subprocess.Popen, timeout: float = 15.0) -> None:
        started_at = time.time()
        while time.time() - started_at < timeout:
            if proc.poll() is not None:
                stderr = proc.stderr.read() if proc.stderr else ""
                raise RuntimeError(f"SSH tunnel for {label} exited early: {stderr.strip()}")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    return
            time.sleep(0.25)
        raise TimeoutError(f"SSH tunnel for {label} is not ready on 127.0.0.1:{port}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate legacy nitroapps emails into Hub chat tables.")
    parser.add_argument("--legacy-db", default="nitroapps", help="MySQL schema with emails/emailsto/emaila.")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-attachments", action="store_true")
    parser.add_argument("--download-timeout", type=float, default=30.0)
    return parser.parse_args()


def normalize_legacy_body(value: str | None) -> str:
    if not value:
        return ""
    parser = _HtmlToTextParser()
    parser.feed(value)
    text_value = parser.get_text()
    return text_value or " ".join(html.unescape(value).split())


def build_message_text(theme: str | None, body: str | None) -> str | None:
    theme = (theme or "").strip()
    body_text = normalize_legacy_body(body)
    if theme and body_text:
        return f"Subject: {theme}\n\n{body_text}"
    return theme or body_text or None


def create_legacy_engine(tunnels: SshTunnelManager, legacy_db: str):
    settings = get_settings()
    host = "127.0.0.1" if settings.ssh_enabled else settings.MYSQL_HOST
    port = tunnels.mysql_port if settings.ssh_enabled else settings.MYSQL_PORT
    url = URL.create(
        "mysql+aiomysql",
        username=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        host=host,
        port=port,
        database=legacy_db,
    )
    return create_async_engine(url, echo=False, pool_pre_ping=True, pool_recycle=3600)


async def fetch_candidate_platonus_ids(legacy_session: AsyncSession) -> list[int]:
    stmt = text(
        """
        SELECT DISTINCT platonus_id
        FROM (
            SELECT e.mailfrom AS platonus_id
            FROM emails e
            JOIN emailsto t ON t.mailid = e.mailid
            WHERE e.mailfrom BETWEEN :min_id AND :max_id
              AND t.mailto BETWEEN :min_id AND :max_id
            UNION
            SELECT t.mailto AS platonus_id
            FROM emails e
            JOIN emailsto t ON t.mailid = e.mailid
            WHERE e.mailfrom BETWEEN :min_id AND :max_id
              AND t.mailto BETWEEN :min_id AND :max_id
        ) ids
        ORDER BY platonus_id
        """
    )
    result = await legacy_session.execute(
        stmt,
        {"min_id": VALID_PLATONUS_MIN, "max_id": VALID_PLATONUS_MAX},
    )
    return [int(row[0]) for row in result.all()]


async def fetch_postgres_user_map(pg_session: AsyncSession, platonus_ids: list[int]) -> dict[int, int]:
    from app.models.postgres import User

    if not platonus_ids:
        return {}

    result: dict[int, int] = {}
    for offset in range(0, len(platonus_ids), 1000):
        chunk = platonus_ids[offset : offset + 1000]
        stmt = select(User.platonus_id, User.id).where(
            User.is_student == False,
            User.platonus_id.in_(chunk),
        )
        rows = await pg_session.execute(stmt)
        result.update({int(platonus_id): int(user_id) for platonus_id, user_id in rows.all()})
    return result


async def ensure_users(
    *,
    nitro_session: AsyncSession,
    pg_session: AsyncSession,
    legacy_session: AsyncSession,
) -> dict[int, int]:
    from app.dao.migrate_user import MigrateUserMysqlToPostgres

    candidate_ids = await fetch_candidate_platonus_ids(legacy_session)
    user_map = await fetch_postgres_user_map(pg_session, candidate_ids)
    missing_ids = [platonus_id for platonus_id in candidate_ids if platonus_id not in user_map]

    if missing_ids:
        migrator = MigrateUserMysqlToPostgres(nitro_session, pg_session)
        await migrator.migrate_tutors_by_ids(missing_ids)
        user_map = await fetch_postgres_user_map(pg_session, candidate_ids)

    unresolved = [platonus_id for platonus_id in candidate_ids if platonus_id not in user_map]
    if unresolved:
        print(f"Skipped users not found in Nitro tutors: {len(unresolved)}")
        print(f"First unresolved platonus IDs: {unresolved[:20]}")

    return user_map


async def fetch_legacy_rows(
    legacy_session: AsyncSession,
    *,
    last_mailtoid: int,
    limit: int,
) -> list[LegacyRow]:
    stmt = text(
        """
        SELECT
            t.mailtoid,
            e.mailid,
            e.mailfrom,
            t.mailto,
            e.maildate,
            e.mailtheme,
            e.mailbody,
            t.maildateread,
            t.status
        FROM emailsto t
        JOIN emails e ON e.mailid = t.mailid
        WHERE t.mailtoid > :last_mailtoid
          AND e.mailfrom BETWEEN :min_id AND :max_id
          AND t.mailto BETWEEN :min_id AND :max_id
        ORDER BY t.mailtoid
        LIMIT :limit
        """
    )
    result = await legacy_session.execute(
        stmt,
        {
            "last_mailtoid": last_mailtoid,
            "limit": limit,
            "min_id": VALID_PLATONUS_MIN,
            "max_id": VALID_PLATONUS_MAX,
        },
    )
    return [LegacyRow(**dict(row)) for row in result.mappings().all()]


async def fetch_legacy_attachments(
    legacy_session: AsyncSession,
    mailids: list[int],
) -> dict[int, list[LegacyAttachment]]:
    if not mailids:
        return {}

    result: dict[int, list[LegacyAttachment]] = defaultdict(list)
    for offset in range(0, len(mailids), 1000):
        chunk = mailids[offset : offset + 1000]
        stmt = text("SELECT aid, mailid, mailfiles FROM emaila WHERE mailid IN :mailids").bindparams(
            bindparam("mailids", expanding=True)
        )
        rows = await legacy_session.execute(stmt, {"mailids": chunk})
        for row in rows.mappings():
            attachment = LegacyAttachment(**dict(row))
            result[attachment.mailid].append(attachment)
    return result


async def fetch_existing_mapping_mailtoids(pg_session: AsyncSession, mailtoids: list[int]) -> set[int]:
    from app.models.postgres import LegacyChatMessageMapping

    if not mailtoids:
        return set()
    stmt = select(LegacyChatMessageMapping.legacy_mailtoid).where(
        LegacyChatMessageMapping.legacy_mailtoid.in_(mailtoids)
    )
    result = await pg_session.execute(stmt)
    return {int(row[0]) for row in result.all()}


async def get_or_create_direct_chat(
    pg_session: AsyncSession,
    *,
    sender_user_id: int,
    recipient_user_id: int,
    chat_cache: dict[tuple[int, int], int],
) -> int:
    from app.models.postgres import Chat, ChatParticipant, ChatParticipantRole, ChatType

    user1_id, user2_id = sorted((sender_user_id, recipient_user_id))
    cache_key = (user1_id, user2_id)
    cached_chat_id = chat_cache.get(cache_key)
    if cached_chat_id is not None:
        return cached_chat_id

    stmt = select(Chat).where(
        Chat.type == ChatType.DIRECT,
        Chat.user1_id == user1_id,
        Chat.user2_id == user2_id,
    )
    chat = (await pg_session.execute(stmt)).scalar_one_or_none()
    if chat is None:
        chat = Chat(type=ChatType.DIRECT, user1_id=user1_id, user2_id=user2_id)
        pg_session.add(chat)
        await pg_session.flush()

    existing_participants = await pg_session.execute(
        select(ChatParticipant.user_id).where(
            ChatParticipant.chat_id == chat.id,
            ChatParticipant.user_id.in_([user1_id, user2_id]),
        )
    )
    existing_user_ids = {int(row[0]) for row in existing_participants.all()}
    for user_id in (user1_id, user2_id):
        if user_id not in existing_user_ids:
            pg_session.add(
                ChatParticipant(
                    chat_id=chat.id,
                    user_id=user_id,
                    role=ChatParticipantRole.MEMBER,
                    added_by_user_id=None,
                )
            )

    chat_cache[cache_key] = int(chat.id)
    return int(chat.id)


async def download_legacy_attachment(
    *,
    client: httpx.AsyncClient,
    attachment: LegacyAttachment,
    chat_id: int,
    downloaded_cache: dict[int, DownloadedAttachment],
) -> DownloadedAttachment:
    cached = downloaded_cache.get(attachment.aid)
    if cached is not None:
        return cached

    original_name = Path(attachment.mailfiles).name or f"legacy-attachment-{attachment.aid}"
    response = await client.get(LEGACY_DOWNLOAD_URL.format(aid=attachment.aid))
    response.raise_for_status()
    content = response.content
    if not content:
        raise ValueError(f"Legacy attachment {attachment.aid} is empty")

    mime_type = (
        response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        or mimetypes.guess_type(original_name)[0]
        or "application/octet-stream"
    )
    attachment_type = "image" if mime_type.startswith("image/") else "file"
    suffix = Path(original_name).suffix.lower()
    storage_key = str(
        Path("chat")
        / "attachments"
        / str(chat_id)
        / "legacy"
        / f"{attachment.aid}-{uuid.uuid4().hex}{suffix}"
    )
    storage_path = get_settings().STORAGE_DIRECTORY / storage_key
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(storage_path, "wb") as file:
        await file.write(content)

    downloaded = DownloadedAttachment(
        aid=attachment.aid,
        original_name=original_name[:255],
        storage_key=storage_key,
        mime_type=mime_type[:255],
        size_bytes=len(content),
        type=attachment_type,
    )
    downloaded_cache[attachment.aid] = downloaded
    return downloaded


async def migrate_batch(
    *,
    pg_session: AsyncSession,
    rows: list[LegacyRow],
    attachments_by_mailid: dict[int, list[LegacyAttachment]],
    user_map: dict[int, int],
    chat_cache: dict[tuple[int, int], int],
    downloaded_cache: dict[int, DownloadedAttachment],
    http_client: httpx.AsyncClient,
    dry_run: bool,
    skip_attachments: bool,
) -> dict[str, int]:
    from app.models.postgres import (
        ChatMessage,
        ChatMessageAttachment,
        ChatMessageRead,
        LegacyChatMessageMapping,
    )

    stats = defaultdict(int)
    existing_mailtoids = await fetch_existing_mapping_mailtoids(
        pg_session,
        [row.mailtoid for row in rows],
    )

    for row in rows:
        if row.mailtoid in existing_mailtoids:
            stats["already_migrated"] += 1
            continue

        sender_user_id = user_map.get(row.mailfrom)
        recipient_user_id = user_map.get(row.mailto)
        if sender_user_id is None or recipient_user_id is None:
            stats["skipped_missing_user"] += 1
            continue
        if sender_user_id == recipient_user_id:
            stats["skipped_self_chat"] += 1
            continue

        text_value = build_message_text(row.mailtheme, row.mailbody)
        legacy_attachments = attachments_by_mailid.get(row.mailid, [])
        if not text_value and not legacy_attachments:
            stats["skipped_empty"] += 1
            continue

        if dry_run:
            stats["would_migrate"] += 1
            continue

        if skip_attachments and not text_value and legacy_attachments:
            stats["skipped_attachment_only"] += 1
            continue

        chat_id = await get_or_create_direct_chat(
            pg_session,
            sender_user_id=sender_user_id,
            recipient_user_id=recipient_user_id,
            chat_cache=chat_cache,
        )

        downloaded_attachments: list[DownloadedAttachment] = []
        if not skip_attachments:
            for legacy_attachment in legacy_attachments:
                try:
                    downloaded_attachments.append(
                        await download_legacy_attachment(
                            client=http_client,
                            attachment=legacy_attachment,
                            chat_id=chat_id,
                            downloaded_cache=downloaded_cache,
                        )
                    )
                    stats["attachments_downloaded"] += 1
                except Exception as exc:
                    stats["attachments_failed"] += 1
                    print(f"Attachment {legacy_attachment.aid} for mailid {row.mailid} skipped: {exc}")

        if not text_value and legacy_attachments and not downloaded_attachments and not skip_attachments:
            stats["skipped_empty_after_attachment_fail"] += 1
            continue

        is_read = row.maildateread is not None
        message = ChatMessage(
            chat_id=chat_id,
            sender_id=sender_user_id,
            text=text_value,
            is_read=is_read,
            created_at=row.maildate,
        )
        pg_session.add(message)
        await pg_session.flush()

        if is_read:
            pg_session.add(
                ChatMessageRead(
                    chat_id=chat_id,
                    message_id=message.id,
                    user_id=recipient_user_id,
                    read_at=row.maildateread,
                )
            )

        for downloaded in downloaded_attachments:
            pg_session.add(
                ChatMessageAttachment(
                    chat_id=chat_id,
                    message_id=message.id,
                    uploader_id=sender_user_id,
                    type=downloaded.type,
                    mime_type=downloaded.mime_type,
                    original_name=downloaded.original_name,
                    storage_key=downloaded.storage_key,
                    size_bytes=downloaded.size_bytes,
                    width=None,
                    height=None,
                    created_at=row.maildate,
                )
            )

        pg_session.add(
            LegacyChatMessageMapping(
                legacy_mailid=row.mailid,
                legacy_mailtoid=row.mailtoid,
                chat_id=chat_id,
                new_message_id=message.id,
                sender_user_id=sender_user_id,
                recipient_user_id=recipient_user_id,
            )
        )
        stats["migrated"] += 1

    if not dry_run:
        await pg_session.commit()
    return dict(stats)


def merge_stats(total: dict[str, int], batch: dict[str, int]) -> None:
    for key, value in batch.items():
        total[key] = total.get(key, 0) + value


async def run() -> None:
    args = parse_args()
    tunnels = SshTunnelManager()
    tunnels.start()

    try:
        from app.db.mysql_connection import async_session_mysql_nitro, engine_mysql_nitro
        from app.db.postgres_connection import async_session_postgres, engine_postgres

        legacy_engine = create_legacy_engine(tunnels, args.legacy_db)
        legacy_session_factory = async_sessionmaker(legacy_engine, expire_on_commit=False)

        total_stats: dict[str, int] = {}
        chat_cache: dict[tuple[int, int], int] = {}
        downloaded_cache: dict[int, DownloadedAttachment] = {}
        last_mailtoid = 0
        processed_rows = 0

        async with (
            async_session_postgres() as pg_session,
            async_session_mysql_nitro() as nitro_session,
            legacy_session_factory() as legacy_session,
            httpx.AsyncClient(
                follow_redirects=True,
                timeout=args.download_timeout,
            ) as http_client,
        ):
            user_map = await ensure_users(
                nitro_session=nitro_session,
                pg_session=pg_session,
                legacy_session=legacy_session,
            )

            while True:
                if args.max_rows is not None and processed_rows >= args.max_rows:
                    break

                limit = args.batch_size
                if args.max_rows is not None:
                    limit = min(limit, args.max_rows - processed_rows)

                rows = await fetch_legacy_rows(
                    legacy_session,
                    last_mailtoid=last_mailtoid,
                    limit=limit,
                )
                if not rows:
                    break

                last_mailtoid = rows[-1].mailtoid
                processed_rows += len(rows)
                attachments_by_mailid = await fetch_legacy_attachments(
                    legacy_session,
                    list({row.mailid for row in rows}),
                )

                try:
                    batch_stats = await migrate_batch(
                        pg_session=pg_session,
                        rows=rows,
                        attachments_by_mailid=attachments_by_mailid,
                        user_map=user_map,
                        chat_cache=chat_cache,
                        downloaded_cache=downloaded_cache,
                        http_client=http_client,
                        dry_run=args.dry_run,
                        skip_attachments=args.skip_attachments,
                    )
                except Exception:
                    await pg_session.rollback()
                    raise

                merge_stats(total_stats, batch_stats)
                print(f"Processed up to legacy mailtoid {last_mailtoid}: {batch_stats}")

        await legacy_engine.dispose()
        await engine_mysql_nitro.dispose()
        await engine_postgres.dispose()
        print("Done")
        print(total_stats)
    finally:
        tunnels.stop()


if __name__ == "__main__":
    asyncio.run(run())
