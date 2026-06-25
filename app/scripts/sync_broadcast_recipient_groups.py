from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.migrate_user import MigrateUserMysqlToPostgres
from app.dao.postgres.broadcast_group import BroadcastGroupDAO
from app.db.mysql_connection import async_session_mysql_nitro, engine_mysql_nitro
from app.db.postgres_connection import async_session_postgres, engine_postgres
from app.models.postgres import BroadcastGroup, BroadcastGroupMember, User
from app.scripts.migrate_legacy_chat_messages import SshTunnelManager

LEGACY_CASE_DESCRIPTION_PREFIX = "legacy_recipient_case="


@dataclass(frozen=True)
class RecipientCategory:
    case_id: str
    name: str
    sql: str


RECIPIENT_CATEGORIES: list[RecipientCategory] = [
    RecipientCategory(
        "1",
        "Проректора",
        """
        SELECT dean AS tutor_id
        FROM nitro.structural_subdivision
        WHERE subdivision_type = 0 AND dean > 0 AND deleted <> 1 AND id IN (98, 99, 100, 142)
        """,
    ),
    RecipientCategory(
        "2",
        "Деканы факультетов",
        """
        SELECT dean AS tutor_id
        FROM nitro.structural_subdivision
        WHERE subdivision_type = 2 AND dean > 0 AND deleted <> 1 AND id > 0
        """,
    ),
    RecipientCategory(
        "3",
        "Заведующие кафедрой",
        """
        SELECT dean AS tutor_id
        FROM nitro.structural_subdivision
        WHERE subdivision_type = 3 AND dean > 0 AND deleted <> 1 AND id > 0
        """,
    ),
    RecipientCategory(
        "4",
        "Руководители СП",
        """
        SELECT dean AS tutor_id
        FROM nitro.structural_subdivision
        WHERE subdivision_type = 1 AND dean > 0 AND deleted <> 1 AND id > 0
        UNION
        SELECT TutorID AS tutor_id
        FROM nitro.tutors
        WHERE TutorID IN (481, 6186)
        """,
    ),
    RecipientCategory(
        "6",
        "Эдвайзеры",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutors
        INNER JOIN nitro.`groups` ON tutors.TutorID = `groups`.adviserID
        INNER JOIN nitro.students ON `groups`.groupID = students.groupID
        WHERE tutors.has_access = 1 AND tutors.deleted <> 1 AND students.isStudent = 1
        """,
    ),
    RecipientCategory(
        "7",
        "ППС - Исследовательской школы пищевой инженерии",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.FacultyID = 1
        """,
    ),
    RecipientCategory(
        "8",
        "ППС - Исследовательской школы ветеринарии и сельского хозяйства",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.FacultyID = 4
        """,
    ),
    RecipientCategory(
        "9",
        "ППС - Высшей школы образования",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.FacultyID = 7
        """,
    ),
    RecipientCategory(
        "10",
        "ППС - Высшей школы STEM - образования",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.FacultyID = 8
        """,
    ),
    RecipientCategory(
        "11",
        "ППС - Высшей школы спорта и естественных наук",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.FacultyID = 9
        """,
    ),
    RecipientCategory(
        "12",
        "ППС - Исследовательской школы физических и химических наук",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.FacultyID = 10
        """,
    ),
    RecipientCategory(
        "13",
        "ППС - Высшей школы цифровых технологий и строительства",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.FacultyID = 11
        """,
    ),
    RecipientCategory(
        "14",
        "ППС - Высшей школы бизнеса и коммуникации",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.FacultyID = 12
        """,
    ),
    RecipientCategory(
        "15",
        "ППС - Кафедры биоинженерных систем",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 1
        """,
    ),
    RecipientCategory(
        "16",
        "ППС - Кафедры пищевой технологии",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 4
        """,
    ),
    RecipientCategory(
        "17",
        "ППС - Кафедры техническая физика и теплоэнергетика",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 5
        """,
    ),
    RecipientCategory(
        "18",
        "ППС - Кафедры математики",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 7
        """,
    ),
    RecipientCategory(
        "19",
        "ППС - Кафедры физической культуры и спорта",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 9
        """,
    ),
    RecipientCategory(
        "20",
        "ППС - Кафедры экономики и финансов",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 12
        """,
    ),
    RecipientCategory(
        "21",
        "ППС - Кафедры химии и экологии",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 16
        """,
    ),
    RecipientCategory(
        "22",
        "ППС - Кафедры ветеринарии",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 17
        """,
    ),
    RecipientCategory(
        "23",
        "ППС - Кафедры химии и биологии",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 19
        """,
    ),
    RecipientCategory(
        "24",
        "ППС - Кафедры казахской филологии",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 24
        """,
    ),
    RecipientCategory(
        "25",
        "ППС - Кафедры иностранных и русского языков",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 26
        """,
    ),
    RecipientCategory(
        "26",
        "ППС - Кафедры автоматизации и информационных технологий",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 28
        """,
    ),
    RecipientCategory(
        "27",
        "ППС - Кафедры сельского хозяйства",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 38
        """,
    ),
    RecipientCategory(
        "28",
        "ППС - Кафедры искусства",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 43
        """,
    ),
    RecipientCategory(
        "29",
        "ППС - Кафедры истории",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 44
        """,
    ),
    RecipientCategory(
        "30",
        "ППС - Кафедры педагогики и психологии",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 52
        """,
    ),
    RecipientCategory(
        "31",
        "ППС - Кафедры физики и информатики",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 54
        """,
    ),
    RecipientCategory(
        "32",
        "ППС - Кафедры строительства и геодезии",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 55
        """,
    ),
    RecipientCategory(
        "33",
        "ППС - Кафедры языковой коммуникации",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1) AND cafedras.cafedraID = 60
        """,
    ),
    RecipientCategory(
        "34",
        "ППС - Старшие кураторы",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutor_cafedra
        INNER JOIN nitro.tutors ON tutor_cafedra.tutorID = tutors.TutorID
        INNER JOIN nitro.cafedras ON tutor_cafedra.cafedraid = cafedras.cafedraID
        WHERE tutors.has_access = 1 AND tutors.deleted = 0 AND tutor_cafedra.deleted = 0
          AND tutor_cafedra.type IN (0, 1)
          AND tutors.TutorID IN (
            6377, 5890, 4020, 3707, 506, 4132, 660, 5889, 3890, 6279, 3884, 3756, 4698,
            5847, 4106, 513, 3395, 4301, 954, 5872, 5129, 3872, 2094, 3529, 2058, 331,
            3945, 54, 4017, 5904, 5851, 4105, 3569, 2713, 4164, 5902, 5895
          )
        """,
    ),
    RecipientCategory(
        "35",
        "ППС - Офис регистратора",
        """
        SELECT DISTINCT tutors.TutorID AS tutor_id
        FROM nitro.tutors
        WHERE tutors.has_access = 1 AND tutors.deleted = 0
          AND tutors.TutorID IN (4452, 4983, 5419, 6136, 6376, 5879)
        """,
    ),
    RecipientCategory(
        "40",
        "Руководители СП (pre=0)",
        """
        SELECT dean AS tutor_id
        FROM nitro.structural_subdivision
        WHERE subdivision_type = 1 AND pre = 0 AND dean > 0 AND deleted <> 1 AND id > 0
        """,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Создаёт группы рассылки из legacy-категорий получателей Nitro "
            "и наполняет их пользователями Hub по TutorID."
        )
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        help="Обработать только указанные legacy case (можно передать несколько раз).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать статистику, без записи в Postgres.",
    )
    parser.add_argument(
        "--migrate-missing",
        action="store_true",
        help="Создать в Postgres отсутствующих сотрудников по TutorID из Nitro.",
    )
    parser.add_argument(
        "--sync-members",
        action="store_true",
        help="Удалить из группы участников, которых больше нет в SQL-выборке.",
    )
    return parser.parse_args()


def legacy_case_description(case_id: str) -> str:
    return f"{LEGACY_CASE_DESCRIPTION_PREFIX}{case_id}"


def selected_categories(case_ids: list[str] | None) -> list[RecipientCategory]:
    if not case_ids:
        return RECIPIENT_CATEGORIES

    by_id = {category.case_id: category for category in RECIPIENT_CATEGORIES}
    missing = [case_id for case_id in case_ids if case_id not in by_id]
    if missing:
        known = ", ".join(sorted(by_id))
        raise SystemExit(f"Неизвестные case: {', '.join(missing)}. Доступны: {known}")

    return [by_id[case_id] for case_id in case_ids]


async def fetch_tutor_ids(nitro_session: AsyncSession, category: RecipientCategory) -> list[int]:
    result = await nitro_session.execute(text(category.sql))
    tutor_ids: list[int] = []
    for row in result.all():
        value = row[0]
        if value is None:
            continue
        tutor_id = int(value)
        if tutor_id > 0:
            tutor_ids.append(tutor_id)
    return list(dict.fromkeys(tutor_ids))


async def fetch_user_map(pg_session: AsyncSession, tutor_ids: list[int]) -> dict[int, int]:
    if not tutor_ids:
        return {}

    user_map: dict[int, int] = {}
    for offset in range(0, len(tutor_ids), 1000):
        chunk = tutor_ids[offset : offset + 1000]
        stmt = select(User.platonus_id, User.id).where(
            User.is_student == False,
            User.platonus_id.in_(chunk),
        )
        rows = await pg_session.execute(stmt)
        user_map.update({int(platonus_id): int(user_id) for platonus_id, user_id in rows.all()})
    return user_map


async def get_group_for_category(
    pg_session: AsyncSession,
    category: RecipientCategory,
) -> BroadcastGroup | None:
    marker = legacy_case_description(category.case_id)
    group = (
        await pg_session.execute(
            select(BroadcastGroup).where(BroadcastGroup.description == marker)
        )
    ).scalar_one_or_none()
    if group is not None:
        return group

    return (
        await pg_session.execute(
            select(BroadcastGroup).where(BroadcastGroup.name == category.name)
        )
    ).scalar_one_or_none()


async def ensure_group(
    pg_session: AsyncSession,
    category: RecipientCategory,
    *,
    dry_run: bool,
) -> BroadcastGroup | None:
    group = await get_group_for_category(pg_session, category)
    if group is not None:
        if group.name != category.name:
            group.name = category.name
        marker = legacy_case_description(category.case_id)
        if group.description != marker:
            group.description = marker
        return group

    if dry_run:
        return None

    group = BroadcastGroup(
        name=category.name,
        description=legacy_case_description(category.case_id),
        created_by_user_id=None,
    )
    pg_session.add(group)
    await pg_session.flush()
    return group


async def sync_group_members(
    pg_session: AsyncSession,
    *,
    group_id: int,
    target_user_ids: list[int],
    sync_members: bool,
    dry_run: bool,
) -> dict[str, int]:
    stats = defaultdict(int)
    target_set = set(target_user_ids)

    existing_rows = await pg_session.execute(
        select(BroadcastGroupMember.user_id).where(BroadcastGroupMember.group_id == group_id)
    )
    existing_user_ids = {int(row[0]) for row in existing_rows.all()}

    to_add = [user_id for user_id in target_user_ids if user_id not in existing_user_ids]
    to_remove = sorted(existing_user_ids - target_set) if sync_members else []

    stats["members_existing"] = len(existing_user_ids)
    stats["members_target"] = len(target_set)
    stats["members_added"] = len(to_add)
    stats["members_removed"] = len(to_remove)

    if dry_run:
        return dict(stats)

    dao = BroadcastGroupDAO(pg_session)
    for user_id in to_add:
        await dao.add_member(group_id, user_id, added_by_user_id=None)

    for user_id in to_remove:
        await dao.remove_member(group_id, user_id)

    return dict(stats)


async def process_category(
    *,
    nitro_session: AsyncSession,
    pg_session: AsyncSession,
    category: RecipientCategory,
    dry_run: bool,
    migrate_missing: bool,
    sync_members: bool,
) -> dict[str, int | str]:
    stats: dict[str, int | str] = {
        "case_id": category.case_id,
        "name": category.name,
    }

    tutor_ids = await fetch_tutor_ids(nitro_session, category)
    stats["tutor_ids_found"] = len(tutor_ids)

    user_map = await fetch_user_map(pg_session, tutor_ids)
    missing_tutor_ids = [tutor_id for tutor_id in tutor_ids if tutor_id not in user_map]
    stats["users_found"] = len(user_map)
    stats["users_missing"] = len(missing_tutor_ids)

    if missing_tutor_ids and migrate_missing and not dry_run:
        migrated = await MigrateUserMysqlToPostgres(nitro_session, pg_session).migrate_tutors_by_ids(
            missing_tutor_ids
        )
        user_map.update(migrated)
        user_map = await fetch_user_map(pg_session, tutor_ids)
        missing_tutor_ids = [tutor_id for tutor_id in tutor_ids if tutor_id not in user_map]
        stats["users_migrated"] = len(migrated)
        stats["users_found"] = len(user_map)
        stats["users_missing"] = len(missing_tutor_ids)

    target_user_ids = [user_map[tutor_id] for tutor_id in tutor_ids if tutor_id in user_map]
    stats["members_target"] = len(set(target_user_ids))

    if dry_run:
        group = await get_group_for_category(pg_session, category)
        stats["group_exists"] = int(group is not None)
        if group is not None:
            stats["group_id"] = group.id
        if group is not None:
            member_stats = await sync_group_members(
                pg_session,
                group_id=group.id,
                target_user_ids=target_user_ids,
                sync_members=sync_members,
                dry_run=True,
            )
            stats.update(member_stats)
        else:
            stats["members_added"] = len(set(target_user_ids))
            stats["members_removed"] = 0
        if missing_tutor_ids:
            stats["missing_tutor_ids_sample"] = ",".join(str(tid) for tid in missing_tutor_ids[:10])
        return stats

    group = await ensure_group(pg_session, category, dry_run=False)
    if group is None:
        raise RuntimeError(f"Не удалось создать группу для case {category.case_id}")

    stats["group_id"] = group.id
    member_stats = await sync_group_members(
        pg_session,
        group_id=group.id,
        target_user_ids=target_user_ids,
        sync_members=sync_members,
        dry_run=False,
    )
    stats.update(member_stats)

    if missing_tutor_ids:
        stats["missing_tutor_ids_sample"] = ",".join(str(tid) for tid in missing_tutor_ids[:10])

    return stats


async def run() -> None:
    args = parse_args()
    categories = selected_categories(args.cases)
    tunnels = SshTunnelManager()
    tunnels.start()

    try:
        async with async_session_postgres() as pg_session, async_session_mysql_nitro() as nitro_session:
            for category in categories:
                try:
                    stats = await process_category(
                        nitro_session=nitro_session,
                        pg_session=pg_session,
                        category=category,
                        dry_run=args.dry_run,
                        migrate_missing=args.migrate_missing,
                        sync_members=args.sync_members,
                    )
                    if not args.dry_run:
                        await pg_session.commit()
                    print(stats)
                except Exception:
                    await pg_session.rollback()
                    raise

        await engine_mysql_nitro.dispose()
        await engine_postgres.dispose()
        print("Done")
    finally:
        tunnels.stop()


if __name__ == "__main__":
    asyncio.run(run())
