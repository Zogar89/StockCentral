from __future__ import annotations

import csv
import io
import unicodedata

import requests

from stockcentral.models import RawStockItem
from stockcentral.providers import SourceConfig

NAME_COLUMNS = ["producto", "product", "nombre", "descripcion", "descripción", "detalle"]
STOCK_COLUMNS = ["stock", "stock real", "cantidad", "disponible", "unidades"]
BRAND_COLUMNS = ["marca", "brand", "fabricante"]
NON_PRODUCT_NAMES = {"grilon3", "3n3", "ean13"}
SECTION_ROW_PREFIXES = ("gama ",)


def build_csv_export_url(sheet_id: str, gid: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def fetch_sheet_items(
    source: SourceConfig,
    updated_at: str,
    timeout_seconds: int = 30,
) -> list[RawStockItem]:
    url = build_csv_export_url(source.sheet_id, source.gid)
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_sheet_csv(response.text, source, updated_at)


def parse_sheet_csv(csv_text: str, source: SourceConfig, updated_at: str) -> list[RawStockItem]:
    rows = list(csv.reader(io.StringIO(csv_text)))
    header_index, columns = _find_header_row(rows, source)
    items: list[RawStockItem] = []

    for row in rows[header_index + 1 :]:
        original_name = _cell(row, columns["name"])
        if not original_name:
            continue

        stock_quantity = _parse_stock(_cell(row, columns["stock"]) if columns["stock"] is not None else "")
        if _is_non_product_row(original_name, stock_quantity):
            continue

        brand_hint = source.brand_hint
        if columns["brand"] is not None:
            brand_hint = _cell(row, columns["brand"]) or source.brand_hint

        items.append(
            RawStockItem(
                source_id=source.id,
                provider_name=source.name,
                provider_zone=source.zone,
                provider_url=source.homepage_url,
                original_name=original_name,
                stock_quantity=stock_quantity,
                source_url=source.source_url,
                brand_hint=brand_hint,
                updated_at=updated_at,
            )
        )
    return items


def _find_header_row(rows: list[list[str]], source: SourceConfig) -> tuple[int, dict[str, int | None]]:
    for index, row in enumerate(rows):
        normalized = [_normalize_header(value) for value in row]
        name_column = _find_column(normalized, NAME_COLUMNS)
        stock_column = _find_column(normalized, STOCK_COLUMNS)
        brand_column = _find_column(normalized, BRAND_COLUMNS)
        if name_column is not None:
            return index, {"name": name_column, "stock": stock_column, "brand": brand_column}
    raise ValueError(f"No product column found for {source.id}")


def _find_column(normalized_headers: list[str], candidates: list[str]) -> int | None:
    normalized_candidates = {_normalize_header(candidate) for candidate in candidates}
    for index, normalized in enumerate(normalized_headers):
        if normalized in normalized_candidates:
            return index
    return None


def _parse_stock(value: str) -> int | None:
    cleaned = value.strip()
    if cleaned == "":
        return None
    if cleaned.startswith(("-", "−")):
        return None

    lowered = cleaned.lower()
    if lowered in {"n/d", "#n/d", "n/a", "#n/a", "na", "nan"}:
        return None
    if "sin" in lowered or lowered == "no":
        return 0

    digits = "".join(char for char in cleaned if char.isdigit())
    if digits == "":
        return None
    return int(digits)


def _cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def _is_non_product_row(original_name: str, stock_quantity: int | None) -> bool:
    normalized = _normalize_header(original_name)
    return stock_quantity is None and (
        normalized in NON_PRODUCT_NAMES
        or any(normalized.startswith(prefix) for prefix in SECTION_ROW_PREFIXES)
    )


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(without_marks.strip().lower().split())
