from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
from typing import Any


PUBLIC_DIR = Path("public")
THUMBNAIL_ROOT_URL = "assets/thumbs"
THUMBNAIL_SIZE = (160, 160)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def is_local_asset_url(image_url: str) -> bool:
    path = PurePosixPath(image_url)
    return bool(path.parts) and path.parts[0] == "assets" and not image_url.startswith(("http://", "https://"))


def thumbnail_url_for(image_url: str) -> str:
    if not image_url or not is_local_asset_url(image_url):
        return ""
    source = PurePosixPath(image_url)
    if len(source.parts) > 1 and source.parts[1] == "thumbs":
        return image_url
    return str(PurePosixPath(THUMBNAIL_ROOT_URL, *source.parts[1:]).with_suffix(".webp"))


def local_path_for_url(image_url: str, public_dir: str | Path = PUBLIC_DIR) -> Path:
    return Path(public_dir).joinpath(*PurePosixPath(image_url).parts)


def ensure_thumbnail_for_url(
    image_url: str,
    public_dir: str | Path = PUBLIC_DIR,
    size: tuple[int, int] = THUMBNAIL_SIZE,
    quality: int = 72,
) -> str:
    thumb_url = thumbnail_url_for(image_url)
    if not thumb_url:
        return ""

    source_path = local_path_for_url(image_url, public_dir)
    if not source_path.exists() or source_path.suffix.lower() not in IMAGE_SUFFIXES:
        return ""

    thumb_path = local_path_for_url(thumb_url, public_dir)
    if _thumbnail_is_current(source_path, thumb_path):
        return thumb_url

    generate_thumbnail(source_path, thumb_path, size=size, quality=quality)
    return thumb_url


def generate_thumbnail(
    source_path: str | Path,
    thumb_path: str | Path,
    size: tuple[int, int] = THUMBNAIL_SIZE,
    quality: int = 72,
) -> None:
    from PIL import Image, ImageOps

    source = Path(source_path)
    target = Path(thumb_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as image:
        normalized = ImageOps.exif_transpose(image)
        if normalized.mode not in {"RGB", "RGBA"}:
            normalized = normalized.convert("RGBA" if "A" in normalized.getbands() else "RGB")
        normalized.thumbnail(size, Image.Resampling.LANCZOS)
        if normalized.mode == "RGBA":
            normalized.save(target, "WEBP", quality=quality, method=6)
        else:
            normalized.convert("RGB").save(target, "WEBP", quality=quality, method=6)


def apply_thumbnails_to_stock(
    stock_json: str | Path = "public/data/stock.json",
    public_dir: str | Path = PUBLIC_DIR,
) -> int:
    path = Path(stock_json)
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    changes = 0

    for product in payload.get("products", []):
        if not isinstance(product, dict):
            continue
        image_url = str(product.get("image_url", ""))
        thumb_url = ensure_thumbnail_for_url(image_url, public_dir=public_dir)
        if product.get("thumbnail_url", "") != thumb_url:
            product["thumbnail_url"] = thumb_url
            changes += 1

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return changes


def _thumbnail_is_current(source_path: Path, thumb_path: Path) -> bool:
    return (
        thumb_path.exists()
        and thumb_path.stat().st_size > 0
        and thumb_path.stat().st_mtime >= source_path.stat().st_mtime
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera miniaturas WebP para las imagenes usadas por stock.json.")
    parser.add_argument("--stock-json", default="public/data/stock.json")
    parser.add_argument("--public-dir", default=str(PUBLIC_DIR))
    args = parser.parse_args()

    changes = apply_thumbnails_to_stock(args.stock_json, args.public_dir)
    print(f"Miniaturas actualizadas en stock: {changes} productos")


if __name__ == "__main__":
    main()
