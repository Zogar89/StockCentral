from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from stockcentral.thumbnails import ensure_thumbnail_for_url


IMAGE_KEYS = ("image_remote_url", "image_url")
METADATA_KEYS = ("pantone", "sku", "ean")


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: str | Path, payload: Any) -> None:
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def refreshed_by_url(refreshed_cache: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    by_url: dict[str, dict[str, str]] = {}
    for data in refreshed_cache.values():
        product_url = data.get("manufacturer_product_url", "")
        image_url = data.get("image_url", "")
        if product_url and image_url:
            by_url[product_url] = data
    return by_url


def update_metadata_cache(
    metadata: dict[str, dict[str, str]],
    refreshed: dict[str, dict[str, str]],
) -> int:
    changes = 0
    for data in metadata.values():
        source = refreshed.get(data.get("manufacturer_product_url", ""))
        if not source:
            continue
        for key in (*IMAGE_KEYS, *METADATA_KEYS):
            if source.get(key) and data.get(key) != source[key]:
                data[key] = source[key]
                changes += 1
    return changes


def update_stock_payload(
    payload: dict[str, Any],
    metadata: dict[str, dict[str, str]],
    refreshed: dict[str, dict[str, str]],
) -> int:
    changes = 0
    for product in payload.get("products", []):
        if product.get("brand") != "Grilon3":
            continue
        source = {
            **metadata.get(product.get("id", ""), {}),
            **refreshed.get(product.get("manufacturer_product_url", ""), {}),
        }
        if not source:
            continue
        if source.get("image_url"):
            thumbnail_url = ensure_thumbnail_for_url(source["image_url"])
            if product.get("image_url") != source["image_url"]:
                product["image_url"] = source["image_url"]
                product["image_source"] = "manufacturer"
                changes += 1
            if product.get("thumbnail_url", "") != thumbnail_url:
                product["thumbnail_url"] = thumbnail_url
                changes += 1
        for key in METADATA_KEYS:
            if source.get(key) and not product.get(key):
                product[key] = source[key]
                changes += 1
    return changes


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica fotos oficiales nuevas de Grilon3 sin refrescar stock.")
    parser.add_argument("--refreshed-cache", required=True)
    parser.add_argument("--metadata-cache", default="stockcentral/data/grilon3_metadata.json")
    parser.add_argument("--stock-json", default="public/data/stock.json")
    args = parser.parse_args()

    metadata = load_json(args.metadata_cache)
    refreshed = refreshed_by_url(load_json(args.refreshed_cache))
    stock = load_json(args.stock_json)

    metadata_changes = update_metadata_cache(metadata, refreshed)
    stock_changes = update_stock_payload(stock, metadata, refreshed)

    write_json(args.metadata_cache, metadata)
    write_json(args.stock_json, stock)

    print(f"Metadata actualizada: {metadata_changes} campos")
    print(f"Stock actualizado: {stock_changes} campos")


if __name__ == "__main__":
    main()
