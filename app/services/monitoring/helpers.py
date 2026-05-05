from __future__ import annotations

from app.services.monitoring.constants import AbsenceLang


def normalize_name_part(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None

    def cap_segment(s: str) -> str:
        s = s.strip()
        if not s:
            return ""
        s = s.lower()
        return s[:1].upper() + s[1:]

    parts: list[str] = []
    for word in value.split():
        hy_parts = word.split("-")
        parts.append("-".join(cap_segment(p) for p in hy_parts if p != ""))
    return " ".join(p for p in parts if p != "")


def localize_absence_status(code: str | None, lang: AbsenceLang) -> str | None:
    if code is None:
        return None
    code = str(code).strip()
    if not code:
        return None

    mapping: dict[AbsenceLang, dict[str, str]] = {
        "ru": {
            "1000": "Командировка",
            "2000": "Трудовой отпуск",
            "3000": "Экологический отпуск",
            "4000": "Декретный отпуск",
            "5000": "Отпуск без содержания",
            "6000": "Отгул",
            "9000": "Больничный",
            "9999": "ПР",
        },
        "kz": {
            "1000": "Іссапар",
            "2000": "Еңбек демалысы",
            "3000": "Экологиялық демалыс",
            "4000": "Декреттік демалыс",
            "5000": "Жалақысыз демалыс",
            "6000": "Отгул",
            "9000": "Ауру қағазы",
            "9999": "ПР",
        },
        "en": {
            "1000": "Business trip",
            "2000": "Annual leave",
            "3000": "Ecological leave",
            "4000": "Maternity leave",
            "5000": "Unpaid leave",
            "6000": "Day off",
            "9000": "Sick leave",
            "9999": "AWOL",
        },
    }
    return mapping.get(lang, {}).get(code, code)


def uppercase_first(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return value[:1].upper() + value[1:]


def pick_localized_value(
    *,
    lang: AbsenceLang,
    ru: str | None,
    kz: str | None,
    en: str | None,
) -> str | None:
    values = {
        "ru": ru,
        "kz": kz,
        "en": en,
    }
    selected = values.get(lang)
    for candidate in [selected, ru, kz, en]:
        normalized = uppercase_first(candidate)
        if normalized is not None:
            return normalized
    return None


def build_full_name(*, lastname: str | None, firstname: str | None, patronomic: str | None) -> str:
    return " ".join(part for part in [lastname, firstname, patronomic] if part).strip()
