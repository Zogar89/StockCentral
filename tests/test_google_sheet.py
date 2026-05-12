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

    assert len(items) == 5
    assert items[0].original_name == "3N3 PLA+ Rojo 1kg 1.75mm"
    assert items[0].stock_quantity == 12
    assert items[0].brand_hint == ""
    assert items[1].stock_quantity == 0
    assert items[2].stock_quantity is None
    assert items[3].stock_quantity is None
    assert items[4].stock_quantity is None


def test_parse_sheet_csv_supports_mundoinsumos_headers():
    csv_text = "\n".join(
        [
            ",,,,,",
            ",,,,,",
            "Código,Descripción,Código,STOCK REAL,,",
            "SKU Fábrica,Grilon3,EAN13,,,",
            "GAMA ABS,,,,,",
            "M10ING175CJ,GRILON3 PLA 02_G1_NEGRO 1.75 MM X 1 KG,7798049652795,114,,",
            "M10IRJ175CJ,GRILON3 PLA 05_G1_ROJO 1.75 MM X 1 KG,7798049652825,-5,,",
            "S10ILA1010K,KIT LAPIZ 3D GRILON3 PLA 10 COLORES 10M POR COLOR (100M),7798049657394,#N/A,,",
        ]
    )
    source = SOURCES["mundoinsumos"]

    items = parse_sheet_csv(csv_text, source, updated_at="2026-05-12T12:00:00-03:00")

    assert len(items) == 3
    assert items[0].original_name == "GRILON3 PLA 02_G1_NEGRO 1.75 MM X 1 KG"
    assert items[0].stock_quantity == 114
    assert items[1].stock_quantity is None
    assert items[2].stock_quantity is None


def test_parse_sheet_csv_repairs_mojibake_headers_from_export_response():
    csv_text = "\n".join(
        [
            "CÃ³digo,DescripciÃ³n,CÃ³digo,STOCK REAL,,",
            "M10ING175CJ,GRILON3 PLA 02_G1_NEGRO 1.75 MM X 1 KG,7798049652795,114,,",
        ]
    )
    source = SOURCES["mundoinsumos"]

    items = parse_sheet_csv(csv_text, source, updated_at="2026-05-12T12:00:00-03:00")

    assert len(items) == 1
    assert items[0].stock_quantity == 114
