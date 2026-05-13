from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
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
from stockcentral.normalize import COLOR_RULES, build_display_name, build_product_id, normalize_record
from stockcentral.providers import MANUFACTURERS, SOURCES, SourceConfig
from stockcentral.thumbnails import thumbnail_url_for

GRILON3_METADATA_CACHE = Path("stockcentral/data/grilon3_metadata.json")
FILAMENTOS3D_METADATA_CACHE = Path("stockcentral/data/filamentos3d_metadata.json")

ZONE_ORDER = {
    "Zona Norte": 0,
    "Zona Oeste": 1,
    "Zona Sur": 2,
}

DEFAULT_ENRICHMENT = {
    "manufacturer_product_url": "",
    "image_url": "",
    "image_source": "",
    "pantone": "",
    "sku": "",
    "ean": "",
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
            }

        _add_offer_to_group(grouped[product_id], _offer_from_raw(item))

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
                "pantone": getattr(catalog_product, "pantone", ""),
                "sku": getattr(catalog_product, "sku", ""),
                "ean": getattr(catalog_product, "ean", ""),
            },
            "offers": [],
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

    catalog = fetch_grilon3_catalog(MANUFACTURERS["grilon3"].products_url) if catalog is None else catalog
    metadata = load_grilon3_metadata()
    enrichments: dict[str, dict[str, str]] = {}

    for item in raw_items:
        fields = normalize_record(item)
        product_id = build_product_id(fields)
        if _is_sampler_or_3d_pen_item(item):
            continue
        enrichment = enrich_with_grilon3_catalog(fields, catalog)
        cache_data = _grilon3_metadata_for_fields(metadata, fields)
        enrichment["manufacturer_product_url"] = enrichment.get("manufacturer_product_url", "") or cache_data.get("manufacturer_product_url", "")
        enrichment["pantone"] = enrichment.get("pantone", "") or cache_data.get("pantone", "")
        enrichment["sku"] = enrichment.get("sku", "") or cache_data.get("sku", "")
        enrichment["ean"] = enrichment.get("ean", "") or cache_data.get("ean", "")
        if not enrichment["image_url"] and cache_data.get("image_url"):
            enrichment["image_url"] = cache_data["image_url"]
            enrichment["image_source"] = "manufacturer"
        if enrichment["manufacturer_product_url"] or enrichment["image_url"]:
            enrichments[product_id] = enrichment
        elif enrichment["pantone"] or enrichment["sku"] or enrichment["ean"]:
            enrichments[product_id] = enrichment

    return enrichments


def build_filamentos3d_enrichments(
    raw_items: list[RawStockItem],
    metadata: Mapping[str, dict[str, str]] | None = None,
) -> dict[str, dict[str, str]]:
    metadata = load_filamentos3d_metadata() if metadata is None else metadata
    enrichments: dict[str, dict[str, str]] = {}

    for item in raw_items:
        fields = normalize_record(item)
        if fields.brand != "3N3":
            continue
        product_id = build_product_id(fields)
        cache_data = metadata.get(product_id, {})
        image_url = cache_data.get("image_url", "")
        if not image_url:
            continue

        enrichment = {
            "image_url": image_url,
            "image_source": "provider",
        }
        if cache_data.get("sku"):
            enrichment["sku"] = cache_data["sku"]
        enrichments[product_id] = enrichment

    return enrichments


def _is_sampler_or_3d_pen_item(item: RawStockItem) -> bool:
    text = f" {item.original_name.upper()} "
    return " SAMPLER " in text or "LAPIZ 3D" in text or "LÁPIZ 3D" in text


def fetch_grilon3_catalog_products() -> dict[str, object]:
    from stockcentral.connectors.grilon3_catalog import apply_grilon3_metadata, fetch_grilon3_catalog, fetch_grilon3_sitemap_catalog

    catalog = fetch_grilon3_catalog(MANUFACTURERS["grilon3"].products_url)
    try:
        for product_id, product in fetch_grilon3_sitemap_catalog().items():
            if product_id in catalog and catalog[product_id].product_url != product.product_url:
                product_id = f"{product_id}-{_slug(product.product_url.rstrip('/').rsplit('/', 1)[-1])}"
            catalog[product_id] = product
    except Exception:
        pass
    return apply_grilon3_metadata(catalog, load_grilon3_metadata())


def load_grilon3_metadata(path: str | Path = GRILON3_METADATA_CACHE) -> dict[str, dict[str, str]]:
    cache_path = Path(path)
    if not cache_path.exists():
        return {}
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    metadata = {}
    for product_id, data in payload.items():
        if isinstance(data, str):
            data = {"pantone": data}
        if not isinstance(data, dict):
            continue
        clean = {
            key: str(data.get(key, ""))
            for key in ["manufacturer_product_url", "pantone", "sku", "ean", "image_url"]
            if data.get(key)
        }
        if clean:
            metadata[str(product_id)] = clean
    return metadata


def load_filamentos3d_metadata(path: str | Path = FILAMENTOS3D_METADATA_CACHE) -> dict[str, dict[str, str]]:
    cache_path = Path(path)
    if not cache_path.exists():
        return {}
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    metadata = {}
    for product_id, data in payload.items():
        if not isinstance(data, dict):
            continue
        clean = {
            key: str(data.get(key, ""))
            for key in ["provider_product_url", "image_url", "image_remote_url", "sku", "line_code"]
            if data.get(key)
        }
        if clean:
            metadata[str(product_id)] = clean
    return metadata


def _grilon3_metadata_for_fields(metadata: Mapping[str, dict[str, str]], fields) -> dict[str, str]:
    exact = metadata.get(_grilon3_metadata_cache_key(fields), {})
    unknown_diameter = metadata.get(_grilon3_metadata_unknown_diameter_cache_key(fields), {})
    legacy = metadata.get(_grilon3_metadata_legacy_cache_key(fields), {})
    legacy = _strip_large_presentation_metadata(legacy, fields)
    unknown_diameter = _strip_large_presentation_metadata(unknown_diameter, fields)
    exact = _strip_large_presentation_metadata(exact, fields)
    legacy = _strip_color_mismatched_image_metadata(legacy, fields)
    unknown_diameter = _strip_color_mismatched_image_metadata(unknown_diameter, fields)
    exact = _strip_color_mismatched_image_metadata(exact, fields)
    return {**legacy, **unknown_diameter, **exact}


def _grilon3_metadata_cache_key(fields) -> str:
    return build_product_id(fields)


def _grilon3_metadata_unknown_diameter_cache_key(fields) -> str:
    weight = str(fields.weight_g) if fields.weight_g is not None else "unknown"
    parts = [
        fields.material,
        fields.variant,
        fields.color,
        "unknown",
        weight,
        fields.brand,
    ]
    return "-".join(_slug(part) for part in parts if part)


def _grilon3_metadata_legacy_cache_key(fields) -> str:
    parts = [fields.material, fields.variant, fields.color, fields.brand]
    return "-".join(_slug(part) for part in parts if part)


def _strip_large_presentation_metadata(data: Mapping[str, str], fields) -> dict[str, str]:
    if not data:
        return {}
    clean = dict(data)
    if fields.weight_g and fields.weight_g >= 2500:
        return clean
    marker_text = " ".join(
        clean.get(key, "")
        for key in ["manufacturer_product_url", "image_url", "sku", "ean"]
    ).lower()
    if "megafill" not in marker_text and "maxicarrete" not in marker_text:
        return clean
    for key in ["manufacturer_product_url", "image_url", "sku", "ean"]:
        clean.pop(key, None)
    return clean


def _strip_color_mismatched_image_metadata(data: Mapping[str, str], fields) -> dict[str, str]:
    if not data:
        return {}
    clean = dict(data)
    expected_color = getattr(fields, "color", "")
    detected_color = _image_metadata_color(clean)
    if expected_color and detected_color and not _colors_match(detected_color, expected_color):
        clean.pop("image_url", None)
        clean.pop("image_remote_url", None)
    return clean


def _image_metadata_color(data: Mapping[str, str]) -> str:
    image_text = " ".join(data.get(key, "") for key in ["image_url", "image_remote_url"])
    filename = image_text.rsplit("/", 1)[-1]
    slug = _slug(filename)
    compact = slug.replace("-", "")
    for pattern, color in sorted(COLOR_RULES, key=lambda item: len(_slug(item[0])), reverse=True):
        pattern_slug = _slug(pattern)
        color_slug = _slug(color)
        if pattern_slug and pattern_slug in slug:
            return color
        if color_slug and color_slug in slug:
            return color
        if pattern_slug and pattern_slug.replace("-", "") in compact:
            return color
        if color_slug and color_slug.replace("-", "") in compact:
            return color
    return ""


def _colors_match(detected_color: str, expected_color: str) -> bool:
    detected = _slug(detected_color)
    expected = _slug(expected_color)
    return detected == expected or (detected == "piel" and expected.startswith("piel-"))


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    folded = without_marks.lower()
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build public StockCentral JSON data.")
    parser.add_argument("--output", default="public/data/stock.json")
    args = parser.parse_args()

    raw_items, source_errors = collect_raw_items()
    try:
        catalog_products = fetch_grilon3_catalog_products()
        enrichments = {
            **build_filamentos3d_enrichments(raw_items),
            **build_grilon3_enrichments(raw_items, catalog_products),
        }
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


def _add_offer_to_group(group: dict[str, object], offer: Offer) -> None:
    offers = group["offers"]  # type: ignore[assignment]
    for index, existing_offer in enumerate(offers):
        if not _is_same_provider_alias(existing_offer, offer):
            continue
        offers[index] = _preferred_offer(existing_offer, offer)
        return
    offers.append(offer)


def _is_same_provider_alias(left: Offer, right: Offer) -> bool:
    return (
        left.source_id == right.source_id
        and left.provider_name == right.provider_name
        and _canonical_offer_name(left.original_name) == _canonical_offer_name(right.original_name)
    )


def _preferred_offer(left: Offer, right: Offer) -> Offer:
    left_quantity = left.stock_quantity if left.stock_quantity is not None else -1
    right_quantity = right.stock_quantity if right.stock_quantity is not None else -1
    return right if right_quantity > left_quantity else left


def _product_from_group(product_id: str, data: Mapping[str, object]) -> ProductGroup:
    fields = data["fields"]
    enrichment = data["enrichment"]
    offers = sorted(data["offers"], key=_offer_sort_key)  # type: ignore[arg-type]
    _validate_unique_provider_offers(product_id, offers)

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
        thumbnail_url=thumbnail_url_for(str(enrichment["image_url"])),
        image_source=enrichment["image_source"],  # type: ignore[arg-type]
        pantone=str(enrichment["pantone"]),
        sku=str(enrichment["sku"]),
        ean=str(enrichment["ean"]),
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


def _validate_unique_provider_offers(product_id: str, offers: list[Offer]) -> None:
    provider_counts = Counter(offer.provider_name for offer in offers)
    duplicated_providers = sorted(provider for provider, count in provider_counts.items() if count > 1)
    if not duplicated_providers:
        return

    details = []
    for provider in duplicated_providers:
        provider_offers = [offer.original_name for offer in offers if offer.provider_name == provider]
        details.append(f"{provider}: {' | '.join(provider_offers)}")
    raise ValueError(
        f"Product {product_id} has repeated provider offers. "
        f"This usually means different products were normalized together. "
        f"{'; '.join(details)}"
    )


def _canonical_offer_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    folded = without_marks.upper()
    return re.sub(r"\s+", " ", folded).strip()


def _now() -> str:
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
