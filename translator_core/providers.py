"""Перевод через бесплатные HTTP-эндпоинты, без ключей и зависимостей.

Основной канал — Google (неофициальный gtx-эндпоинт, автоопределение языка),
резервный — MyMemory. Оба вызываются через стандартный urllib, поэтому
приложению не нужен pip и его можно копировать папкой.
"""

from __future__ import annotations

import html
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Any, Callable

from .config import TranslationConfig
from .language import clamp_text, detect_language

LOGGER = logging.getLogger(__name__)

GOOGLE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
MYMEMORY_ENDPOINT = "https://api.mymemory.translated.net/get"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PortableTranslator/1.0"
MYMEMORY_LIMIT = 480
CACHE_LIMIT = 64
_PARAGRAPHS = re.compile(r"\n\s*\n")


class TranslationError(RuntimeError):
    """Перевод не удался по сетевой причине или из-за ответа сервиса."""


@dataclass(frozen=True)
class Translation:
    text: str
    source_language: str
    provider: str
    truncated_input: bool = False


def _fetch_json(url: str, timeout: float) -> Any:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except urllib.error.HTTPError as exc:
        raise TranslationError(f"сервис ответил кодом {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TranslationError("нет соединения с сервисом перевода") from exc
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TranslationError("сервис вернул некорректный ответ") from exc


def _google(text: str, target: str, timeout: float) -> Translation:
    query = urllib.parse.urlencode(
        {"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text}
    )
    payload = _fetch_json(f"{GOOGLE_ENDPOINT}?{query}", timeout)

    if not isinstance(payload, list) or not payload:
        raise TranslationError("Google: неожиданный формат ответа")

    channels = payload[0] if isinstance(payload[0], list) else []
    try:
        translated = "".join(str(channel[0]) for channel in channels if channel and channel[0])
    except (TypeError, IndexError) as exc:
        raise TranslationError("Google: не удалось разобрать перевод") from exc

    if not translated.strip():
        raise TranslationError("Google вернул пустой перевод")

    source = payload[2] if len(payload) > 2 and isinstance(payload[2], str) else "auto"
    return Translation(text=translated.strip(), source_language=source, provider="Google")


def _mymemory(text: str, target: str, timeout: float) -> Translation:
    prepared, truncated = clamp_text(text, MYMEMORY_LIMIT)
    source = detect_language(prepared)
    if source == target:
        source = "en" if target == "ru" else "ru"

    query = urllib.parse.urlencode({"q": prepared, "langpair": f"{source}|{target}"})
    payload = _fetch_json(f"{MYMEMORY_ENDPOINT}?{query}", timeout)
    if not isinstance(payload, dict):
        raise TranslationError("MyMemory: неожиданный формат ответа")

    status = payload.get("responseStatus")
    if str(status) != "200":
        detail = payload.get("responseDetails")
        raise TranslationError(f"MyMemory: {detail or 'перевод недоступен'}")

    data = payload.get("responseData")
    translated = data.get("translatedText") if isinstance(data, dict) else None
    if not isinstance(translated, str) or not translated.strip():
        raise TranslationError("MyMemory вернул пустой перевод")

    return Translation(
        text=html.unescape(translated.strip()),
        source_language=source,
        provider="MyMemory",
        truncated_input=truncated,
    )


_PROVIDERS: dict[str, Callable[[str, str, float], Translation]] = {
    "google": _google,
    "mymemory": _mymemory,
}


class Translator:
    """Цепочка провайдеров с кэшем на время работы приложения."""

    def __init__(self, config: TranslationConfig) -> None:
        self._config = config
        self._cache: OrderedDict[tuple[str, str], Translation] = OrderedDict()

    def translate(self, text: str, target: str) -> Translation:
        prepared, truncated = clamp_text(text, self._config.max_chars)
        if not prepared:
            raise TranslationError("выделенный текст пуст")

        key = (prepared, target)
        cached = self._cache.get(key)
        if cached is not None:
            self._cache.move_to_end(key)
            return replace(cached, truncated_input=cached.truncated_input or truncated)

        blocks = [block for block in _PARAGRAPHS.split(prepared) if block.strip()]
        if len(blocks) <= 1:
            result = self._translate_block(prepared, target)
        else:
            parts = [self._translate_block(block, target) for block in blocks]
            result = Translation(
                text="\n\n".join(part.text for part in parts),
                source_language=parts[0].source_language,
                provider=parts[0].provider,
                truncated_input=any(part.truncated_input for part in parts),
            )

        result = replace(result, truncated_input=result.truncated_input or truncated)
        self._cache[key] = result
        if len(self._cache) > CACHE_LIMIT:
            self._cache.popitem(last=False)
        return result

    def _translate_block(self, text: str, target: str) -> Translation:
        problems: list[str] = []
        for name in self._config.providers:
            provider = _PROVIDERS.get(name)
            if provider is None:
                problems.append(f"{name}: неизвестный сервис")
                continue
            try:
                return provider(text, target, self._config.timeout_seconds)
            except TranslationError as exc:
                problems.append(f"{name}: {exc}")
                LOGGER.warning("Провайдер %s не сработал: %s", name, exc)

        raise TranslationError("; ".join(problems) or "нет доступных сервисов перевода")
