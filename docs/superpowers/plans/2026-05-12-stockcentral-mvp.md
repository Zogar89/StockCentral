# StockCentral MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first public StockCentral MVP: a static GitHub Pages catalog fed by Python ingestion and normalization jobs.

**Architecture:** Python downloads provider stock sources, normalizes products, enriches Grilon3 products with official manufacturer links/images, and writes `public/data/stock.json`. The frontend is a static HTML/CSS/JS app that reads that JSON and renders a minimalist Apple-inspired catalog with filters.

**Tech Stack:** Python 3.12, requests, BeautifulSoup, pytest, plain HTML/CSS/JavaScript, GitHub Actions, GitHub Pages.

---

## File Structure

- Create `pyproject.toml`: Python package metadata, dependencies, pytest config.
- Create `README.md`: local setup, data build, test and deploy notes.
- Create `stockcentral/__init__.py`: package marker and version.
- Create `stockcentral/models.py`: dataclasses and JSON serialization helpers.
- Create `stockcentral/providers.py`: source and manufacturer configuration.
- Create `stockcentral/normalize.py`: conservative normalization logic.
- Create `stockcentral/connectors/__init__.py`: connector exports.
- Create `stockcentral/connectors/google_sheet.py`: Google Sheets CSV export and parser.
- Create `stockcentral/connectors/filamentos3d.py`: Filamentos3D HTML parser.
- Create `stockcentral/connectors/grilon3_catalog.py`: official Grilon3 catalog parser/enricher.
- Create `stockcentral/build_data.py`: orchestration entrypoint that writes `public/data/stock.json`.
- Create `public/index.html`: static app shell.
- Create `public/styles.css`: minimalist visual system and responsive layout.
- Create `public/app.js`: data loading, filters, grouping render, state updates.
- Create `public/data/stock.json`: small fixture dataset for local UI before live ingestion runs.
- Create `.github/workflows/ci.yml`: run tests on push and pull requests.
- Create `.github/workflows/pages.yml`: scheduled ingestion and GitHub Pages deploy.
- Create `tests/fixtures/google_sheet_stock.csv`: representative Sheet data.
- Create `tests/fixtures/filamentos3d_stock.html`: representative Filamentos3D table.
- Create `tests/fixtures/grilon3_catalog.html`: representative Grilon3 catalog cards.
- Create `tests/test_models.py`: model serialization tests.
- Create `tests/test_normalize.py`: normalization tests.
- Create `tests/test_google_sheet.py`: Google Sheets connector tests.
- Create `tests/test_filamentos3d.py`: Filamentos3D parser tests.
- Create `tests/test_grilon3_catalog.py`: Grilon3 enrichment tests.
- Create `tests/test_build_data.py`: final JSON build tests.
- Create `tests/test_frontend_assets.py`: static asset smoke tests.

---

### Task 1: Python Project Scaffold And Data Models

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `stockcentral/__init__.py`
- Create: `stockcentral/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Create the failing model tests**

Create `tests/test_models.py`:

```python
from stockcentral.models import Offer, ProductGroup, SourceStatus


def test_product_group_serializes_for_public_json():
    offer = Offer(
        source_id="filamentos3d",
        provider_name="Filamentos3D",
        provider_zone="Zona Sur",
        provider_url="https://filamentos3d.com.ar/grilon3.php",
        original_name="GRILON3 PLA Negro 1kg",
        stock_quantity=14,
        stock_status="in_stock",
        source_url="https://filamentos3d.com.ar/grilon3.php",
        updated_at="2026-05-12T12:00:00-03:00",
    )

    product = ProductGroup(
        id="pla-negro-175-1000-grilon3",
        material="PLA",
        variant="",
        color="Negro",
        diameter_mm=1.75,
        weight_g=1000,
        brand="Grilon3",
        manufacturer_name="Grilon3",
        manufacturer_product_url="https://grilon3.com.ar/producto/pla-negro/",
        image_url="https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg",
        image_source="manufacturer",
        display_name="PLA Negro Grilon3 1 kg",
        offers=[offer],
    )

    payload = product.to_dict()

    assert payload["id"] == "pla-negro-175-1000-grilon3"
    assert payload["material"] == "PLA"
    assert payload["offers"][0]["provider_zone"] == "Zona Sur"
    assert payload["offers"][0]["stock_status"] == "in_stock"
    assert payload["manufacturer_product_url"].startswith("https://grilon3.com.ar/")
    assert payload["image_source"] == "manufacturer"


def test_source_status_serializes_error_message():
    source = SourceStatus(
        id="grupo_senz",
        name="Grupo Senz",
        zone="Zona Oeste",
        homepage_url="https://docs.google.com/spreadsheets/d/14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM",
        source_url="https://docs.google.com/spreadsheets/d/14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM",
        last_success_at="2026-05-12T12:00:00-03:00",
        last_attempt_at="2026-05-12T15:00:00-03:00",
        status="error",
        error_message="CSV export returned 403",
    )

    payload = source.to_dict()

    assert payload["status"] == "error"
    assert payload["error_message"] == "CSV export returned 403"
```

- [ ] **Step 2: Run the tests to verify the package is missing**

Run:

```bash
pytest tests/test_models.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'stockcentral'`.

- [ ] **Step 3: Create project metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "stockcentral"
version = "0.1.0"
description = "Centralizador estatico de stock de filamentos 3D para AMBA"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "beautifulsoup4>=4.12.3",
  "requests>=2.32.3",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Create `README.md`:

````markdown
# StockCentral

StockCentral centraliza stock online de proveedores de filamento 3D del AMBA.

## Desarrollo local

```bash
python -m pip install -e ".[dev]"
pytest
python -m stockcentral.build_data --output public/data/stock.json
python -m http.server 8000 -d public
```

Abrir `http://localhost:8000`.

## Datos

El frontend lee `public/data/stock.json`. En produccion, GitHub Actions genera ese archivo y publica `public/` en GitHub Pages.
````

Create `stockcentral/__init__.py`:

```python
__version__ = "0.1.0"
```

- [ ] **Step 4: Create the dataclasses and serializers**

Create `stockcentral/models.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

StockStatus = Literal["in_stock", "out_of_stock", "unknown"]
SourceRunStatus = Literal["ok", "error"]
ImageSource = Literal["manufacturer", "provider", ""]


@dataclass(frozen=True)
class RawStockItem:
    source_id: str
    provider_name: str
    provider_zone: str
    provider_url: str
    original_name: str
    stock_quantity: int | None
    source_url: str
    brand_hint: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class NormalizedFields:
    material: str
    variant: str
    color: str
    diameter_mm: float | None
    weight_g: int | None
    brand: str
    manufacturer_name: str


@dataclass(frozen=True)
class Offer:
    source_id: str
    provider_name: str
    provider_zone: str
    provider_url: str
    original_name: str
    stock_quantity: int | None
    stock_status: StockStatus
    source_url: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProductGroup:
    id: str
    material: str
    variant: str
    color: str
    diameter_mm: float | None
    weight_g: int | None
    brand: str
    manufacturer_name: str
    manufacturer_product_url: str
    image_url: str
    image_source: ImageSource
    display_name: str
    offers: list[Offer]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["offers"] = [offer.to_dict() for offer in self.offers]
        return payload


@dataclass(frozen=True)
class SourceStatus:
    id: str
    name: str
    zone: str
    homepage_url: str
    source_url: str
    last_success_at: str
    last_attempt_at: str
    status: SourceRunStatus
    error_message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ManufacturerInfo:
    id: str
    name: str
    official_site_url: str
    products_url: str
    has_official_product_pages: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
```

- [ ] **Step 5: Run the model tests**

Run:

```bash
pytest tests/test_models.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit the scaffold**

Run:

```bash
git add pyproject.toml README.md stockcentral/__init__.py stockcentral/models.py tests/test_models.py
git commit -m "chore: scaffold python models"
```

---

### Task 2: Provider And Manufacturer Configuration

**Files:**
- Create: `stockcentral/providers.py`
- Test: `tests/test_providers.py`

- [ ] **Step 1: Write configuration tests**

Create `tests/test_providers.py`:

```python
from stockcentral.providers import MANUFACTURERS, SOURCES


def test_sources_cover_initial_amba_providers():
    assert set(SOURCES) == {"filamentos3d", "grupo_senz", "mundoinsumos"}
    assert SOURCES["filamentos3d"].zone == "Zona Sur"
    assert SOURCES["grupo_senz"].zone == "Zona Oeste"
    assert SOURCES["mundoinsumos"].zone == "Zona Norte"


def test_google_sheet_sources_include_sheet_ids_and_gids():
    assert SOURCES["grupo_senz"].sheet_id == "14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM"
    assert SOURCES["grupo_senz"].gid == "0"
    assert SOURCES["mundoinsumos"].sheet_id == "1r-nKy4tRRtZ-5xwgxAcia8REDVW0Dv0h"
    assert SOURCES["mundoinsumos"].gid == "1981641819"


def test_manufacturer_configuration_keeps_3n3_without_official_site():
    assert MANUFACTURERS["grilon3"].products_url == "https://grilon3.com.ar/productos/"
    assert MANUFACTURERS["grilon3"].has_official_product_pages is True
    assert MANUFACTURERS["3n3"].official_site_url == ""
    assert MANUFACTURERS["3n3"].has_official_product_pages is False
```

- [ ] **Step 2: Run tests to verify the config module is missing**

Run:

```bash
pytest tests/test_providers.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `stockcentral.providers`.

- [ ] **Step 3: Implement source configuration**

Create `stockcentral/providers.py`:

```python
from __future__ import annotations

from dataclasses import dataclass

from stockcentral.models import ManufacturerInfo


@dataclass(frozen=True)
class SourceConfig:
    id: str
    name: str
    zone: str
    homepage_url: str
    source_url: str
    connector: str
    sheet_id: str = ""
    gid: str = "0"
    brand_hint: str = ""


SOURCES: dict[str, SourceConfig] = {
    "filamentos3d": SourceConfig(
        id="filamentos3d",
        name="Filamentos3D",
        zone="Zona Sur",
        homepage_url="https://filamentos3d.com.ar/",
        source_url="https://filamentos3d.com.ar/grilon3.php",
        connector="filamentos3d",
        brand_hint="Grilon3",
    ),
    "grupo_senz": SourceConfig(
        id="grupo_senz",
        name="Grupo Senz",
        zone="Zona Oeste",
        homepage_url="https://docs.google.com/spreadsheets/d/14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM",
        source_url="https://docs.google.com/spreadsheets/d/14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM",
        connector="google_sheet",
        sheet_id="14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM",
        gid="0",
    ),
    "mundoinsumos": SourceConfig(
        id="mundoinsumos",
        name="MundoInsumos",
        zone="Zona Norte",
        homepage_url="https://www.mundoinsumos.com.ar/",
        source_url="https://docs.google.com/spreadsheets/d/1r-nKy4tRRtZ-5xwgxAcia8REDVW0Dv0h/edit?gid=1981641819#gid=1981641819",
        connector="google_sheet",
        sheet_id="1r-nKy4tRRtZ-5xwgxAcia8REDVW0Dv0h",
        gid="1981641819",
    ),
}

MANUFACTURERS: dict[str, ManufacturerInfo] = {
    "grilon3": ManufacturerInfo(
        id="grilon3",
        name="Grilon3",
        official_site_url="https://grilon3.com.ar/",
        products_url="https://grilon3.com.ar/productos/",
        has_official_product_pages=True,
    ),
    "3n3": ManufacturerInfo(
        id="3n3",
        name="3N3",
        official_site_url="",
        products_url="",
        has_official_product_pages=False,
    ),
}
```

- [ ] **Step 4: Run provider tests**

Run:

```bash
pytest tests/test_providers.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit provider configuration**

Run:

```bash
git add stockcentral/providers.py tests/test_providers.py
git commit -m "feat: add provider configuration"
```

---

### Task 3: Conservative Product Normalization

**Files:**
- Create: `stockcentral/normalize.py`
- Test: `tests/test_normalize.py`

- [ ] **Step 1: Write normalization tests**

Create `tests/test_normalize.py`:

```python
from stockcentral.models import RawStockItem
from stockcentral.normalize import build_product_id, normalize_record


def raw(name: str, source_id: str = "filamentos3d", brand_hint: str = "") -> RawStockItem:
    return RawStockItem(
        source_id=source_id,
        provider_name="Proveedor",
        provider_zone="Zona Sur",
        provider_url="https://example.com",
        original_name=name,
        stock_quantity=1,
        source_url="https://example.com/source",
        brand_hint=brand_hint,
        updated_at="2026-05-12T12:00:00-03:00",
    )


def test_normalizes_grilon3_pla_negro():
    fields = normalize_record(raw("GRILON3 PLA Negro 1.75mm 1kg", brand_hint="Grilon3"))

    assert fields.material == "PLA"
    assert fields.variant == ""
    assert fields.color == "Negro"
    assert fields.diameter_mm == 1.75
    assert fields.weight_g == 1000
    assert fields.brand == "Grilon3"
    assert fields.manufacturer_name == "Grilon3"


def test_normalizes_3n3_pla_plus_rojo():
    fields = normalize_record(raw("3N3 PLA+ Rojo 1 kg 1.75 mm", source_id="grupo_senz"))

    assert fields.material == "PLA"
    assert fields.variant == "PLA+"
    assert fields.color == "Rojo"
    assert fields.diameter_mm == 1.75
    assert fields.weight_g == 1000
    assert fields.brand == "3N3"
    assert fields.manufacturer_name == "3N3"


def test_keeps_other_weights_separate():
    fields = normalize_record(raw("PETG Transparente 750g 1.75mm"))

    assert fields.material == "PETG"
    assert fields.color == "Transparente"
    assert fields.weight_g == 750


def test_product_id_includes_brand_and_format():
    fields = normalize_record(raw("PLA Silk Azul 1kg 1.75mm Grilon3"))

    assert build_product_id(fields) == "pla-silk-azul-175-1000-grilon3"
```

- [ ] **Step 2: Run tests to verify normalization is missing**

Run:

```bash
pytest tests/test_normalize.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `stockcentral.normalize`.

- [ ] **Step 3: Implement normalization**

Create `stockcentral/normalize.py`:

```python
from __future__ import annotations

import re
import unicodedata

from stockcentral.models import NormalizedFields, RawStockItem

MATERIALS = ["PLA", "PETG", "ABS", "TPU", "HIPS", "NYLON", "PA"]
VARIANTS = {
    "PLA+": "PLA+",
    "PLUS": "PLA+",
    "SILK": "Silk",
    "MATE": "Mate",
    "BOUTIQUE": "Boutique",
    "ASTRA": "Astra",
    "PRO": "Pro",
    "FLEX": "Flex",
    "WOOD": "Wood",
    "GALAXY": "Galaxy",
}
COLORS = {
    "NEGRO": "Negro",
    "BLANCO": "Blanco",
    "ROJO": "Rojo",
    "AZUL": "Azul",
    "VERDE": "Verde",
    "AMARILLO": "Amarillo",
    "NARANJA": "Naranja",
    "VIOLETA": "Violeta",
    "GRIS": "Gris",
    "ROSA": "Rosa",
    "MARRON": "Marron",
    "NATURAL": "Natural",
    "TRANSPARENTE": "Transparente",
    "CRISTAL": "Transparente",
}
BRANDS = {
    "GRILON3": "Grilon3",
    "GRILON 3": "Grilon3",
    "3N3": "3N3",
}


def normalize_record(item: RawStockItem) -> NormalizedFields:
    text = _fold(f"{item.original_name} {item.brand_hint}")
    material = _detect_material(text)
    variant = _detect_variant(text)
    color = _detect_color(text)
    diameter_mm = _detect_diameter(text)
    weight_g = _detect_weight(text)
    brand = _detect_brand(text, item.brand_hint)

    return NormalizedFields(
        material=material,
        variant=variant,
        color=color,
        diameter_mm=diameter_mm,
        weight_g=weight_g,
        brand=brand,
        manufacturer_name=brand,
    )


def build_product_id(fields: NormalizedFields) -> str:
    diameter = "unknown"
    if fields.diameter_mm is not None:
        diameter = str(fields.diameter_mm).replace(".", "")
    weight = str(fields.weight_g) if fields.weight_g is not None else "unknown"
    parts = [
        fields.material,
        fields.variant,
        fields.color,
        diameter,
        weight,
        fields.brand,
    ]
    return "-".join(_slug(part) for part in parts if part)


def build_display_name(fields: NormalizedFields) -> str:
    pieces = [fields.material]
    if fields.variant and fields.variant != fields.material:
        pieces.append(fields.variant)
    if fields.color:
        pieces.append(fields.color)
    if fields.brand:
        pieces.append(fields.brand)
    if fields.weight_g:
        pieces.append(f"{fields.weight_g / 1000:g} kg")
    if fields.diameter_mm:
        pieces.append(f"{fields.diameter_mm:g} mm")
    return " ".join(pieces)


def _detect_material(text: str) -> str:
    for material in MATERIALS:
        if re.search(rf"\b{re.escape(material)}\b", text):
            return "Nylon" if material in {"NYLON", "PA"} else material
    return "Sin clasificar"


def _detect_variant(text: str) -> str:
    for token, value in VARIANTS.items():
        if re.search(rf"\b{re.escape(token)}\b", text):
            return value
    return ""


def _detect_color(text: str) -> str:
    for token, value in COLORS.items():
        if re.search(rf"\b{re.escape(token)}\b", text):
            return value
    return "Sin color"


def _detect_diameter(text: str) -> float | None:
    if re.search(r"1[,.]?75\s*MM", text):
        return 1.75
    if re.search(r"\b175\s*MM\b", text):
        return 1.75
    if re.search(r"2[,.]?85\s*MM", text):
        return 2.85
    return None


def _detect_weight(text: str) -> int | None:
    kg_match = re.search(r"(\d+(?:[,.]\d+)?)\s*KG\b", text)
    if kg_match:
        return int(float(kg_match.group(1).replace(",", ".")) * 1000)

    g_match = re.search(r"(\d{3,5})\s*G\b", text)
    if g_match:
        return int(g_match.group(1))

    return None


def _detect_brand(text: str, brand_hint: str) -> str:
    folded_hint = _fold(brand_hint)
    for token, value in BRANDS.items():
        if token in text or token in folded_hint:
            return value
    return brand_hint.strip() if brand_hint.strip() else ""


def _slug(value: str) -> str:
    folded = _fold(value).lower()
    folded = folded.replace("+", "plus")
    folded = re.sub(r"[^a-z0-9]+", "-", folded)
    return folded.strip("-")


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.upper()
```

- [ ] **Step 4: Run normalization tests**

Run:

```bash
pytest tests/test_normalize.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit normalization**

Run:

```bash
git add stockcentral/normalize.py tests/test_normalize.py
git commit -m "feat: add product normalization"
```

---

### Task 4: Google Sheets Connector

**Files:**
- Create: `stockcentral/connectors/__init__.py`
- Create: `stockcentral/connectors/google_sheet.py`
- Create: `tests/fixtures/google_sheet_stock.csv`
- Test: `tests/test_google_sheet.py`

- [ ] **Step 1: Write Google Sheets fixture**

Create `tests/fixtures/google_sheet_stock.csv`:

```csv
Producto,Stock,Marca
PLA+ Rojo 1kg 1.75mm,12,3N3
PETG Transparente 750g 1.75mm,0,3N3
TPU Flex Negro 500g 1.75mm,,3N3
```

- [ ] **Step 2: Write connector tests**

Create `tests/test_google_sheet.py`:

```python
from pathlib import Path

from stockcentral.connectors.google_sheet import build_csv_export_url, parse_sheet_csv
from stockcentral.providers import SOURCES


def test_build_csv_export_url_uses_sheet_id_and_gid():
    url = build_csv_export_url("abc123", "1981641819")

    assert url == "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=1981641819"


def test_parse_sheet_csv_detects_name_stock_and_brand():
    csv_text = Path("tests/fixtures/google_sheet_stock.csv").read_text(encoding="utf-8")
    source = SOURCES["grupo_senz"]

    items = parse_sheet_csv(csv_text, source, updated_at="2026-05-12T12:00:00-03:00")

    assert len(items) == 3
    assert items[0].original_name == "PLA+ Rojo 1kg 1.75mm"
    assert items[0].stock_quantity == 12
    assert items[0].brand_hint == "3N3"
    assert items[1].stock_quantity == 0
    assert items[2].stock_quantity is None
```

- [ ] **Step 3: Run tests to verify connector is missing**

Run:

```bash
pytest tests/test_google_sheet.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 4: Implement Google Sheets connector**

Create `stockcentral/connectors/__init__.py`:

```python
"""Provider connectors for StockCentral."""
```

Create `stockcentral/connectors/google_sheet.py`:

```python
from __future__ import annotations

import csv
import io

import requests

from stockcentral.models import RawStockItem
from stockcentral.providers import SourceConfig

NAME_COLUMNS = ["producto", "product", "nombre", "descripcion", "descripción", "detalle"]
STOCK_COLUMNS = ["stock", "cantidad", "disponible", "unidades"]
BRAND_COLUMNS = ["marca", "brand", "fabricante"]


def build_csv_export_url(sheet_id: str, gid: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def fetch_sheet_items(source: SourceConfig, updated_at: str, timeout_seconds: int = 30) -> list[RawStockItem]:
    url = build_csv_export_url(source.sheet_id, source.gid)
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_sheet_csv(response.text, source, updated_at)


def parse_sheet_csv(csv_text: str, source: SourceConfig, updated_at: str) -> list[RawStockItem]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        return []

    headers = {header: _normalize_header(header) for header in reader.fieldnames}
    name_column = _find_column(headers, NAME_COLUMNS)
    stock_column = _find_column(headers, STOCK_COLUMNS)
    brand_column = _find_column(headers, BRAND_COLUMNS)

    if name_column is None:
        raise ValueError(f"No product column found for {source.id}")

    items: list[RawStockItem] = []
    for row in reader:
        original_name = (row.get(name_column) or "").strip()
        if not original_name:
            continue
        stock_quantity = _parse_stock(row.get(stock_column, "") if stock_column else "")
        brand_hint = (row.get(brand_column) or source.brand_hint).strip() if brand_column else source.brand_hint
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


def _find_column(headers: dict[str, str], candidates: list[str]) -> str | None:
    normalized_candidates = {_normalize_header(candidate) for candidate in candidates}
    for original, normalized in headers.items():
        if normalized in normalized_candidates:
            return original
    return None


def _parse_stock(value: str) -> int | None:
    cleaned = value.strip()
    if cleaned == "":
        return None
    digits = "".join(char for char in cleaned if char.isdigit())
    if digits == "":
        lowered = cleaned.lower()
        if "sin" in lowered or "no" in lowered:
            return 0
        return None
    return int(digits)


def _normalize_header(value: str) -> str:
    return value.strip().lower()
```

- [ ] **Step 5: Run Google Sheets tests**

Run:

```bash
pytest tests/test_google_sheet.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Google Sheets connector**

Run:

```bash
git add stockcentral/connectors/__init__.py stockcentral/connectors/google_sheet.py tests/fixtures/google_sheet_stock.csv tests/test_google_sheet.py
git commit -m "feat: add google sheets stock connector"
```

---

### Task 5: Filamentos3D HTML Connector

**Files:**
- Create: `stockcentral/connectors/filamentos3d.py`
- Create: `tests/fixtures/filamentos3d_stock.html`
- Test: `tests/test_filamentos3d.py`

- [ ] **Step 1: Write representative Filamentos3D fixture**

Create `tests/fixtures/filamentos3d_stock.html`:

```html
<!doctype html>
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>Codigo</th>
          <th>Producto</th>
          <th>Stock</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>02_G1_NEGRO</td>
          <td>GRILON3 PLA Negro 1kg 1.75mm</td>
          <td>24</td>
        </tr>
        <tr>
          <td>03_G1_BLANCO</td>
          <td>GRILON3 PETG Blanco 1kg 1.75mm</td>
          <td>0</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
```

- [ ] **Step 2: Write parser tests**

Create `tests/test_filamentos3d.py`:

```python
from pathlib import Path

from stockcentral.connectors.filamentos3d import parse_filamentos3d_html
from stockcentral.providers import SOURCES


def test_parse_filamentos3d_table_rows():
    html = Path("tests/fixtures/filamentos3d_stock.html").read_text(encoding="utf-8")
    source = SOURCES["filamentos3d"]

    items = parse_filamentos3d_html(html, source, updated_at="2026-05-12T12:00:00-03:00")

    assert len(items) == 2
    assert items[0].original_name == "GRILON3 PLA Negro 1kg 1.75mm"
    assert items[0].stock_quantity == 24
    assert items[0].brand_hint == "Grilon3"
    assert items[1].stock_quantity == 0
```

- [ ] **Step 3: Run tests to verify connector is missing**

Run:

```bash
pytest tests/test_filamentos3d.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 4: Implement the HTML parser**

Create `stockcentral/connectors/filamentos3d.py`:

```python
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from stockcentral.models import RawStockItem
from stockcentral.providers import SourceConfig


def fetch_filamentos3d_items(source: SourceConfig, updated_at: str, timeout_seconds: int = 30) -> list[RawStockItem]:
    response = requests.get(source.source_url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_filamentos3d_html(response.text, source, updated_at)


def parse_filamentos3d_html(html: str, source: SourceConfig, updated_at: str) -> list[RawStockItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[RawStockItem] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [_cell_text(cell).lower() for cell in rows[0].find_all(["th", "td"])]
        product_index = _find_index(headers, ["producto", "descripcion", "descripción", "detalle"])
        stock_index = _find_index(headers, ["stock", "cantidad", "disponible"])

        if product_index is None or stock_index is None:
            continue

        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) <= max(product_index, stock_index):
                continue
            original_name = _cell_text(cells[product_index])
            if not original_name:
                continue
            items.append(
                RawStockItem(
                    source_id=source.id,
                    provider_name=source.name,
                    provider_zone=source.zone,
                    provider_url=source.homepage_url,
                    original_name=original_name,
                    stock_quantity=_parse_stock(_cell_text(cells[stock_index])),
                    source_url=source.source_url,
                    brand_hint=source.brand_hint,
                    updated_at=updated_at,
                )
            )

    return items


def _find_index(headers: list[str], candidates: list[str]) -> int | None:
    for index, header in enumerate(headers):
        if header in candidates:
            return index
    return None


def _parse_stock(value: str) -> int | None:
    digits = "".join(char for char in value if char.isdigit())
    if digits:
        return int(digits)
    lowered = value.lower()
    if "sin" in lowered or "no" in lowered:
        return 0
    return None


def _cell_text(cell) -> str:
    return " ".join(cell.get_text(" ", strip=True).split())
```

- [ ] **Step 5: Run Filamentos3D tests**

Run:

```bash
pytest tests/test_filamentos3d.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Filamentos3D connector**

Run:

```bash
git add stockcentral/connectors/filamentos3d.py tests/fixtures/filamentos3d_stock.html tests/test_filamentos3d.py
git commit -m "feat: add filamentos3d stock connector"
```

---

### Task 6: Grilon3 Manufacturer Catalog Enrichment

**Files:**
- Create: `stockcentral/connectors/grilon3_catalog.py`
- Create: `tests/fixtures/grilon3_catalog.html`
- Test: `tests/test_grilon3_catalog.py`

- [ ] **Step 1: Write Grilon3 catalog fixture**

Create `tests/fixtures/grilon3_catalog.html`:

```html
<!doctype html>
<html>
  <body>
    <article class="product">
      <a href="https://grilon3.com.ar/producto/pla-negro/">
        <img src="https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg" alt="PLA Negro">
        <h2>PLA Negro</h2>
      </a>
    </article>
    <article class="product">
      <a href="https://grilon3.com.ar/producto/petg-blanco/">
        <img src="https://grilon3.com.ar/wp-content/uploads/petg-blanco.jpg" alt="PETG Blanco">
        <h2>PETG Blanco</h2>
      </a>
    </article>
  </body>
</html>
```

- [ ] **Step 2: Write enrichment tests**

Create `tests/test_grilon3_catalog.py`:

```python
from pathlib import Path

from stockcentral.connectors.grilon3_catalog import enrich_grilon3_product, parse_grilon3_catalog
from stockcentral.models import NormalizedFields


def test_parse_grilon3_catalog_products():
    html = Path("tests/fixtures/grilon3_catalog.html").read_text(encoding="utf-8")

    products = parse_grilon3_catalog(html)

    assert products["pla-negro"].product_url == "https://grilon3.com.ar/producto/pla-negro/"
    assert products["pla-negro"].image_url == "https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg"


def test_enriches_matching_grilon3_product():
    html = Path("tests/fixtures/grilon3_catalog.html").read_text(encoding="utf-8")
    catalog = parse_grilon3_catalog(html)
    fields = NormalizedFields(
        material="PLA",
        variant="",
        color="Negro",
        diameter_mm=1.75,
        weight_g=1000,
        brand="Grilon3",
        manufacturer_name="Grilon3",
    )

    enriched = enrich_grilon3_product(fields, catalog)

    assert enriched["manufacturer_product_url"] == "https://grilon3.com.ar/producto/pla-negro/"
    assert enriched["image_source"] == "manufacturer"


def test_does_not_enrich_3n3_product():
    html = Path("tests/fixtures/grilon3_catalog.html").read_text(encoding="utf-8")
    catalog = parse_grilon3_catalog(html)
    fields = NormalizedFields(
        material="PLA",
        variant="",
        color="Rojo",
        diameter_mm=1.75,
        weight_g=1000,
        brand="3N3",
        manufacturer_name="3N3",
    )

    enriched = enrich_grilon3_product(fields, catalog)

    assert enriched["manufacturer_product_url"] == ""
    assert enriched["image_url"] == ""
    assert enriched["image_source"] == ""
```

- [ ] **Step 3: Run tests to verify enrichment is missing**

Run:

```bash
pytest tests/test_grilon3_catalog.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 4: Implement Grilon3 catalog parser and enricher**

Create `stockcentral/connectors/grilon3_catalog.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

import requests
from bs4 import BeautifulSoup

from stockcentral.models import NormalizedFields


@dataclass(frozen=True)
class CatalogProduct:
    key: str
    title: str
    product_url: str
    image_url: str


def fetch_grilon3_catalog(products_url: str, timeout_seconds: int = 30) -> dict[str, CatalogProduct]:
    response = requests.get(products_url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_grilon3_catalog(response.text)


def parse_grilon3_catalog(html: str) -> dict[str, CatalogProduct]:
    soup = BeautifulSoup(html, "html.parser")
    products: dict[str, CatalogProduct] = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/producto/" not in href:
            continue
        title = _extract_title(link)
        if not title:
            continue
        image = link.find("img")
        image_url = image.get("src", "") if image else ""
        key = _catalog_key(title)
        products[key] = CatalogProduct(
            key=key,
            title=title,
            product_url=href,
            image_url=image_url,
        )

    return products


def enrich_grilon3_product(fields: NormalizedFields, catalog: dict[str, CatalogProduct]) -> dict[str, str]:
    if fields.brand != "Grilon3":
        return {"manufacturer_product_url": "", "image_url": "", "image_source": ""}

    key = _fields_key(fields)
    product = catalog.get(key)
    if product is None:
        return {"manufacturer_product_url": "", "image_url": "", "image_source": ""}

    return {
        "manufacturer_product_url": product.product_url,
        "image_url": product.image_url,
        "image_source": "manufacturer" if product.image_url else "",
    }


def _extract_title(link) -> str:
    heading = link.find(["h1", "h2", "h3"])
    if heading:
        return " ".join(heading.get_text(" ", strip=True).split())
    image = link.find("img")
    if image and image.get("alt"):
        return " ".join(image["alt"].split())
    return " ".join(link.get_text(" ", strip=True).split())


def _fields_key(fields: NormalizedFields) -> str:
    parts = [fields.material, fields.variant, fields.color]
    return _catalog_key(" ".join(part for part in parts if part))


def _catalog_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    folded = without_marks.lower().replace("+", "plus")
    return re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
```

- [ ] **Step 5: Run Grilon3 enrichment tests**

Run:

```bash
pytest tests/test_grilon3_catalog.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit Grilon3 enrichment**

Run:

```bash
git add stockcentral/connectors/grilon3_catalog.py tests/fixtures/grilon3_catalog.html tests/test_grilon3_catalog.py
git commit -m "feat: enrich grilon3 products"
```

---

### Task 7: Build Public Stock JSON

**Files:**
- Create: `stockcentral/build_data.py`
- Create: `tests/test_build_data.py`
- Create: `public/data/stock.json`

- [ ] **Step 1: Write build tests**

Create `tests/test_build_data.py`:

```python
import json
from pathlib import Path

from stockcentral.build_data import build_payload, write_payload
from stockcentral.models import RawStockItem


def test_build_payload_groups_products_and_preserves_out_of_stock():
    raw_items = [
        RawStockItem(
            source_id="filamentos3d",
            provider_name="Filamentos3D",
            provider_zone="Zona Sur",
            provider_url="https://filamentos3d.com.ar/",
            original_name="GRILON3 PLA Negro 1kg 1.75mm",
            stock_quantity=4,
            source_url="https://filamentos3d.com.ar/grilon3.php",
            brand_hint="Grilon3",
            updated_at="2026-05-12T12:00:00-03:00",
        ),
        RawStockItem(
            source_id="mundoinsumos",
            provider_name="MundoInsumos",
            provider_zone="Zona Norte",
            provider_url="https://www.mundoinsumos.com.ar/",
            original_name="GRILON3 PLA Negro 1kg 1.75mm",
            stock_quantity=0,
            source_url="https://docs.google.com/spreadsheets/d/1r-nKy4tRRtZ-5xwgxAcia8REDVW0Dv0h",
            brand_hint="Grilon3",
            updated_at="2026-05-12T12:00:00-03:00",
        ),
    ]
    catalog = {
        "pla-negro": {
            "manufacturer_product_url": "https://grilon3.com.ar/producto/pla-negro/",
            "image_url": "https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg",
            "image_source": "manufacturer",
        }
    }

    payload = build_payload(raw_items, grilon3_enrichment=catalog, generated_at="2026-05-12T12:00:00-03:00")

    assert payload["generated_at"] == "2026-05-12T12:00:00-03:00"
    assert len(payload["products"]) == 1
    assert len(payload["products"][0]["offers"]) == 2
    assert payload["products"][0]["offers"][1]["stock_status"] == "out_of_stock"
    assert payload["products"][0]["manufacturer_product_url"] == "https://grilon3.com.ar/producto/pla-negro/"


def test_write_payload_creates_json_file(tmp_path: Path):
    output = tmp_path / "stock.json"
    payload = {"generated_at": "2026-05-12T12:00:00-03:00", "products": [], "sources": [], "manufacturers": []}

    write_payload(payload, output)

    assert json.loads(output.read_text(encoding="utf-8"))["products"] == []
```

- [ ] **Step 2: Run tests to verify build module is missing**

Run:

```bash
pytest tests/test_build_data.py -v
```

Expected: FAIL with `ModuleNotFoundError` or `ImportError`.

- [ ] **Step 3: Implement payload building and CLI**

Create `stockcentral/build_data.py`:

```python
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from stockcentral.connectors.filamentos3d import fetch_filamentos3d_items
from stockcentral.connectors.google_sheet import fetch_sheet_items
from stockcentral.connectors.grilon3_catalog import enrich_grilon3_product, fetch_grilon3_catalog
from stockcentral.models import Offer, ProductGroup, RawStockItem, SourceStatus
from stockcentral.normalize import build_display_name, build_product_id, normalize_record
from stockcentral.providers import MANUFACTURERS, SOURCES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="public/data/stock.json")
    args = parser.parse_args()

    generated_at = now_argentina()
    raw_items, source_statuses = fetch_all_sources(generated_at)
    grilon3_catalog = fetch_grilon3_catalog(MANUFACTURERS["grilon3"].products_url)
    grilon3_enrichment = {
        key: {
            "manufacturer_product_url": product.product_url,
            "image_url": product.image_url,
            "image_source": "manufacturer" if product.image_url else "",
        }
        for key, product in grilon3_catalog.items()
    }
    payload = build_payload(raw_items, grilon3_enrichment, generated_at, source_statuses)
    write_payload(payload, Path(args.output))


def fetch_all_sources(generated_at: str) -> tuple[list[RawStockItem], list[SourceStatus]]:
    raw_items: list[RawStockItem] = []
    statuses: list[SourceStatus] = []

    for source in SOURCES.values():
        try:
            if source.connector == "filamentos3d":
                items = fetch_filamentos3d_items(source, generated_at)
            elif source.connector == "google_sheet":
                items = fetch_sheet_items(source, generated_at)
            else:
                raise ValueError(f"Unsupported connector {source.connector}")
            raw_items.extend(items)
            statuses.append(
                SourceStatus(
                    id=source.id,
                    name=source.name,
                    zone=source.zone,
                    homepage_url=source.homepage_url,
                    source_url=source.source_url,
                    last_success_at=generated_at,
                    last_attempt_at=generated_at,
                    status="ok",
                    error_message="",
                )
            )
        except Exception as exc:
            statuses.append(
                SourceStatus(
                    id=source.id,
                    name=source.name,
                    zone=source.zone,
                    homepage_url=source.homepage_url,
                    source_url=source.source_url,
                    last_success_at="",
                    last_attempt_at=generated_at,
                    status="error",
                    error_message=str(exc)[:240],
                )
            )

    return raw_items, statuses


def build_payload(
    raw_items: list[RawStockItem],
    grilon3_enrichment: dict[str, dict[str, str]],
    generated_at: str,
    source_statuses: list[SourceStatus] | None = None,
) -> dict[str, object]:
    grouped: dict[str, list[tuple[RawStockItem, object]]] = defaultdict(list)

    for item in raw_items:
        fields = normalize_record(item)
        grouped[build_product_id(fields)].append((item, fields))

    products: list[ProductGroup] = []
    for product_id, entries in grouped.items():
        first_fields = entries[0][1]
        enrichment = _enrichment_for(first_fields, grilon3_enrichment)
        offers = [_offer_from_raw(item) for item, _fields in entries]
        products.append(
            ProductGroup(
                id=product_id,
                material=first_fields.material,
                variant=first_fields.variant,
                color=first_fields.color,
                diameter_mm=first_fields.diameter_mm,
                weight_g=first_fields.weight_g,
                brand=first_fields.brand,
                manufacturer_name=first_fields.manufacturer_name,
                manufacturer_product_url=enrichment["manufacturer_product_url"],
                image_url=enrichment["image_url"],
                image_source=enrichment["image_source"],  # type: ignore[arg-type]
                display_name=build_display_name(first_fields),
                offers=offers,
            )
        )

    products.sort(key=_product_sort_key)
    statuses = source_statuses or []

    return {
        "generated_at": generated_at,
        "products": [product.to_dict() for product in products],
        "sources": [source.to_dict() for source in statuses],
        "manufacturers": [manufacturer.to_dict() for manufacturer in MANUFACTURERS.values()],
    }


def write_payload(payload: dict[str, object], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def now_argentina() -> str:
    return datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).isoformat(timespec="seconds")


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


def _stock_status(quantity: int | None) -> str:
    if quantity is None:
        return "unknown"
    return "in_stock" if quantity > 0 else "out_of_stock"


def _product_sort_key(product: ProductGroup) -> tuple[int, str, str]:
    pla_rank = 0 if product.material == "PLA" else 1
    return (pla_rank, product.color, product.display_name)


def _enrichment_for(fields, grilon3_enrichment: dict[str, dict[str, str]]) -> dict[str, str]:
    enriched = enrich_grilon3_product(fields, {})
    if fields.brand == "Grilon3":
        key = "-".join(part.lower() for part in [fields.material, fields.variant, fields.color] if part)
        key = key.replace("+", "plus").replace(" ", "-")
        enriched = grilon3_enrichment.get(key, enriched)
    return enriched


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create a sample public JSON for frontend development**

Create `public/data/stock.json`:

```json
{
  "generated_at": "2026-05-12T12:00:00-03:00",
  "products": [
    {
      "id": "pla-negro-175-1000-grilon3",
      "material": "PLA",
      "variant": "",
      "color": "Negro",
      "diameter_mm": 1.75,
      "weight_g": 1000,
      "brand": "Grilon3",
      "manufacturer_name": "Grilon3",
      "manufacturer_product_url": "https://grilon3.com.ar/producto/pla-negro/",
      "image_url": "https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg",
      "image_source": "manufacturer",
      "display_name": "PLA Negro Grilon3 1 kg 1.75 mm",
      "offers": [
        {
          "source_id": "filamentos3d",
          "provider_name": "Filamentos3D",
          "provider_zone": "Zona Sur",
          "provider_url": "https://filamentos3d.com.ar/",
          "original_name": "GRILON3 PLA Negro 1kg 1.75mm",
          "stock_quantity": 24,
          "stock_status": "in_stock",
          "source_url": "https://filamentos3d.com.ar/grilon3.php",
          "updated_at": "2026-05-12T12:00:00-03:00"
        }
      ]
    }
  ],
  "sources": [],
  "manufacturers": []
}
```

- [ ] **Step 5: Run build tests**

Run:

```bash
pytest tests/test_build_data.py -v
```

Expected: PASS.

- [ ] **Step 6: Run the full Python test suite**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 7: Commit build orchestration**

Run:

```bash
git add stockcentral/build_data.py tests/test_build_data.py public/data/stock.json
git commit -m "feat: build public stock json"
```

---

### Task 8: Static Minimalist Frontend

**Files:**
- Create: `public/index.html`
- Create: `public/styles.css`
- Create: `public/app.js`
- Test: `tests/test_frontend_assets.py`

- [ ] **Step 1: Write frontend asset smoke tests**

Create `tests/test_frontend_assets.py`:

```python
from pathlib import Path


def test_index_loads_styles_script_and_data_app_root():
    html = Path("public/index.html").read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="styles.css">' in html
    assert '<script src="app.js" defer></script>' in html
    assert 'id="app"' in html
    assert 'StockCentral' in html


def test_frontend_script_fetches_stock_json_and_supports_required_filters():
    js = Path("public/app.js").read_text(encoding="utf-8")

    assert 'fetch("data/stock.json")' in js
    assert "material" in js
    assert "variant" in js
    assert "color" in js
    assert "diameter" in js
    assert "weight" in js
    assert "brand" in js
    assert "provider" in js
    assert "stock" in js


def test_styles_include_minimal_visual_tokens():
    css = Path("public/styles.css").read_text(encoding="utf-8")

    assert "--surface" in css
    assert "--accent" in css
    assert "border-radius" in css
    assert "@media" in css
```

- [ ] **Step 2: Run tests to verify frontend files are missing**

Run:

```bash
pytest tests/test_frontend_assets.py -v
```

Expected: FAIL with `FileNotFoundError`.

- [ ] **Step 3: Create the static HTML shell**

Create `public/index.html`:

```html
<!doctype html>
<html lang="es-AR">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>StockCentral</title>
    <meta name="description" content="Stock centralizado de filamentos 3D para AMBA.">
    <link rel="stylesheet" href="styles.css">
    <script src="app.js" defer></script>
  </head>
  <body>
    <main id="app" class="shell">
      <header class="hero">
        <div>
          <p class="eyebrow">AMBA filament stock</p>
          <h1>StockCentral</h1>
          <p class="subtitle">Filamentos disponibles por proveedor, material, color, formato y marca.</p>
        </div>
        <div class="update-card">
          <span>Ultima actualizacion</span>
          <strong id="generated-at">Cargando...</strong>
        </div>
      </header>

      <section class="toolbar" aria-label="Filtros de catalogo">
        <label class="search">
          <span>Buscar</span>
          <input id="search-input" type="search" placeholder="negro, pla+, grilon, 1kg">
        </label>

        <div class="filter-grid">
          <label><span>Material</span><select id="filter-material"></select></label>
          <label><span>Variante</span><select id="filter-variant"></select></label>
          <label><span>Color</span><select id="filter-color"></select></label>
          <label><span>Diametro</span><select id="filter-diameter"></select></label>
          <label><span>Peso</span><select id="filter-weight"></select></label>
          <label><span>Marca</span><select id="filter-brand"></select></label>
          <label><span>Proveedor</span><select id="filter-provider"></select></label>
          <label><span>Stock</span><select id="filter-stock"></select></label>
        </div>
      </section>

      <section class="summary" aria-live="polite">
        <strong id="result-count">0 productos</strong>
        <button id="pla-shortcut" type="button">Ver PLA</button>
        <button id="clear-filters" type="button">Limpiar filtros</button>
      </section>

      <section id="source-status" class="source-status" aria-label="Estado de fuentes"></section>
      <section id="products" class="products" aria-label="Productos"></section>
    </main>
  </body>
</html>
```

- [ ] **Step 4: Create the minimalist CSS**

Create `public/styles.css`:

```css
:root {
  --bg: #f5f5f7;
  --surface: #ffffff;
  --surface-soft: #fbfbfd;
  --text: #1d1d1f;
  --muted: #6e6e73;
  --line: #d2d2d7;
  --accent: #0071e3;
  --success: #0a7f37;
  --empty: #8a1c1c;
  --radius: 18px;
  --shadow: 0 18px 45px rgba(0, 0, 0, 0.07);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
}

.shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 40px 0 64px;
}

.hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.eyebrow {
  margin: 0 0 8px;
  color: var(--muted);
  font-size: 13px;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(42px, 7vw, 76px);
  line-height: 0.95;
  letter-spacing: 0;
}

.subtitle {
  max-width: 620px;
  margin: 14px 0 0;
  color: var(--muted);
  font-size: 18px;
  line-height: 1.45;
}

.update-card,
.toolbar,
.product-card,
.source-status {
  background: var(--surface);
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.update-card {
  min-width: 230px;
  padding: 18px;
}

.update-card span,
label span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 7px;
}

.toolbar {
  padding: 18px;
  margin-bottom: 16px;
}

.search input,
select {
  width: 100%;
  min-height: 42px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface-soft);
  color: var(--text);
  padding: 0 12px;
  font: inherit;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 16px 0;
}

button {
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  padding: 10px 14px;
  font: inherit;
  cursor: pointer;
}

#pla-shortcut {
  background: var(--accent);
  border-color: var(--accent);
  color: #ffffff;
}

.source-status {
  display: grid;
  gap: 8px;
  padding: 14px;
  margin-bottom: 16px;
}

.source-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: var(--muted);
  font-size: 14px;
}

.products {
  display: grid;
  gap: 14px;
}

.product-card {
  display: grid;
  grid-template-columns: 112px 1fr;
  gap: 18px;
  padding: 18px;
}

.product-image {
  width: 112px;
  height: 112px;
  object-fit: contain;
  border-radius: 14px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
}

.image-placeholder {
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 12px;
}

.product-title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 10px;
}

.product-title h2 {
  margin: 0;
  font-size: 22px;
  letter-spacing: 0;
}

a {
  color: inherit;
  text-decoration: none;
}

a:hover {
  color: var(--accent);
}

.chips,
.offers {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip,
.offer {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 7px 10px;
  color: var(--muted);
  font-size: 13px;
}

.offer {
  border-radius: 12px;
  background: var(--surface-soft);
}

.stock-in {
  color: var(--success);
  font-weight: 700;
}

.stock-out {
  color: var(--empty);
  font-weight: 700;
}

@media (max-width: 760px) {
  .shell {
    width: min(100% - 20px, 1180px);
    padding-top: 24px;
  }

  .hero {
    align-items: stretch;
    flex-direction: column;
  }

  .filter-grid {
    grid-template-columns: 1fr;
  }

  .summary {
    align-items: stretch;
    flex-direction: column;
  }

  .product-card {
    grid-template-columns: 1fr;
  }

  .product-image {
    width: 100%;
    height: 180px;
  }
}
```

- [ ] **Step 5: Create the frontend behavior**

Create `public/app.js`:

```javascript
const state = {
  products: [],
  sources: [],
  filters: {
    search: "",
    material: "",
    variant: "",
    color: "",
    diameter: "",
    weight: "",
    brand: "",
    provider: "",
    stock: "all",
  },
};

const filterIds = {
  material: "filter-material",
  variant: "filter-variant",
  color: "filter-color",
  diameter: "filter-diameter",
  weight: "filter-weight",
  brand: "filter-brand",
  provider: "filter-provider",
  stock: "filter-stock",
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  const response = await fetch("data/stock.json");
  const payload = await response.json();
  state.products = payload.products || [];
  state.sources = payload.sources || [];
  document.getElementById("generated-at").textContent = formatDate(payload.generated_at);
  setupFilters();
  bindEvents();
  render();
}

function setupFilters() {
  setSelect("stock", [
    ["all", "Cualquier estado"],
    ["in_stock", "Con stock"],
    ["out_of_stock", "Sin stock"],
  ]);
  setSelect("material", valuesFor("material"), "Material");
  setSelect("variant", valuesFor("variant"), "Variante");
  setSelect("color", valuesFor("color"), "Color");
  setSelect("diameter", valuesFor("diameter_mm").map((value) => [String(value), `${value} mm`]), "Diametro");
  setSelect("weight", valuesFor("weight_g").map((value) => [String(value), `${value / 1000:g} kg`.replace(":g", "")]), "Peso");
  setSelect("brand", valuesFor("brand"), "Marca");
  setSelect("provider", providerValues(), "Proveedor");
}

function bindEvents() {
  document.getElementById("search-input").addEventListener("input", (event) => {
    state.filters.search = event.target.value.toLowerCase().trim();
    render();
  });

  Object.entries(filterIds).forEach(([key, id]) => {
    document.getElementById(id).addEventListener("change", (event) => {
      state.filters[key] = event.target.value;
      render();
    });
  });

  document.getElementById("pla-shortcut").addEventListener("click", () => {
    state.filters.material = "PLA";
    document.getElementById("filter-material").value = "PLA";
    render();
  });

  document.getElementById("clear-filters").addEventListener("click", () => {
    state.filters = { search: "", material: "", variant: "", color: "", diameter: "", weight: "", brand: "", provider: "", stock: "all" };
    document.getElementById("search-input").value = "";
    Object.entries(filterIds).forEach(([key, id]) => {
      document.getElementById(id).value = key === "stock" ? "all" : "";
    });
    render();
  });
}

function render() {
  const filtered = state.products.filter(matchesFilters);
  document.getElementById("result-count").textContent = `${filtered.length} productos`;
  renderSources();
  renderProducts(filtered);
}

function matchesFilters(product) {
  const text = [
    product.display_name,
    product.material,
    product.variant,
    product.color,
    product.brand,
    ...(product.offers || []).map((offer) => `${offer.provider_name} ${offer.original_name}`),
  ].join(" ").toLowerCase();

  if (state.filters.search && !text.includes(state.filters.search)) return false;
  if (state.filters.material && product.material !== state.filters.material) return false;
  if (state.filters.variant && product.variant !== state.filters.variant) return false;
  if (state.filters.color && product.color !== state.filters.color) return false;
  if (state.filters.diameter && String(product.diameter_mm) !== state.filters.diameter) return false;
  if (state.filters.weight && String(product.weight_g) !== state.filters.weight) return false;
  if (state.filters.brand && product.brand !== state.filters.brand) return false;
  if (state.filters.provider && !(product.offers || []).some((offer) => offer.provider_name === state.filters.provider)) return false;
  if (state.filters.stock !== "all" && !(product.offers || []).some((offer) => offer.stock_status === state.filters.stock)) return false;
  return true;
}

function renderSources() {
  const container = document.getElementById("source-status");
  if (!state.sources.length) {
    container.innerHTML = "";
    return;
  }
  container.innerHTML = state.sources.map((source) => `
    <div class="source-row">
      <span>${escapeHtml(source.name)} · ${escapeHtml(source.zone)}</span>
      <span>${source.status === "ok" ? "Actualizado" : `Error: ${escapeHtml(source.error_message)}`}</span>
    </div>
  `).join("");
}

function renderProducts(products) {
  const container = document.getElementById("products");
  container.innerHTML = products.map(productTemplate).join("");
}

function productTemplate(product) {
  const title = product.manufacturer_product_url
    ? `<a href="${escapeAttribute(product.manufacturer_product_url)}" target="_blank" rel="noopener">${escapeHtml(product.display_name)}</a>`
    : escapeHtml(product.display_name);
  const image = product.image_url
    ? `<img class="product-image" src="${escapeAttribute(product.image_url)}" alt="${escapeAttribute(product.display_name)}">`
    : `<div class="product-image image-placeholder">Sin imagen</div>`;
  return `
    <article class="product-card">
      ${image}
      <div>
        <div class="product-title"><h2>${title}</h2></div>
        <div class="chips">
          ${chip(product.material)}
          ${product.variant ? chip(product.variant) : ""}
          ${chip(product.color)}
          ${product.diameter_mm ? chip(`${product.diameter_mm} mm`) : ""}
          ${product.weight_g ? chip(`${product.weight_g / 1000} kg`) : ""}
          ${product.brand ? chip(product.brand) : ""}
        </div>
        <div class="offers">${(product.offers || []).map(offerTemplate).join("")}</div>
      </div>
    </article>
  `;
}

function offerTemplate(offer) {
  const stockClass = offer.stock_status === "in_stock" ? "stock-in" : "stock-out";
  const stockLabel = offer.stock_status === "in_stock" ? `${offer.stock_quantity} en stock` : "Sin stock";
  return `
    <div class="offer">
      <a href="${escapeAttribute(offer.provider_url)}" target="_blank" rel="noopener">${escapeHtml(offer.provider_name)}</a>
      · ${escapeHtml(offer.provider_zone)}
      · <span class="${stockClass}">${escapeHtml(stockLabel)}</span>
      <br><small>${escapeHtml(offer.original_name)}</small>
    </div>
  `;
}

function chip(value) {
  return `<span class="chip">${escapeHtml(value)}</span>`;
}

function setSelect(key, values, emptyLabel = "") {
  const select = document.getElementById(filterIds[key]);
  const normalized = values.map((value) => Array.isArray(value) ? value : [value, value]);
  const options = emptyLabel ? [["", emptyLabel], ...normalized] : normalized;
  select.innerHTML = options.map(([value, label]) => `<option value="${escapeAttribute(value)}">${escapeHtml(label)}</option>`).join("");
}

function valuesFor(field) {
  return [...new Set(state.products.map((product) => product[field]).filter((value) => value !== "" && value !== null && value !== undefined))].sort();
}

function providerValues() {
  return [...new Set(state.products.flatMap((product) => (product.offers || []).map((offer) => offer.provider_name)))].sort();
}

function formatDate(value) {
  if (!value) return "Sin datos";
  return new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
```

- [ ] **Step 6: Fix the JavaScript weight label before running tests**

In `public/app.js`, replace the weight select line:

```javascript
setSelect("weight", valuesFor("weight_g").map((value) => [String(value), `${value / 1000:g} kg`.replace(":g", "")]), "Peso");
```

with:

```javascript
setSelect("weight", valuesFor("weight_g").map((value) => [String(value), `${Number(value) / 1000} kg`]), "Peso");
```

- [ ] **Step 7: Run frontend asset tests**

Run:

```bash
pytest tests/test_frontend_assets.py -v
```

Expected: PASS.

- [ ] **Step 8: Run local static server**

Run:

```bash
python -m http.server 8000 -d public
```

Expected: server starts at `http://localhost:8000`.

- [ ] **Step 9: Browser smoke check**

Open `http://localhost:8000` in the in-app browser and verify:

- The page loads without console-visible blank state.
- The catalog shows the sample PLA product.
- The PLA shortcut filters to PLA.
- Search for `negro` keeps the sample product visible.
- The provider name opens the provider URL in a new tab.
- The product title opens the Grilon3 manufacturer URL in a new tab.
- Mobile width keeps filters and cards readable with no overlap.

- [ ] **Step 10: Commit frontend**

Run:

```bash
git add public/index.html public/styles.css public/app.js tests/test_frontend_assets.py
git commit -m "feat: add static stock catalog"
```

---

### Task 9: GitHub Actions CI And Pages Deployment

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/pages.yml`

- [ ] **Step 1: Create CI workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: python -m pip install -e ".[dev]"
      - name: Run tests
        run: pytest -v
```

- [ ] **Step 2: Create scheduled GitHub Pages workflow**

Create `.github/workflows/pages.yml`:

```yaml
name: Build and deploy stock site

on:
  workflow_dispatch:
  schedule:
    - cron: "0 12,15,18,21 * * 1-5"

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: python -m pip install -e ".[dev]"
      - name: Run tests
        run: pytest -v
      - name: Build stock data
        run: python -m stockcentral.build_data --output public/data/stock.json
      - name: Configure Pages
        uses: actions/configure-pages@v5
      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: public

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Run tests locally after workflow files are added**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 4: Commit workflows**

Run:

```bash
git add .github/workflows/ci.yml .github/workflows/pages.yml
git commit -m "ci: add tests and pages deployment"
```

---

### Task 10: Final Verification And Documentation Polish

**Files:**
- Modify: `README.md`
- Verify: all source, tests, workflows, public assets.

- [ ] **Step 1: Update README with usage and Pages notes**

Modify `README.md` to:

````markdown
# StockCentral

StockCentral centraliza stock online de proveedores de filamento 3D del AMBA.

## Desarrollo local

```bash
python -m pip install -e ".[dev]"
pytest
python -m stockcentral.build_data --output public/data/stock.json
python -m http.server 8000 -d public
```

Abrir `http://localhost:8000`.

## Fuentes iniciales

- Filamentos3D: Zona Sur.
- Grupo Senz: Zona Oeste.
- MundoInsumos: Zona Norte.

## Actualizacion

GitHub Actions ejecuta el build en dias habiles a las 09:00, 12:00, 15:00 y 18:00 hora Argentina. El cron esta expresado en UTC como `0 12,15,18,21 * * 1-5`.

## Publicacion

El workflow `Build and deploy stock site` genera `public/data/stock.json` y publica la carpeta `public/` con GitHub Pages. En la configuracion del repositorio, Pages debe usar GitHub Actions como source.
````

- [ ] **Step 2: Run complete local verification**

Run:

```bash
pytest -v
python -m stockcentral.build_data --output public/data/stock.json
python -m http.server 8000 -d public
```

Expected:

- `pytest -v` passes.
- `public/data/stock.json` is written.
- Static server starts at `http://localhost:8000`.

- [ ] **Step 3: Browser visual verification**

Open `http://localhost:8000` in the in-app browser and verify:

- Desktop view has a light, minimal, spacious catalog surface.
- Mobile view has no overlapping filters, cards or product text.
- Product image area stays stable when an image is missing.
- Products without stock remain visible.
- There are no prices in the UI.
- Zone appears next to providers but no zone filter exists.

- [ ] **Step 4: Inspect git status**

Run:

```bash
git status --short
```

Expected: only intentional files changed.

- [ ] **Step 5: Commit final documentation polish**

Run:

```bash
git add README.md public/data/stock.json
git commit -m "docs: document local and pages workflows"
```

---

## Self-Review

Spec coverage:

- Public static app: Task 8 and Task 9.
- Python ingestion and normalization: Task 3, Task 4, Task 5 and Task 7.
- GitHub Actions scheduled updates: Task 9.
- GitHub Pages publication: Task 9.
- Initial providers across AMBA: Task 2, Task 4 and Task 5.
- PLA priority and catalog filters: Task 8.
- No prices: Task 8 visual verification.
- Products without stock visible: Task 7 and Task 10.
- Manufacturer links and images: Task 6, Task 7 and Task 8.
- Grilon3 official catalog and 3N3 without invented site: Task 2 and Task 6.
- Minimalist Apple-inspired UI: Task 8 and Task 10.

Placeholder scan:

- The plan contains concrete file paths, tests, commands and expected outcomes.
- No step requires unspecified implementation work.

Type consistency:

- `RawStockItem`, `NormalizedFields`, `Offer`, `ProductGroup`, `SourceStatus` and `ManufacturerInfo` are introduced before they are consumed.
- Frontend field names match `ProductGroup.to_dict()` and `Offer.to_dict()`.
