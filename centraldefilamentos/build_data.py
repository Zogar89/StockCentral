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

from centraldefilamentos.models import (
    ManufacturerInfo,
    Offer,
    ProductGroup,
    ProviderStats,
    RawStockItem,
    SourceStatus,
    StockStatus,
)
from centraldefilamentos.normalize import COLOR_RULES, build_display_name, build_product_id, normalize_record
from centraldefilamentos.providers import MANUFACTURERS, SOURCES, SourceConfig
from centraldefilamentos.thumbnails import thumbnail_url_for

GRILON3_METADATA_CACHE = Path("centraldefilamentos/data/grilon3_metadata.json")
FILAMENTOS3D_METADATA_CACHE = Path("centraldefilamentos/data/filamentos3d_metadata.json")
DAILY_PROVIDER_STOCK_SNAPSHOT = Path("centraldefilamentos/data/daily_provider_stock_snapshot.json")
PROVIDER_STOCK_HISTORY = Path("centraldefilamentos/data/provider_stock_history.json")
PUBLIC_PROVIDER_STOCK_HISTORY = Path("public/data/provider_stock_history.json")
PUBLIC_BUSINESS_LOG = Path("public/data/build_business_log.json")
PUBLIC_TECHNICAL_LOG = Path("public/data/build_technical_log.json")

MIN_PRODUCTS_FOR_DROP_CHECK = 50
MIN_PROVIDER_STOCK_FOR_DROP_CHECK = 100
MAX_PRODUCT_DROP_RATIO = 0.40
MAX_PROVIDER_STOCK_DROP_RATIO = 0.60

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
    _write_json(output_path, payload)


def _write_json(path: str | Path, payload: Mapping[str, object]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_payload(path: str | Path) -> dict[str, object]:
    payload_path = Path(path)
    if not payload_path.exists():
        return {}
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def evaluate_build_quality(
    payload: Mapping[str, object],
    previous_payload: Mapping[str, object] | None = None,
    source_errors: Mapping[str, str] | None = None,
    enrichment_errors: Mapping[str, str] | None = None,
) -> dict[str, object]:
    previous_payload = previous_payload or {}
    source_errors = {str(source_id): _clean_error_message(error) for source_id, error in (source_errors or {}).items() if error}
    enrichment_errors = {str(source_id): _clean_error_message(error) for source_id, error in (enrichment_errors or {}).items() if error}
    current_metrics = _payload_quality_metrics(payload)
    previous_metrics = _payload_quality_metrics(previous_payload)
    last_good_sources = _last_good_sources(previous_payload, source_errors)
    technical_events: list[dict[str, object]] = []
    business_events: list[dict[str, object]] = []
    checks: list[dict[str, object]] = []
    schema_errors = _stock_payload_schema_errors(payload)

    if source_errors:
        checks.append({"name": "source_errors", "status": "failed", "failed_sources": sorted(source_errors)})
        for source_id, error_message in sorted(source_errors.items()):
            source_name = _source_name(payload, source_id)
            last_good = last_good_sources.get(source_id, {})
            last_good_text = ""
            if last_good:
                last_good_text = f" Se mantiene el ultimo dato bueno de {last_good.get('generated_at', '')}."
            technical_events.append(
                {
                    "level": "error",
                    "code": "source_error",
                    "source_id": source_id,
                    "message": error_message,
                }
            )
            business_events.append(
                {
                    "level": "error",
                    "code": "source_error",
                    "message": f"{source_name} no respondio correctamente. Se conserva la ultima publicacion buena.{last_good_text}",
                }
            )
    else:
        checks.append({"name": "source_errors", "status": "passed"})

    if enrichment_errors:
        checks.append({"name": "enrichment", "status": "warning", "failed_steps": sorted(enrichment_errors)})
        for enrichment_id, error_message in sorted(enrichment_errors.items()):
            technical_events.append(
                {
                    "level": "warning",
                    "code": "enrichment_error",
                    "source_id": enrichment_id,
                    "message": error_message,
                }
            )
            business_events.append(
                {
                    "level": "warning",
                    "code": "enrichment_error",
                    "message": "No se pudo actualizar parte de las imagenes o metadata enriquecida. El stock se publica con los datos disponibles.",
                }
            )
    else:
        checks.append({"name": "enrichment", "status": "passed"})

    if schema_errors:
        checks.append({"name": "schema", "status": "failed", "errors": schema_errors})
        for schema_error in schema_errors:
            technical_events.append({"level": "error", "code": "schema_error", "message": schema_error})
        business_events.append(
            {
                "level": "error",
                "code": "schema_error",
                "message": "La estructura del JSON final no paso las validaciones. Se conserva la ultima publicacion buena.",
            }
        )
    else:
        checks.append({"name": "schema", "status": "passed"})

    if current_metrics["product_count"] == 0:
        checks.append({"name": "non_empty_catalog", "status": "failed"})
        technical_events.append({"level": "error", "code": "empty_catalog", "message": "Current payload has no products."})
        business_events.append(
            {
                "level": "error",
                "code": "empty_catalog",
                "message": "La corrida no encontro productos. Se conserva la ultima publicacion buena.",
            }
        )
    else:
        checks.append({"name": "non_empty_catalog", "status": "passed", "product_count": current_metrics["product_count"]})

    previous_product_count = int(previous_metrics.get("product_count", 0))
    current_product_count = int(current_metrics.get("product_count", 0))
    if previous_product_count >= MIN_PRODUCTS_FOR_DROP_CHECK:
        product_drop = _drop_ratio(previous_product_count, current_product_count)
        if product_drop > MAX_PRODUCT_DROP_RATIO:
            checks.append(
                {
                    "name": "product_count_drop",
                    "status": "failed",
                    "previous": previous_product_count,
                    "current": current_product_count,
                    "drop_ratio": round(product_drop, 4),
                    "max_drop_ratio": MAX_PRODUCT_DROP_RATIO,
                }
            )
            technical_events.append(
                {
                    "level": "error",
                    "code": "product_count_drop",
                    "message": f"Product count dropped from {previous_product_count} to {current_product_count}.",
                }
            )
            business_events.append(
                {
                    "level": "error",
                    "code": "product_count_drop",
                    "message": "La cantidad de productos bajo demasiado contra la ultima corrida buena. Se conserva la publicacion anterior.",
                }
            )
        else:
            checks.append({"name": "product_count_drop", "status": "passed", "drop_ratio": round(product_drop, 4)})

    previous_sources = previous_metrics.get("sources", {})
    current_sources = current_metrics.get("sources", {})
    if isinstance(previous_sources, dict) and isinstance(current_sources, dict):
        for source_id, previous_source in sorted(previous_sources.items()):
            current_source = current_sources.get(source_id)
            if not isinstance(previous_source, dict) or not isinstance(current_source, dict):
                continue
            previous_stock = int(previous_source.get("total_stock_units", 0))
            current_stock = int(current_source.get("total_stock_units", 0))
            if previous_stock < MIN_PROVIDER_STOCK_FOR_DROP_CHECK:
                continue
            stock_drop = _drop_ratio(previous_stock, current_stock)
            if stock_drop <= MAX_PROVIDER_STOCK_DROP_RATIO:
                continue
            source_name = str(current_source.get("name") or previous_source.get("name") or source_id)
            checks.append(
                {
                    "name": "provider_stock_drop",
                    "status": "failed",
                    "source_id": source_id,
                    "previous": previous_stock,
                    "current": current_stock,
                    "drop_ratio": round(stock_drop, 4),
                    "max_drop_ratio": MAX_PROVIDER_STOCK_DROP_RATIO,
                }
            )
            technical_events.append(
                {
                    "level": "error",
                    "code": "provider_stock_drop",
                    "source_id": source_id,
                    "message": f"{source_id} stock dropped from {previous_stock} to {current_stock}.",
                }
            )
            business_events.append(
                {
                    "level": "error",
                    "code": "provider_stock_drop",
                    "message": f"{source_name} tuvo una baja de stock demasiado grande para publicarla automaticamente. Se conserva la publicacion anterior.",
                }
            )

    should_publish = not any(event.get("level") == "error" for event in technical_events)
    status = "ok" if should_publish else "blocked"
    summary = (
        "Publicacion habilitada. No se detectaron errores criticos."
        if should_publish
        else "Publicacion bloqueada por datos incompletos o sospechosos."
    )
    if should_publish:
        business_events.append({"level": "info", "code": "publish_ok", "message": "La actualizacion paso los controles y se puede publicar."})
        technical_events.append({"level": "info", "code": "publish_ok", "message": "Build quality checks passed."})

    return {
        "generated_at": str(payload.get("generated_at", "")),
        "status": status,
        "should_publish": should_publish,
        "summary": summary,
        "business_events": business_events,
        "technical_events": technical_events,
        "last_good_sources": last_good_sources,
        "metrics": {
            "current": current_metrics,
            "previous": previous_metrics,
        },
        "checks": checks,
    }


def write_build_logs(
    report: Mapping[str, object],
    business_path: str | Path = PUBLIC_BUSINESS_LOG,
    technical_path: str | Path = PUBLIC_TECHNICAL_LOG,
) -> None:
    business_log = {
        "generated_at": str(report.get("generated_at", "")),
        "status": str(report.get("status", "")),
        "should_publish": bool(report.get("should_publish", False)),
        "summary": str(report.get("summary", "")),
        "events": list(report.get("business_events", [])),
        "last_good_sources": report.get("last_good_sources", {}),
    }
    technical_log = {
        "generated_at": str(report.get("generated_at", "")),
        "status": str(report.get("status", "")),
        "should_publish": bool(report.get("should_publish", False)),
        "summary": str(report.get("summary", "")),
        "events": list(report.get("technical_events", [])),
        "last_good_sources": report.get("last_good_sources", {}),
        "metrics": report.get("metrics", {}),
        "checks": list(report.get("checks", [])),
    }
    _write_json(business_path, business_log)
    _write_json(technical_path, technical_log)


def load_daily_provider_stock_snapshot(path: str | Path = DAILY_PROVIDER_STOCK_SNAPSHOT) -> dict[str, object]:
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        return {}
    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def apply_provider_stock_deltas(payload: dict[str, object], snapshot: Mapping[str, object]) -> None:
    previous_counts = _provider_counts_for_delta(snapshot, str(payload.get("generated_at", "")))
    if not previous_counts:
        return

    for source in payload.get("sources", []):
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id", ""))
        if source_id not in previous_counts:
            continue
        stats = source.get("stats")
        if not isinstance(stats, dict):
            continue
        current_stock = _safe_int(stats.get("total_stock_units"))
        if current_stock is None:
            continue
        stats["stock_delta_units"] = current_stock - previous_counts[source_id]


def maybe_update_daily_provider_stock_snapshot(
    payload: Mapping[str, object],
    path: str | Path = DAILY_PROVIDER_STOCK_SNAPSHOT,
    snapshot_hour: int = 9,
) -> bool:
    generated_at = str(payload.get("generated_at", ""))
    generated = _parse_datetime(generated_at)
    if generated is None or generated.hour != snapshot_hour:
        return False

    snapshot_path = Path(path)
    previous_snapshot = load_daily_provider_stock_snapshot(snapshot_path)
    if _date_part(str(previous_snapshot.get("captured_at", ""))) == generated.date().isoformat():
        return False

    current_providers = _provider_counts_from_payload(payload)
    next_snapshot = {
        "captured_at": generated_at,
        "providers": current_providers,
        "previous_captured_at": str(previous_snapshot.get("captured_at", "")),
        "previous_providers": _clean_provider_counts(previous_snapshot.get("providers", {})),
    }
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(next_snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return True


def load_provider_stock_history(path: str | Path = PROVIDER_STOCK_HISTORY) -> dict[str, object]:
    history_path = Path(path)
    if not history_path.exists():
        return {"days": []}
    payload = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return {"days": []}
    days = payload.get("days", [])
    return {"days": days if isinstance(days, list) else []}


def maybe_update_provider_stock_history(
    payload: Mapping[str, object],
    path: str | Path = PROVIDER_STOCK_HISTORY,
    snapshot_hour: int = 9,
    max_days: int = 30,
) -> bool:
    generated_at = str(payload.get("generated_at", ""))
    generated = _parse_datetime(generated_at)
    if generated is None:
        return False

    history_path = Path(path)
    history = load_provider_stock_history(history_path)
    days = _history_days(history)
    date = generated.date().isoformat()
    counts = _provider_counts_from_payload(payload)
    check = {
        "captured_at": generated_at,
        "providers": counts,
    }
    existing_day = next((day for day in days if day.get("date") == date), None)
    if existing_day is None:
        day = {
            "date": date,
            "captured_at": generated_at,
            "providers": counts,
            "checks": [check],
        }
        days.append(day)
    else:
        checks = _history_checks(existing_day)
        checks = [item for item in checks if _check_hour(item) != generated.hour]
        checks.append(check)
        checks = _sort_checks(checks)
        existing_day["checks"] = checks
        if generated.hour == snapshot_hour or not existing_day.get("providers"):
            existing_day["captured_at"] = generated_at
            existing_day["providers"] = counts

    days = _trim_history_days(days, max_days)
    next_history = {"days": days}

    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(next_history, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return True


def write_public_provider_stock_history(
    history: Mapping[str, object],
    payload: Mapping[str, object],
    output_path: str | Path = PUBLIC_PROVIDER_STOCK_HISTORY,
    max_days: int = 30,
) -> None:
    path = Path(output_path)
    public_payload = {
        "generated_at": str(payload.get("generated_at", "")),
        "providers": _provider_metadata_from_payload(payload),
        "days": _trim_history_days(_history_days(history), max_days),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(public_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def collect_raw_items(
    sources: Mapping[str, SourceConfig] = SOURCES,
    updated_at: str | None = None,
    retry_attempts: int = 2,
) -> tuple[list[RawStockItem], dict[str, str]]:
    generated = updated_at or _now()
    items: list[RawStockItem] = []
    errors: dict[str, str] = {}

    for source in sources.values():
        try:
            items.extend(_fetch_source_items_with_retries(source, generated, retry_attempts))
        except Exception as exc:  # pragma: no cover - exact requests errors vary by provider.
            errors[source.id] = str(exc)

    return items, errors


def _fetch_source_items_with_retries(source: SourceConfig, updated_at: str, retry_attempts: int) -> list[RawStockItem]:
    attempts = max(1, retry_attempts)
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return _fetch_source_items(source, updated_at)
        except Exception as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return []


def build_grilon3_enrichments(
    raw_items: list[RawStockItem],
    catalog: Mapping[str, object] | None = None,
) -> dict[str, dict[str, str]]:
    from centraldefilamentos.connectors.grilon3_catalog import enrich_with_grilon3_catalog, fetch_grilon3_catalog

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
    from centraldefilamentos.connectors.grilon3_catalog import apply_grilon3_metadata, fetch_grilon3_catalog, fetch_grilon3_sitemap_catalog

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


def _payload_quality_metrics(payload: Mapping[str, object]) -> dict[str, object]:
    products = payload.get("products", [])
    product_count = len(products) if isinstance(products, list) else 0
    sources: dict[str, dict[str, object]] = {}
    total_stock_units = 0
    raw_sources = payload.get("sources", [])
    if isinstance(raw_sources, list):
        for source in raw_sources:
            if not isinstance(source, dict):
                continue
            source_id = str(source.get("id", ""))
            if not source_id:
                continue
            stats = source.get("stats", {})
            stats = stats if isinstance(stats, dict) else {}
            stock_units = _safe_int(stats.get("total_stock_units")) or 0
            source_product_count = _safe_int(stats.get("product_count")) or 0
            total_stock_units += stock_units
            sources[source_id] = {
                "name": str(source.get("name", source_id)),
                "status": str(source.get("status", "")),
                "total_stock_units": stock_units,
                "product_count": source_product_count,
            }
    return {
        "product_count": product_count,
        "total_stock_units": total_stock_units,
        "sources": sources,
    }


def _source_name(payload: Mapping[str, object], source_id: str) -> str:
    raw_sources = payload.get("sources", [])
    if isinstance(raw_sources, list):
        for source in raw_sources:
            if isinstance(source, dict) and source.get("id") == source_id:
                return str(source.get("name") or source_id)
    configured = SOURCES.get(source_id)
    return configured.name if configured is not None else source_id


def _last_good_sources(previous_payload: Mapping[str, object], source_errors: Mapping[str, str]) -> dict[str, dict[str, object]]:
    generated_at = str(previous_payload.get("generated_at", ""))
    raw_sources = previous_payload.get("sources", [])
    if not isinstance(raw_sources, list):
        return {}
    last_good: dict[str, dict[str, object]] = {}
    for source in raw_sources:
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id", ""))
        if source_id not in source_errors:
            continue
        stats = source.get("stats", {})
        stats = stats if isinstance(stats, dict) else {}
        last_good[source_id] = {
            "name": str(source.get("name") or source_id),
            "generated_at": generated_at,
            "total_stock_units": _safe_int(stats.get("total_stock_units")) or 0,
            "product_count": _safe_int(stats.get("product_count")) or 0,
        }
    return last_good


def _stock_payload_schema_errors(payload: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    if not str(payload.get("generated_at", "")):
        errors.append("generated_at is required")
    products = payload.get("products")
    sources = payload.get("sources")
    manufacturers = payload.get("manufacturers")
    if not isinstance(products, list):
        errors.append("products must be a list")
    if not isinstance(sources, list):
        errors.append("sources must be a list")
    if not isinstance(manufacturers, list):
        errors.append("manufacturers must be a list")
    if isinstance(sources, list):
        source_ids = {str(source.get("id", "")) for source in sources if isinstance(source, dict)}
        for expected_id in SOURCES:
            if expected_id not in source_ids:
                errors.append(f"missing source {expected_id}")
    if isinstance(products, list):
        for index, product in enumerate(products):
            if not isinstance(product, dict):
                errors.append(f"products[{index}] must be an object")
                continue
            if not product.get("id"):
                errors.append(f"products[{index}].id is required")
            offers = product.get("offers")
            if not isinstance(offers, list):
                errors.append(f"products[{index}].offers must be a list")
    return errors


def _drop_ratio(previous: int, current: int) -> float:
    if previous <= 0 or current >= previous:
        return 0.0
    return (previous - current) / previous


def _clean_error_message(error: object) -> str:
    message = " ".join(str(error).split())
    return message[:500]


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
    parser = argparse.ArgumentParser(description="Build public Central de Filamentos JSON data.")
    parser.add_argument("--output", default="public/data/stock.json")
    parser.add_argument("--daily-snapshot", default=str(DAILY_PROVIDER_STOCK_SNAPSHOT))
    parser.add_argument("--provider-history", default=str(PROVIDER_STOCK_HISTORY))
    parser.add_argument("--public-provider-history", default=str(PUBLIC_PROVIDER_STOCK_HISTORY))
    parser.add_argument("--business-log", default=str(PUBLIC_BUSINESS_LOG))
    parser.add_argument("--technical-log", default=str(PUBLIC_TECHNICAL_LOG))
    parser.add_argument("--snapshot-hour", type=int, default=9)
    args = parser.parse_args()

    raw_items, source_errors = collect_raw_items()
    enrichment_errors: dict[str, str] = {}
    catalog_products = {}
    enrichments: dict[str, dict[str, str]] = {}
    try:
        catalog_products = fetch_grilon3_catalog_products()
    except Exception as exc:
        enrichment_errors["grilon3_catalog"] = str(exc)
    try:
        enrichments.update(build_filamentos3d_enrichments(raw_items))
    except Exception as exc:
        enrichment_errors["filamentos3d_metadata"] = str(exc)
    try:
        enrichments.update(build_grilon3_enrichments(raw_items, catalog_products))
    except Exception as exc:
        enrichment_errors["grilon3_enrichment"] = str(exc)

    payload = build_payload(
        raw_items,
        enrichments=enrichments,
        source_errors=source_errors,
        catalog_products=catalog_products,
    )
    snapshot = load_daily_provider_stock_snapshot(args.daily_snapshot)
    apply_provider_stock_deltas(payload, snapshot)
    quality_report = evaluate_build_quality(payload, load_payload(args.output), source_errors, enrichment_errors)
    write_build_logs(quality_report, args.business_log, args.technical_log)
    if not quality_report["should_publish"]:
        print(str(quality_report["summary"]))
        return

    maybe_update_daily_provider_stock_snapshot(payload, args.daily_snapshot, args.snapshot_hour)
    maybe_update_provider_stock_history(payload, args.provider_history, args.snapshot_hour)
    history = load_provider_stock_history(args.provider_history)
    write_public_provider_stock_history(history, payload, args.public_provider_history)
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
        from centraldefilamentos.connectors.google_sheet import fetch_sheet_items

        return fetch_sheet_items(source, updated_at)
    if source.connector == "filamentos3d":
        from centraldefilamentos.connectors.filamentos3d import fetch_filamentos3d_items

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


def _provider_counts_for_delta(snapshot: Mapping[str, object], generated_at: str) -> dict[str, int]:
    captured_date = _date_part(str(snapshot.get("captured_at", "")))
    generated_date = _date_part(generated_at)
    if captured_date and generated_date and captured_date == generated_date:
        previous_counts = _clean_provider_counts(snapshot.get("previous_providers", {}))
        if previous_counts:
            return previous_counts
    return _clean_provider_counts(snapshot.get("providers", {}))


def _provider_counts_from_payload(payload: Mapping[str, object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in payload.get("sources", []):
        if not isinstance(source, dict):
            continue
        stats = source.get("stats")
        if not isinstance(stats, dict):
            continue
        total = _safe_int(stats.get("total_stock_units"))
        if total is None:
            continue
        counts[str(source.get("id", ""))] = total
    return counts


def _provider_metadata_from_payload(payload: Mapping[str, object]) -> list[dict[str, str]]:
    providers: list[dict[str, str]] = []
    for source in payload.get("sources", []):
        if not isinstance(source, dict):
            continue
        providers.append(
            {
                "id": str(source.get("id", "")),
                "name": str(source.get("name", "")),
                "zone": str(source.get("zone", "")),
            }
        )
    return providers


def _history_days(history: Mapping[str, object]) -> list[dict[str, object]]:
    days = history.get("days", [])
    if not isinstance(days, list):
        return []
    return [_normalize_history_day(day) for day in days if isinstance(day, dict) and day.get("date")]


def _trim_history_days(days: list[dict[str, object]], max_days: int) -> list[dict[str, object]]:
    sorted_days = sorted(days, key=lambda day: str(day.get("date", "")))
    return sorted_days[-max_days:]


def _normalize_history_day(day: Mapping[str, object]) -> dict[str, object]:
    providers = _clean_provider_counts(day.get("providers", {}))
    normalized = {
        "date": str(day.get("date", "")),
        "captured_at": str(day.get("captured_at", "")),
        "providers": providers,
        "checks": _history_checks(day),
    }
    if not normalized["checks"] and normalized["captured_at"] and providers:
        normalized["checks"] = [
            {
                "captured_at": normalized["captured_at"],
                "providers": providers,
            }
        ]
    return normalized


def _history_checks(day: Mapping[str, object]) -> list[dict[str, object]]:
    raw_checks = day.get("checks", [])
    if not isinstance(raw_checks, list):
        return []
    checks: list[dict[str, object]] = []
    for check in raw_checks:
        if not isinstance(check, dict) or not check.get("captured_at"):
            continue
        checks.append(
            {
                "captured_at": str(check.get("captured_at", "")),
                "providers": _clean_provider_counts(check.get("providers", {})),
            }
        )
    return _sort_checks(checks)


def _sort_checks(checks: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(checks, key=lambda check: str(check.get("captured_at", "")))


def _check_hour(check: Mapping[str, object]) -> int | None:
    parsed = _parse_datetime(str(check.get("captured_at", "")))
    return parsed.hour if parsed is not None else None


def _clean_provider_counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for source_id, total in value.items():
        parsed = _safe_int(total)
        if parsed is not None:
            counts[str(source_id)] = parsed
    return counts


def _safe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _date_part(value: str) -> str:
    parsed = _parse_datetime(value)
    return parsed.date().isoformat() if parsed is not None else ""


def _parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


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
