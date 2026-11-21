"""Определение языка по письменности и подготовка текста к переводу."""

from __future__ import annotations

import re

_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LATIN = re.compile(r"[A-Za-z]")

_LABELS = {
    "ru": "RU",
    "en": "EN",
    "uk": "UK",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "it": "IT",
    "pl": "PL",
    "tr": "TR",
    "auto": "AUTO",
}


def detect_language(text: str) -> str:
    """'ru', если кириллицы не меньше, чем латиницы, иначе 'en'."""
    cyrillic = len(_CYRILLIC.findall(text))
    latin = len(_LATIN.findall(text))
    if cyrillic and cyrillic >= latin:
        return "ru"
    return "en"


def language_label(code: str) -> str:
    """Короткая подпись языка для шапки уведомления."""
    return _LABELS.get(code.lower(), code.upper()[:3])


def direction_label(source: str, target: str) -> str:
    return f"{language_label(source)} → {language_label(target)}"


_INLINE_SPACES = re.compile(r"[ \t\f\v]+")


def flatten(text: str) -> str:
    """Свести текст в одну строку — для короткого предпросмотра."""
    return " ".join(text.split())


def normalize(text: str) -> str:
    """Убрать лишние пробелы, сохранив абзацы и переводы строк."""
    lines = [_INLINE_SPACES.sub(" ", line).strip() for line in text.splitlines()]
    result: list[str] = []
    for line in lines:
        if line:
            result.append(line)
        elif result and result[-1]:
            result.append("")
    while result and not result[-1]:
        result.pop()
    return "\n".join(result)


def clamp_text(text: str, limit: int) -> tuple[str, bool]:
    """Вернуть очищенный текст и признак того, что он был обрезан."""
    cleaned = normalize(text)
    if len(cleaned) <= limit:
        return cleaned, False
    return cleaned[:limit].rstrip(), True


def shorten(text: str, limit: int) -> str:
    """Сократить текст для предпросмотра в уведомлении."""
    cleaned = flatten(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(1, limit - 1)].rstrip() + "…"
