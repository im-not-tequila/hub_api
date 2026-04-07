import argparse
import asyncio
import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.db.postgres_connection import async_session_postgres
from app.models.postgres import (
    NormativeDocument,
    NormativeDocumentCategory,
    NormativeDocumentSubcategory,
)

CATEGORY_TRANSLATIONS: dict[str, tuple[str, str]] = {
    "Внутренние нормативные документы": ("Ішкі нормативтік құжаттар", "Internal normative documents"),
    "Внешние нормативные документы": ("Сыртқы нормативтік құжаттар", "External normative documents"),
    "Документы для обучающихся": ("Білім алушыларға арналған құжаттар", "Documents for students"),
    "Инструктивные документы для ППС": (
        "ПОҚ-қа арналған нұсқаулық құжаттар",
        "Instructional documents for teaching staff",
    ),
}


@dataclass(slots=True)
class CsvRow:
    category_name_ru: str
    category_name_kz: str
    category_name_en: str
    subcategory_name_ru: str
    subcategory_name_kz: str
    subcategory_name_en: str
    document_name_ru: str
    document_name_kz: str
    document_name_en: str
    source_filename_ru: str
    source_filename_kz: str
    source_filename_en: str


def _normalize(value: str) -> str:
    return value.strip()


def _read_rows(csv_path: Path) -> list[CsvRow]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows: list[CsvRow] = []
    with csv_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        for row_number, row in enumerate(reader, start=1):
            if not row:
                continue
            if len(row) < 4:
                raise ValueError(
                    f"Invalid row at line {row_number}: expected 4 columns, got {len(row)}"
                )

            # Backward-compatible mode:
            # 4 columns -> category, subcategory, document_name, filename
            if len(row) == 4:
                category_name, subcategory_name, document_name, source_filename = row
                category_ru = _normalize(category_name)
                category_kz, category_en = CATEGORY_TRANSLATIONS.get(
                    category_ru, (category_ru, category_ru)
                )
                rows.append(
                    CsvRow(
                        category_name_ru=category_ru,
                        category_name_kz=category_kz,
                        category_name_en=category_en,
                        subcategory_name_ru=_normalize(subcategory_name),
                        subcategory_name_kz=_normalize(subcategory_name),
                        subcategory_name_en=_normalize(subcategory_name),
                        document_name_ru=_normalize(document_name),
                        document_name_kz=_normalize(document_name),
                        document_name_en=_normalize(document_name),
                        source_filename_ru=_normalize(source_filename),
                        source_filename_kz=_normalize(source_filename),
                        source_filename_en=_normalize(source_filename),
                    )
                )
                continue

            # Multi-language mode (exactly 12 columns):
            # category_ru, category_kz, category_en,
            # subcategory_ru, subcategory_kz, subcategory_en,
            # document_ru, document_kz, document_en,
            # filename_ru, filename_kz, filename_en
            if len(row) < 12:
                raise ValueError(
                    f"Invalid row at line {row_number}: expected 12 columns for multilingual format, got {len(row)}"
                )

            rows.append(
                CsvRow(
                    category_name_ru=_normalize(row[0]),
                    category_name_kz=_normalize(row[1]),
                    category_name_en=_normalize(row[2]),
                    subcategory_name_ru=_normalize(row[3]),
                    subcategory_name_kz=_normalize(row[4]),
                    subcategory_name_en=_normalize(row[5]),
                    document_name_ru=_normalize(row[6]),
                    document_name_kz=_normalize(row[7]),
                    document_name_en=_normalize(row[8]),
                    source_filename_ru=_normalize(row[9]),
                    source_filename_kz=_normalize(row[10]),
                    source_filename_en=_normalize(row[11]),
                )
            )
    return rows


async def _get_or_create_category(
    session: AsyncSession,
    row: CsvRow,
    cache: dict[str, NormativeDocumentCategory],
) -> NormativeDocumentCategory:
    cached = cache.get(row.category_name_ru)
    if cached is not None:
        return cached

    category = await session.scalar(
        select(NormativeDocumentCategory).where(
            NormativeDocumentCategory.name_ru == row.category_name_ru
        )
    )
    if category is None:
        category = NormativeDocumentCategory(
            name_ru=row.category_name_ru,
            name_kz=row.category_name_kz,
            name_en=row.category_name_en,
            is_active=True,
        )
        session.add(category)
        await session.flush()
    else:
        category.name_kz = row.category_name_kz
        category.name_en = row.category_name_en

    cache[row.category_name_ru] = category
    return category


async def _get_or_create_subcategory(
    session: AsyncSession,
    category: NormativeDocumentCategory,
    row: CsvRow,
    cache: dict[tuple[int, str], NormativeDocumentSubcategory],
) -> NormativeDocumentSubcategory:
    key = (category.id, row.subcategory_name_ru)
    cached = cache.get(key)
    if cached is not None:
        return cached

    subcategory = await session.scalar(
        select(NormativeDocumentSubcategory).where(
            NormativeDocumentSubcategory.normative_document_category_id == category.id,
            NormativeDocumentSubcategory.name_ru == row.subcategory_name_ru,
        )
    )
    if subcategory is None:
        subcategory = NormativeDocumentSubcategory(
            name_ru=row.subcategory_name_ru,
            name_kz=row.subcategory_name_kz,
            name_en=row.subcategory_name_en,
            normative_document_category_id=category.id,
            is_active=True,
        )
        session.add(subcategory)
        await session.flush()
    else:
        subcategory.name_kz = row.subcategory_name_kz
        subcategory.name_en = row.subcategory_name_en

    cache[key] = subcategory
    return subcategory


def _resolve_source_file(norm_docs_dir: Path, row: CsvRow, row_index: int) -> Path:
    candidates = [row.source_filename_ru, row.source_filename_kz, row.source_filename_en]
    for filename in candidates:
        if not filename:
            continue
        path = norm_docs_dir / filename
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Source file not found for row {row_index}: "
        f"checked {', '.join(str(norm_docs_dir / name) for name in candidates if name)}"
    )


async def _import_rows(
    rows: list[CsvRow],
    norm_docs_dir: Path,
    skip_missing_files: bool = False,
) -> None:
    if not norm_docs_dir.exists():
        raise FileNotFoundError(f"Directory not found: {norm_docs_dir}")

    category_cache: dict[str, NormativeDocumentCategory] = {}
    subcategory_cache: dict[tuple[int, str], NormativeDocumentSubcategory] = {}

    imported = 0
    skipped = 0

    async with async_session_postgres() as session:
        for index, row in enumerate(rows, start=1):
            try:
                source_path = _resolve_source_file(norm_docs_dir, row, index)
            except FileNotFoundError:
                if skip_missing_files:
                    skipped += 1
                    print(
                        f"[{index}/{len(rows)}] Skipped: source file not found "
                        f"for document '{row.document_name_ru}'"
                    )
                    continue
                raise

            category = await _get_or_create_category(session, row, category_cache)
            subcategory = await _get_or_create_subcategory(
                session, category, row, subcategory_cache
            )

            document = NormativeDocument(
                name_ru=row.document_name_ru,
                name_kz=row.document_name_kz,
                name_en=row.document_name_en,
                normative_document_subcategory_id=subcategory.id,
                is_active=True,
            )
            session.add(document)
            await session.flush()

            extension = source_path.suffix
            target_path = norm_docs_dir / f"{document.id}{extension}"
            if target_path.exists():
                raise FileExistsError(
                    f"Target file already exists for row {index}: {target_path}"
                )

            source_path.rename(target_path)
            await session.commit()
            imported += 1

            print(f"[{index}/{len(rows)}] Imported document id={document.id}: {target_path.name}")

    print(
        f"Import finished. Total rows: {len(rows)} | Imported: {imported} | Skipped: {skipped}"
    )


async def main(csv_path: Path, skip_missing_files: bool) -> None:
    settings = get_settings()
    norm_docs_dir = settings.STORAGE_DIRECTORY / "norm_docs"
    rows = _read_rows(csv_path)
    await _import_rows(rows, norm_docs_dir, skip_missing_files=skip_missing_files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Import normative document categories/subcategories/documents from CSV "
            "and rename files in storage/norm_docs to <document_id>.<ext>."
        )
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=Path("sql_data/normative_documents.csv"),
        help=(
            "Path to CSV. Supports either 4 columns "
            "(category,subcategory,document_name,filename) or 12 multilingual columns."
        ),
    )
    parser.add_argument(
        "--skip-missing-files",
        action="store_true",
        help="Skip rows where source file is not found in storage/norm_docs",
    )
    args = parser.parse_args()
    asyncio.run(main(args.csv_path, args.skip_missing_files))
