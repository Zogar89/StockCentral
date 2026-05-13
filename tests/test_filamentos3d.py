from pathlib import Path

from stockcentral.connectors.filamentos3d import fetch_filamentos3d_items, parse_filamentos3d_html
from stockcentral.providers import SOURCES


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "filamentos3d_stock.html"


def test_parse_filamentos3d_html_keeps_products_and_defensive_stock_values():
    source = SOURCES["filamentos3d"]
    updated_at = "2026-05-12T12:00:00Z"

    items = parse_filamentos3d_html(FIXTURE_PATH.read_text(encoding="utf-8"), source, updated_at)

    assert [item.original_name for item in items] == [
        "PLA Grilon3 Negro 1.75mm 1kg",
        "PETG Grilon3 Natural 1.75mm 1kg",
        "ABS Grilon3 Rojo 1.75mm 1kg",
        "TPU Grilon3 Azul 1.75mm 500g",
        "PLA Grilon3 Blanco 1.75mm 1kg",
    ]
    assert [item.stock_quantity for item in items] == [12, 0, None, None, None]
    assert {item.brand_hint for item in items} == {"Grilon3"}

    first = items[0]
    assert first.source_id == "filamentos3d"
    assert first.provider_name == "Filamentos3D"
    assert first.provider_zone == "Zona Sur"
    assert first.provider_url == "https://filamentos3d.com.ar/"
    assert first.source_url == "https://filamentos3d.com.ar/grilon3.php"
    assert first.updated_at == updated_at


def test_fetch_filamentos3d_items_downloads_source_url(monkeypatch):
    source = SOURCES["filamentos3d"]
    updated_at = "2026-05-12T12:00:00Z"
    fixture_html = FIXTURE_PATH.read_text(encoding="utf-8")
    calls = []

    class Response:
        text = fixture_html

        def raise_for_status(self):
            calls.append("raise_for_status")

    def fake_get(url, timeout, follow_redirects=True):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr("stockcentral.connectors.filamentos3d.httpx.get", fake_get)

    items = fetch_filamentos3d_items(source, updated_at, timeout_seconds=7)

    assert calls == [(source.source_url, 7), "raise_for_status"]
    assert len(items) == 5
    assert items[0].original_name == "PLA Grilon3 Negro 1.75mm 1kg"


def test_parse_filamentos3d_html_supports_real_grilon3_table_shape():
    html = """
    <table>
      <tr><th>SKU Fábrica</th><th>Grilon3</th><th></th></tr>
      <tr><td>M09IBL175CJ</td><td>GRILON3 ABS 01_BLANCO 1.75 MM X 1 KG</td><td>93</td></tr>
      <tr><td>M09IGR175CJ</td><td>GRILON3 ABS 04_GRIS PLATA 1.75 MM X 1 KG</td><td>0</td></tr>
    </table>
    """
    source = SOURCES["filamentos3d"]

    items = parse_filamentos3d_html(html, source, updated_at="2026-05-12T12:00:00Z")

    assert [item.original_name for item in items] == [
        "GRILON3 ABS 01_BLANCO 1.75 MM X 1 KG",
        "GRILON3 ABS 04_GRIS PLATA 1.75 MM X 1 KG",
    ]
    assert [item.stock_quantity for item in items] == [93, 0]


def test_parse_filamentos3d_html_skips_section_rows_without_stock():
    html = """
    <table>
      <tr><th>SKU Fábrica</th><th>Grilon3</th><th></th></tr>
      <tr><td></td><td>GRILON3 KITS LÁPIZ 3D</td><td></td></tr>
      <tr><td></td><td>SUBMARCA 3NMAX (PVP LIBRE)</td><td></td></tr>
      <tr><td>M09IBL175CJ</td><td>GRILON3 ABS 01_BLANCO 1.75 MM X 1 KG</td><td>93</td></tr>
    </table>
    """
    source = SOURCES["filamentos3d"]

    items = parse_filamentos3d_html(html, source, updated_at="2026-05-12T12:00:00Z")

    assert [item.original_name for item in items] == ["GRILON3 ABS 01_BLANCO 1.75 MM X 1 KG"]
