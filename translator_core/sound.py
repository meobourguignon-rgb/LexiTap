"""Звук уведомления: восьмибитный «level up» и мягкий сигнал ошибки.

assets/notify.wav — готовый CC0-звук с OpenGameArt (набор Chiptune SFX Pack,
автор FrogPog), он лежит в assets и попадает в собранный .exe. WAV-файлы
генерируются кодом только как запасной вариант, если пользователь удалил
файл из assets: так папка остаётся переносной и звук не пропадает.
Любой свой .wav можно положить в assets и указать его в config.json.
"""

from __future__ import annotations

import logging
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .paths import ASSETS_DIR, resource_asset

LOGGER = logging.getLogger(__name__)

SAMPLE_RATE = 44100


@dataclass(frozen=True)
class _Note:
    start: float
    duration: float
    frequency: float
    amplitude: float
    decay: float = 12.0
    glide: float = 0.0


@dataclass(frozen=True)
class _SoundProfile:
    notes: tuple[_Note, ...]
    length: float


_PROFILES: dict[str, _SoundProfile] = {
    # Запасной вариант на случай, если assets/notify.wav удалён.
    "notify.wav": _SoundProfile(
        notes=(
            _Note(0.00, 0.10, 987.77, 0.55, decay=22.0),
            _Note(0.07, 0.24, 1318.51, 0.45, decay=12.0),
            _Note(0.14, 0.30, 1975.53, 0.18, decay=16.0),
        ),
        length=0.62,
    ),
    "error.wav": _SoundProfile(
        notes=(
            _Note(0.00, 0.16, 440.00, 0.40, decay=16.0),
            _Note(0.11, 0.28, 311.13, 0.40, decay=11.0),
        ),
        length=0.58,
    ),
}


def _render(profile: _SoundProfile) -> bytes:
    total = int(profile.length * SAMPLE_RATE)
    samples = [0.0] * total

    for note in profile.notes:
        begin = int(note.start * SAMPLE_RATE)
        length = int(note.duration * SAMPLE_RATE)
        phase = 0.0
        for index in range(length):
            frame = begin + index
            if frame >= total:
                break
            position = index / SAMPLE_RATE
            frequency = note.frequency * (1.0 + note.glide * position)
            phase += 2.0 * math.pi * frequency / SAMPLE_RATE
            attack = min(1.0, position / 0.006)
            envelope = attack * math.exp(-note.decay * position)
            tone = (
                math.sin(phase)
                + 0.30 * math.sin(2.0 * phase)
                + 0.10 * math.sin(3.0 * phase)
            ) / 1.40
            samples[frame] += note.amplitude * envelope * tone

    fade_frames = max(1, int(0.012 * SAMPLE_RATE))
    for index in range(fade_frames):
        factor = index / fade_frames
        samples[total - fade_frames + index] *= factor

    frames = bytearray()
    for sample in samples:
        value = int(math.tanh(sample) * 32000)
        frames += int(max(-32768, min(32767, value))).to_bytes(2, "little", signed=True)
    return bytes(frames)


def _write_wav(path: Path, profile: _SoundProfile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(_render(profile))


def ensure_defaults() -> None:
    """Создать стандартные звуки в assets, если пользователь их не удалял."""
    for name, profile in _PROFILES.items():
        target = ASSETS_DIR / name
        if target.exists():
            continue
        try:
            _write_wav(target, profile)
            LOGGER.info("Сгенерирован звук %s", target)
        except OSError as exc:
            LOGGER.warning("Не удалось создать %s: %s", target, exc)


def play(name: str) -> None:
    """Проиграть звук асинхронно, не блокируя интерфейс."""
    path = resource_asset(name)
    if not path.exists():
        ensure_defaults()
        path = resource_asset(name)
    if not path.exists():
        return

    try:
        import winsound
    except ImportError:
        return

    try:
        winsound.PlaySound(
            str(path),
            winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
        )
    except (OSError, RuntimeError) as exc:
        LOGGER.warning("Не удалось проиграть %s: %s", path, exc)


def available_sounds() -> Sequence[str]:
    return tuple(_PROFILES)
