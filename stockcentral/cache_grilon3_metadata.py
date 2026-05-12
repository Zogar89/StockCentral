from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

from stockcentral.build_data import GRILON3_METADATA_CACHE
from stockcentral.connectors.grilon3_catalog import (
    enrich_grilon3_catalog_details,
    fetch_grilon3_catalog,
    fetch_grilon3_sitemap_catalog,
)
from stockcentral.models import RawStockItem
from stockcentral.normalize import normalize_record
from stockcentral.providers import MANUFACTURERS

GRILON3_IMAGE_ASSETS_DIR = Path("public/assets/grilon3")
GRILON3_IMAGE_PUBLIC_PREFIX = "assets/grilon3"


def build_grilon3_metadata_cache(timeout_seconds: int = 4, max_workers: int = 12) -> dict[str, dict[str, str]]:
    catalog = fetch_grilon3_catalog(MANUFACTURERS["grilon3"].products_url)
    catalog.update(fetch_grilon3_sitemap_catalog())
    enriched = enrich_grilon3_catalog_details(
        catalog,
        timeout_seconds=timeout_seconds,
        max_workers=max_workers,
    )
    cache: dict[str, dict[str, str]] = {}
    for _, product in sorted(enriched.items()):
        data = {
            "pantone": product.pantone,
            "sku": product.sku,
            "ean": product.ean,
            "image_url": product.image_url,
        }
        clean = {key: value for key, value in data.items() if value}
        if clean:
            cache[grilon3_metadata_cache_key(product.title)] = clean
    return cache


def write_grilon3_metadata_cache(
    output_path: str | Path = GRILON3_METADATA_CACHE,
    timeout_seconds: int = 4,
    max_workers: int = 12,
    download_images: bool = True,
    assets_dir: str | Path = GRILON3_IMAGE_ASSETS_DIR,
    image_url_prefix: str = GRILON3_IMAGE_PUBLIC_PREFIX,
) -> dict[str, dict[str, str]]:
    cache = build_grilon3_metadata_cache(timeout_seconds=timeout_seconds, max_workers=max_workers)
    if download_images:
        cache = download_grilon3_images(
            cache,
            assets_dir=assets_dir,
            image_url_prefix=image_url_prefix,
            timeout_seconds=timeout_seconds,
        )
    write_metadata_cache(cache, output_path)
    return cache


def write_metadata_cache(cache: dict[str, dict[str, str]], output_path: str | Path = GRILON3_METADATA_CACHE) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_metadata_cache(path: str | Path = GRILON3_METADATA_CACHE) -> dict[str, dict[str, str]]:
    cache_path = Path(path)
    if not cache_path.exists():
        return {}
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    return {
        str(key): {str(data_key): str(data_value) for data_key, data_value in data.items() if data_value}
        for key, data in payload.items()
        if isinstance(data, dict)
    }


def download_grilon3_images(
    cache: dict[str, dict[str, str]],
    assets_dir: str | Path = GRILON3_IMAGE_ASSETS_DIR,
    image_url_prefix: str = GRILON3_IMAGE_PUBLIC_PREFIX,
    timeout_seconds: int = 8,
) -> dict[str, dict[str, str]]:
    asset_dir = Path(assets_dir)
    asset_dir.mkdir(parents=True, exist_ok=True)
    remote_to_public_path: dict[str, str] = {}
    updated: dict[str, dict[str, str]] = {}

    for key, data in cache.items():
        clean = dict(data)
        remote_url = clean.get("image_remote_url") or clean.get("image_url", "")
        if not _is_remote_url(remote_url):
            updated[key] = clean
            continue

        public_path = remote_to_public_path.get(remote_url)
        if not public_path:
            public_path = _download_image(remote_url, asset_dir, image_url_prefix, timeout_seconds)
            remote_to_public_path[remote_url] = public_path
        if public_path:
            clean["image_remote_url"] = remote_url
            clean["image_url"] = public_path
        updated[key] = clean

    return updated


def _download_image(remote_url: str, assets_dir: Path, image_url_prefix: str, timeout_seconds: int) -> str:
    target = assets_dir / _asset_filename(remote_url)
    public_path = f"{image_url_prefix.rstrip('/')}/{target.name}"
    if target.exists() and target.stat().st_size > 0:
        return public_path

    response = requests.get(remote_url, timeout=timeout_seconds)
    response.raise_for_status()
    if not response.content:
        return ""
    target.write_bytes(response.content)
    return public_path


def _asset_filename(remote_url: str) -> str:
    parsed = urlparse(remote_url)
    source_name = Path(parsed.path).name or "grilon3-image.jpg"
    stem = slug(Path(source_name).stem) or "grilon3-image"
    suffix = Path(source_name).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    digest = hashlib.sha1(remote_url.encode("utf-8")).hexdigest()[:8]
    return f"{stem}-{digest}{suffix}"


def _is_remote_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def grilon3_metadata_cache_key(title: str) -> str:
    fields = normalize_record(
        RawStockItem(
            source_id="grilon3_catalog",
            provider_name="Grilon3",
            provider_zone="",
            provider_url=MANUFACTURERS["grilon3"].official_site_url,
            original_name=title,
            stock_quantity=None,
            source_url=MANUFACTURERS["grilon3"].products_url,
            brand_hint="Grilon3",
        )
    )
    parts = [fields.material, fields.variant, fields.color, fields.brand]
    return "-".join(slug(part) for part in parts if part)


def slug(value: str) -> str:
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    folded = without_marks.lower()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualiza la cache local de metadatos desde fichas Grilon3.")
    parser.add_argument("--output", default=str(GRILON3_METADATA_CACHE))
    parser.add_argument("--timeout-seconds", type=int, default=4)
    parser.add_argument("--max-workers", type=int, default=12)
    parser.add_argument("--assets-dir", default=str(GRILON3_IMAGE_ASSETS_DIR))
    parser.add_argument("--image-url-prefix", default=GRILON3_IMAGE_PUBLIC_PREFIX)
    parser.add_argument("--skip-image-download", action="store_true")
    parser.add_argument("--images-only", action="store_true", help="Descarga imágenes usando la cache existente sin refrescar fichas.")
    args = parser.parse_args()

    if args.images_only:
        cache = download_grilon3_images(
            load_metadata_cache(args.output),
            assets_dir=args.assets_dir,
            image_url_prefix=args.image_url_prefix,
            timeout_seconds=args.timeout_seconds,
        )
        write_metadata_cache(cache, args.output)
    else:
        cache = write_grilon3_metadata_cache(
            output_path=args.output,
            timeout_seconds=args.timeout_seconds,
            max_workers=args.max_workers,
            download_images=not args.skip_image_download,
            assets_dir=args.assets_dir,
            image_url_prefix=args.image_url_prefix,
        )
    print(f"Cache Grilon3 actualizada: {len(cache)} productos")


if __name__ == "__main__":
    main()
