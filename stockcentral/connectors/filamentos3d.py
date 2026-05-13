from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup
import httpx

from stockcentral.models import RawStockItem
from stockcentral.providers import SourceConfig

NAME_HEADERS = {"producto", "nombre", "descripcion", "descripción", "detalle"}
STOCK_HEADERS = {"stock", "cantidad", "disponible", "unidades"}


def fetch_filamentos3d_items(
    source: SourceConfig,
    updated_at: str,
    timeout_seconds: int = 30,
) -> list[RawStockItem]:
    response = httpx.get(source.source_url, timeout=timeout_seconds, follow_redirects=True)
    response.raise_for_status()
    return parse_filamentos3d_html(response.text, source, updated_at)


def parse_filamentos3d_html(html_text: str, source: SourceConfig, updated_at: str) -> list[RawStockItem]:
    tables = _parse_tables(html_text)
    items: list[RawStockItem] = []

    for table in tables:
        columns = _table_columns(table)
        if columns["name"] is None:
            continue

        for row in table:
            cells = [_clean_text(cell) for cell in row]
            if not cells or _looks_like_header(cells):
                continue

            original_name = _cell(cells, columns["name"])
            if not original_name:
                continue

            stock_quantity = _parse_stock(_cell(cells, columns["stock"]))
            if _is_non_product_row(original_name, stock_quantity):
                continue
            items.append(
                RawStockItem(
                    source_id=source.id,
                    provider_name=source.name,
                    provider_zone=source.zone,
                    provider_url=source.homepage_url,
                    original_name=original_name,
                    stock_quantity=stock_quantity,
                    source_url=source.source_url,
                    brand_hint=source.brand_hint,
                    updated_at=updated_at,
                )
            )

    return items


def _parse_tables(html_text: str) -> list[list[list[str]]]:
    soup = _soup(html_text)
    tables: list[list[list[str]]] = []
    for table in soup.find_all("table"):
        rows: list[list[str]] = []
        for row in table.find_all("tr"):
            cells = [_clean_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
            if cells:
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def _soup(html_text: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html_text, "lxml")
    except Exception:
        return BeautifulSoup(html_text, "html.parser")


def _table_columns(table: list[list[str]]) -> dict[str, int | None]:
    first_row = table[0] if table else []
    headers = [_normalize_header(cell) for cell in first_row]
    name_column = _find_header(headers, NAME_HEADERS)
    stock_column = _find_header(headers, STOCK_HEADERS)

    if name_column is None and "grilon3" in headers:
        return {"name": headers.index("grilon3"), "stock": headers.index("grilon3") + 1}

    if name_column is None:
        return {"name": None, "stock": None}
    return {"name": name_column, "stock": stock_column}


def _find_header(headers: list[str], candidates: set[str]) -> int | None:
    for index, header in enumerate(headers):
        if header in candidates:
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
    if "consult" in lowered or "sin dato" in lowered:
        return None
    if "sin stock" in lowered:
        return 0

    match = re.search(r"\d+", cleaned)
    if match is None:
        return None
    return int(match.group(0))


def _cell(cells: list[str], index: int | None) -> str:
    if index is None or index >= len(cells):
        return ""
    return cells[index]


def _looks_like_header(cells: list[str]) -> bool:
    normalized = {_normalize_header(cell) for cell in cells}
    return bool(normalized & NAME_HEADERS) and bool(normalized & STOCK_HEADERS)


def _is_non_product_row(original_name: str, stock_quantity: int | None) -> bool:
    normalized = _normalize_header(original_name)
    if stock_quantity is not None:
        return False
    if normalized in {"grilon3", "3n3", "sampler grilon3"}:
        return True
    return any(
        marker in normalized
        for marker in [
            "submarca",
            "descripcion marcas",
            "kits lapiz",
            "kit lapiz",
            "maxifill bulk",
            "megafill box",
        ]
    )


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", _clean_text(value))
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.casefold()
