from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Mapping
from zoneinfo import ZoneInfo

from stockcentral.models import (
    ManufacturerInfo,
    Offer,
    ProductGroup,
    ProviderStats,
    RawStockItem,
    SourceStatus,
    StockStatus,
)
from stockcentral.normalize import build_display_name, build_product_id, normalize_record
from stockcentral.providers import MANUFACTURERS, SOURCES, SourceConfig

ZONE_ORDER = {
    "Zona Norte": 0,
    "Zona Oeste": 1,
    "Zona Sur": 2,
}

DEFAULT_ENRICHMENT = {
    "manufacturer_product_url": "",
    "image_url": "",
    "image_source": "",
}


def build_payload(
    raw_items: list[RawStockItem],
    sources: Mapping[str, SourceConfig] = SOURCES,
    manufacturers: Mapping[str, ManufacturerInfo] = MANUFACTURERS,
    generated_at: str | None = None,
    enrichments: Mapping[str, Mapping[str, str]] | None = None,
    source_errors: Mapping[str, str] | None = None,
    catalog_products: Mapping[str, object] | None = None,
) -> dict[str, object]:
    generated = generated_at or _now()
    enrichments = enrichments or {}
    source_errors = source_errors or {}
    grouped: dict[str, dict[str, object]] = {}

    for item in raw_items:
        fields = normalize_record(item)
        product_id = build_product_id(fields)
        enrichment = {**DEFAULT_ENRICHMENT, **enrichments.get(product_id, {})}

        if product_id not in grouped:
            grouped[product_id] = {
                "fields": fields,
                "enrichment": enrichment,
                "offers": [],
                "offer_keys": set(),
            }

        offer_key = (item.source_id, item.original_name, item.stock_quantity)
        if offer_key in grouped[product_id]["offer_keys"]:  # type: ignore[operator]
            continue
        grouped[product_id]["offer_keys"].add(offer_key)  # type: ignore[union-attr]
        grouped[product_id]["offers"].append(_offer_from_raw(item))  # type: ignore[index, union-attr]

    for product_id, catalog_product in (catalog_products or {}).items():
        if product_id in grouped:
            continue
        fields = normalize_record(
            RawStockItem(
                source_id="grilon3_catalog",
                provider_name="Grilon3",
                provider_zone="",
                provider_url=MANUFACTURERS["grilon3"].official_site_url,
                original_name=catalog_product.title,
                stock_quantity=None,
                source_url=catalog_product.product_url,
                brand_hint="Grilon3",
            )
        )
        if fields.diameter_mm != 2.85 or fields.weight_g != 1000:
            continue
        grouped[product_id] = {
            "fields": fields,
            "enrichment": {
                "manufacturer_product_url": catalog_product.product_url,
                "image_url": catalog_product.image_url,
                "image_source": "manufacturer" if catalog_product.image_url else "",
            },
            "offers": [],
            "offer_keys": set(),
        }

    products = [
        _product_from_group(product_id, data)
        for product_id, data in grouped.items()
    ]
    products.sort(key=_product_sort_key)

    source_statuses = [
        _source_status(source, raw_items, generated, source_errors.get(source.id, ""))
        for source in sorted(sources.values(), key=_source_sort_key)
    ]

    return {
        "generated_at": generated,
        "products": [product.to_dict() for product in products],
        "sources": [source.to_dict() for source in source_statuses],
        "manufacturers": [manufacturer.to_dict() for manufacturer in manufacturers.values()],
    }


def write_payload(payload: Mapping[str, object], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def collect_raw_items(
    sources: Mapping[str, SourceConfig] = SOURCES,
    updated_at: str | None = None,
) -> tuple[list[RawStockItem], dict[str, str]]:
    generated = updated_at or _now()
    items: list[RawStockItem] = []
    errors: dict[str, str] = {}

    for source in sources.values():
        try:
            items.extend(_fetch_source_items(source, generated))
        except Exception as exc:  # pragma: no cover - exact requests errors vary by provider.
            errors[source.id] = str(exc)

    return items, errors


def build_grilon3_enrichments(
    raw_items: list[RawStockItem],
    catalog: Mapping[str, object] | None = None,
) -> dict[str, dict[str, str]]:
    from stockcentral.connectors.grilon3_catalog import enrich_with_grilon3_catalog, fetch_grilon3_catalog

    catalog = catalog or fetch_grilon3_catalog(MANUFACTURERS["grilon3"].products_url)
    enrichments: dict[str, dict[str, str]] = {}

    for item in raw_items:
        fields = normalize_record(item)
        product_id = build_product_id(fields)
        enrichment = enrich_with_grilon3_catalog(fields, catalog)
        if enrichment["manufacturer_product_url"] or enrichment["image_url"]:
            enrichments[product_id] = enrichment

    return enrichments


def fetch_grilon3_catalog_products() -> dict[str, object]:
    from stockcentral.connectors.grilon3_catalog import fetch_grilon3_catalog, fetch_grilon3_sitemap_catalog

    catalog = fetch_grilon3_catalog(MANUFACTURERS["grilon3"].products_url)
    try:
        catalog.update(fetch_grilon3_sitemap_catalog())
    except Exception:
        pass
    return catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="Build public StockCentral JSON data.")
    parser.add_argument("--output", default="public/data/stock.json")
    args = parser.parse_args()

    raw_items, source_errors = collect_raw_items()
    try:
        catalog_products = fetch_grilon3_catalog_products()
        enrichments = build_grilon3_enrichments(raw_items, catalog_products)
    except Exception:
        catalog_products = {}
        enrichments = {}
    payload = build_payload(
        raw_items,
        enrichments=enrichments,
        source_errors=source_errors,
        catalog_products=catalog_products,
    )
    write_payload(payload, args.output)


def _offer_from_raw(item: RawStockItem) -> Offer:
    return Offer(
        source_id=item.source_id,
        provider_name=item.provider_name,
        provider_zone=item.provider_zone,
        provider_url=item.provider_url,
        original_name=item.original_name,
        stock_quantity=item.stock_quantity,
        stock_status=_stock_status(item.stock_quantity),
        source_url=item.source_url,
        updated_at=item.updated_at,
    )


def _product_from_group(product_id: str, data: Mapping[str, object]) -> ProductGroup:
    fields = data["fields"]
    enrichment = data["enrichment"]
    offers = sorted(data["offers"], key=_offer_sort_key)  # type: ignore[arg-type]

    return ProductGroup(
        id=product_id,
        material=fields.material,
        variant=fields.variant,
        color=fields.color,
        diameter_mm=fields.diameter_mm,
        weight_g=fields.weight_g,
        brand=fields.brand,
        manufacturer_name=fields.manufacturer_name,
        manufacturer_product_url=str(enrichment["manufacturer_product_url"]),
        image_url=str(enrichment["image_url"]),
        image_source=enrichment["image_source"],  # type: ignore[arg-type]
        display_name=build_display_name(fields),
        offers=offers,
    )


def _fetch_source_items(source: SourceConfig, updated_at: str) -> list[RawStockItem]:
    if source.connector == "google_sheet":
        from stockcentral.connectors.google_sheet import fetch_sheet_items

        return fetch_sheet_items(source, updated_at)
    if source.connector == "filamentos3d":
        from stockcentral.connectors.filamentos3d import fetch_filamentos3d_items

        return fetch_filamentos3d_items(source, updated_at)
    raise ValueError(f"Unknown connector for {source.id}: {source.connector}")


def _source_status(
    source: SourceConfig,
    raw_items: list[RawStockItem],
    generated_at: str,
    error_message: str = "",
) -> SourceStatus:
    source_items = [item for item in raw_items if item.source_id == source.id]
    stats = _provider_stats(source_items)
    status = "error" if error_message else "ok"
    return SourceStatus(
        id=source.id,
        name=source.name,
        zone=source.zone,
        homepage_url=source.homepage_url,
        source_url=source.source_url,
        contact_whatsapp_url=source.contact_whatsapp_url,
        contact_phone=source.contact_phone,
        contact_email=source.contact_email,
        address=source.address,
        contact_url=source.contact_url or source.homepage_url,
        last_success_at="" if error_message else generated_at,
        last_attempt_at=generated_at,
        status=status,
        error_message=error_message,
        stats=stats,
    )


def _provider_stats(items: list[RawStockItem]) -> ProviderStats:
    total_stock_units = 0
    total_stock_kg = 0.0
    product_count = len(items)
    in_stock_product_count = 0
    out_of_stock_product_count = 0

    for item in items:
        if item.stock_quantity is None:
            continue
        if item.stock_quantity == 0:
            out_of_stock_product_count += 1
            continue
        if item.stock_quantity > 0:
            fields = normalize_record(item)
            in_stock_product_count += 1
            total_stock_units += item.stock_quantity
            if fields.weight_g is not None:
                total_stock_kg += item.stock_quantity * fields.weight_g / 1000

    return ProviderStats(
        total_stock_units=total_stock_units,
        total_stock_kg=round(total_stock_kg, 2),
        product_count=product_count,
        in_stock_product_count=in_stock_product_count,
        out_of_stock_product_count=out_of_stock_product_count,
    )


def _stock_status(stock_quantity: int | None) -> StockStatus:
    if stock_quantity is None:
        return "unknown"
    if stock_quantity <= 0:
        return "out_of_stock"
    return "in_stock"


def _product_sort_key(product: ProductGroup) -> tuple[int, str, str, str]:
    material_priority = 0 if product.material == "PLA" else 1
    return (material_priority, product.material, product.color, product.display_name)


def _source_sort_key(source: SourceConfig) -> tuple[int, str]:
    return (ZONE_ORDER.get(source.zone, 99), source.name)


def _offer_sort_key(offer: Offer) -> tuple[int, str]:
    return (ZONE_ORDER.get(offer.provider_zone, 99), offer.provider_name)


def _now() -> str:
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
