from __future__ import annotations

import re
from html.parser import HTMLParser

import requests

from stockcentral.models import RawStockItem
from stockcentral.providers import SourceConfig

NAME_HEADERS = {"producto", "nombre", "descripcion", "descripción", "detalle"}
STOCK_HEADERS = {"stock", "cantidad", "disponible", "unidades"}


def fetch_filamentos3d_items(
    source: SourceConfig,
    updated_at: str,
    timeout_seconds: int = 30,
) -> list[RawStockItem]:
    response = requests.get(source.source_url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_filamentos3d_html(response.text, source, updated_at)


def parse_filamentos3d_html(html_text: str, source: SourceConfig, updated_at: str) -> list[RawStockItem]:
    tables = _TableParser.parse(html_text)
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
            if stock_quantity is None and _normalize_header(original_name) in {"grilon3"}:
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


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._current_table: list[list[str]] | None = None
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    @classmethod
    def parse(cls, html_text: str) -> list[list[list[str]]]:
        parser = cls()
        parser.feed(html_text)
        return parser.tables

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._current_table = []
            return
        if self._current_table is not None and tag == "tr":
            self._current_row = []
            return
        if self._current_row is not None and tag in {"td", "th"}:
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_cell is not None and self._current_row is not None:
            self._current_row.append(_clean_text(" ".join(self._current_cell)))
            self._current_cell = None
            return
        if tag == "tr" and self._current_row is not None and self._current_table is not None:
            self._current_table.append(self._current_row)
            self._current_row = None
            return
        if tag == "table" and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._current_cell.append(data)


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


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_header(value: str) -> str:
    return _clean_text(value).casefold()
