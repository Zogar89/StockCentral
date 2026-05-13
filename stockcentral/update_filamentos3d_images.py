from __future__ import annotations

import argparse
import json
from pathlib import Path

from stockcentral.build_data import FILAMENTOS3D_METADATA_CACHE, load_filamentos3d_metadata

DEFAULT_STOCK_PATH = Path("public/data/stock.json")


def apply_filamentos3d_images(
    stock_path: str | Path = DEFAULT_STOCK_PATH,
    metadata_path: str | Path = FILAMENTOS3D_METADATA_CACHE,
) -> int:
    path = Path(stock_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    metadata = load_filamentos3d_metadata(metadata_path)
    updated_count = 0

    for product in payload.get("products", []):
        if not isinstance(product, dict) or product.get("brand") != "3N3":
            continue
        product_id = str(product.get("id", ""))
        data = metadata.get(product_id, {})
        image_url = data.get("image_url", "")
        if not image_url:
            if product.get("image_source") == "provider":
                product["image_url"] = ""
                product["image_source"] = ""
                updated_count += 1
            continue
        product["image_url"] = image_url
        product["image_source"] = "provider"
        if data.get("sku"):
            product["sku"] = data["sku"]
        updated_count += 1

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return updated_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica fotos 3N3 desde cache Filamentos3D sin refrescar stock.")
    parser.add_argument("--stock", default=str(DEFAULT_STOCK_PATH))
    parser.add_argument("--metadata", default=str(FILAMENTOS3D_METADATA_CACHE))
    args = parser.parse_args()

    updated_count = apply_filamentos3d_images(args.stock, args.metadata)
    print(f"Productos 3N3 actualizados con foto de proveedor: {updated_count}")


if __name__ == "__main__":
    main()
