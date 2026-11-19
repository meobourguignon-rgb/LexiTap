"""Prepare square app icons from image.jpg for the window and the build."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "image.jpg"
ASSETS = ROOT / "assets"


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    with Image.open(SOURCE) as handle:
        image = ImageOps.fit(handle.convert("RGB"), (256, 256), method=Image.LANCZOS)

    image.save(ASSETS / "app.jpg", quality=92)
    image.save(
        ASSETS / "app.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Icons written to {ASSETS}")


if __name__ == "__main__":
    main()
