import json

from stockcentral.build_data import (
    build_grilon3_enrichments,
    build_payload,
    collect_raw_items,
    fetch_grilon3_catalog_products,
    write_payload,
)
from stockcentral.connectors.grilon3_catalog import CatalogProduct
from stockcentral.models import RawStockItem
from stockcentral.providers import MANUFACTURERS, SOURCES


def raw(
    source_id: str,
    provider_name: str,
    provider_zone: str,
    name: str,
    stock_quantity: int | None,
    brand_hint: str = "",
) -> RawStockItem:
    source = SOURCES[source_id]
    return RawStockItem(
        source_id=source_id,
        provider_name=provider_name,
        provider_zone=provider_zone,
        provider_url=source.homepage_url,
        original_name=name,
        stock_quantity=stock_quantity,
        source_url=source.source_url,
        brand_hint=brand_hint,
        updated_at="2026-05-12T12:00:00-03:00",
    )


def test_build_payload_groups_products_and_keeps_unknown_stock_visible():
    payload = build_payload(
        [
            raw(
                "filamentos3d",
                "Filamentos3D",
                "Zona Sur",
                "GRILON3 PLA Negro 1kg 1.75mm",
                4,
                brand_hint="Grilon3",
            ),
            raw(
                "mundoinsumos",
                "MundoInsumos",
                "Zona Norte",
                "GRILON3 PLA 02_G1_NEGRO 1.75 MM X 1 KG",
                0,
                brand_hint="Grilon3",
            ),
            raw(
                "grupo_senz",
                "Grupo Senz",
                "Zona Oeste",
                "3N3 PLA+ Rojo 1kg 1.75mm",
                None,
            ),
        ],
        sources=SOURCES,
        manufacturers=MANUFACTURERS,
        generated_at="2026-05-12T13:00:00-03:00",
        enrichments={
            "pla-negro-175-1000-grilon3": {
                "manufacturer_product_url": "https://grilon3.com.ar/producto/pla-negro/",
                "image_url": "assets/grilon3/pla-negro.jpg",
                "image_source": "manufacturer",
            }
        },
    )

    assert payload["generated_at"] == "2026-05-12T13:00:00-03:00"
    assert len(payload["products"]) == 2
    assert payload["products"][0]["id"] == "pla-negro-175-1000-grilon3"
    assert payload["products"][0]["manufacturer_product_url"] == "https://grilon3.com.ar/producto/pla-negro/"
    assert payload["products"][0]["image_url"] == "assets/grilon3/pla-negro.jpg"
    assert [offer["provider_name"] for offer in payload["products"][0]["offers"]] == [
        "MundoInsumos",
        "Filamentos3D",
    ]
    assert payload["products"][0]["offers"][0]["stock_status"] == "out_of_stock"
    assert payload["products"][1]["offers"][0]["stock_status"] == "unknown"


def test_build_payload_orders_sources_north_west_south_and_counts_carretes():
    payload = build_payload(
        [
            raw("filamentos3d", "Filamentos3D", "Zona Sur", "GRILON3 PLA Negro 1kg 1.75mm", 4, "Grilon3"),
            raw("mundoinsumos", "MundoInsumos", "Zona Norte", "GRILON3 PLA Blanco 1kg 1.75mm", 2, "Grilon3"),
            raw("grupo_senz", "Grupo Senz", "Zona Oeste", "3N3 PLA Rojo 1kg 1.75mm", None),
        ],
        sources=SOURCES,
        manufacturers=MANUFACTURERS,
        generated_at="2026-05-12T13:00:00-03:00",
    )

    assert [source["id"] for source in payload["sources"]] == ["mundoinsumos", "grupo_senz", "filamentos3d"]
    stats_by_id = {source["id"]: source["stats"] for source in payload["sources"]}
    assert stats_by_id["mundoinsumos"]["total_stock_units"] == 2
    assert stats_by_id["grupo_senz"]["total_stock_units"] == 0
    assert stats_by_id["filamentos3d"]["total_stock_units"] == 4
    assert stats_by_id["grupo_senz"]["product_count"] == 1


def test_build_payload_deduplicates_repeated_provider_rows():
    item = raw("filamentos3d", "Filamentos3D", "Zona Sur", "GRILON3 PLA Negro 1kg 1.75mm", 4, "Grilon3")

    payload = build_payload(
        [item, item],
        sources=SOURCES,
        manufacturers=MANUFACTURERS,
        generated_at="2026-05-12T13:00:00-03:00",
    )

    assert len(payload["products"][0]["offers"]) == 1


def test_build_payload_adds_catalog_products_without_provider_stock():
    payload = build_payload(
        [],
        sources=SOURCES,
        manufacturers=MANUFACTURERS,
        generated_at="2026-05-12T13:00:00-03:00",
        catalog_products={
            "pla-blanco-285-1000-grilon3": CatalogProduct(
                product_id="pla-blanco-285-1000-grilon3",
                title="PLA Blanco Grilon3 1 kg 2.85 mm",
                product_url="https://grilon3.com.ar/producto/pla-blanco-285/",
                image_url="",
            )
        },
    )

    product = payload["products"][0]
    assert product["id"] == "pla-blanco-285-1000-grilon3"
    assert product["diameter_mm"] == 2.85
    assert product["offers"] == []
    assert product["manufacturer_product_url"] == "https://grilon3.com.ar/producto/pla-blanco-285/"


def test_build_payload_does_not_add_catalog_products_without_285_diameter():
    payload = build_payload(
        [],
        sources=SOURCES,
        manufacturers=MANUFACTURERS,
        generated_at="2026-05-12T13:00:00-03:00",
        catalog_products={
            "pla-negro-175-1000-grilon3": CatalogProduct(
                product_id="pla-negro-175-1000-grilon3",
                title="PLA Negro Grilon3 1 kg 1.75 mm",
                product_url="https://grilon3.com.ar/producto/pla-negro/",
                image_url="",
            ),
            "abs-negro-285-unknown-grilon3": CatalogProduct(
                product_id="abs-negro-285-unknown-grilon3",
                title="ABS Negro 2.85 Grilon3",
                product_url="https://grilon3.com.ar/producto/abs-negro-285/",
                image_url="",
            ),
        },
    )

    assert payload["products"] == []


def test_build_payload_marks_partial_source_errors():
    payload = build_payload(
        [],
        sources=SOURCES,
        manufacturers=MANUFACTURERS,
        generated_at="2026-05-12T13:00:00-03:00",
        source_errors={"grupo_senz": "CSV export returned 403"},
    )

    source_by_id = {source["id"]: source for source in payload["sources"]}
    assert source_by_id["grupo_senz"]["status"] == "error"
    assert source_by_id["grupo_senz"]["last_success_at"] == ""
    assert source_by_id["grupo_senz"]["last_attempt_at"] == "2026-05-12T13:00:00-03:00"
    assert source_by_id["grupo_senz"]["error_message"] == "CSV export returned 403"


def test_collect_raw_items_keeps_fetching_when_one_source_fails(monkeypatch):
    def fake_fetch(source, updated_at):
        if source.id == "grupo_senz":
            raise RuntimeError("boom")
        return [
            RawStockItem(
                source_id=source.id,
                provider_name=source.name,
                provider_zone=source.zone,
                provider_url=source.homepage_url,
                original_name=f"{source.name} PLA Negro 1kg",
                stock_quantity=1,
                source_url=source.source_url,
                updated_at=updated_at,
            )
        ]

    monkeypatch.setattr("stockcentral.build_data._fetch_source_items", fake_fetch)

    items, errors = collect_raw_items(sources=SOURCES, updated_at="2026-05-12T13:00:00-03:00")

    assert [item.source_id for item in items] == ["filamentos3d", "mundoinsumos"]
    assert errors == {"grupo_senz": "boom"}


def test_build_grilon3_enrichments_indexes_raw_grilon_products(monkeypatch):
    class CatalogProduct:
        product_url = "https://grilon3.com.ar/producto/pla-negro/"
        image_url = "https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg"

    def fake_fetch_catalog(products_url):
        assert products_url == "https://grilon3.com.ar/productos/"
        return {"pla-negro-175-1000-grilon3": CatalogProduct()}

    monkeypatch.setattr("stockcentral.connectors.grilon3_catalog.fetch_grilon3_catalog", fake_fetch_catalog)

    enrichments = build_grilon3_enrichments(
        [
            raw(
                "filamentos3d",
                "Filamentos3D",
                "Zona Sur",
                "GRILON3 PLA Negro 1kg 1.75mm",
                4,
                brand_hint="Grilon3",
            )
        ]
    )

    assert enrichments["pla-negro-175-1000-grilon3"]["manufacturer_product_url"] == "https://grilon3.com.ar/producto/pla-negro/"


def test_fetch_grilon3_catalog_products_merges_shop_and_sitemap(monkeypatch):
    def fake_shop(url):
        return {
            "pla-negro-175-1000-grilon3": CatalogProduct(
                product_id="pla-negro-175-1000-grilon3",
                title="PLA Negro Grilon3 1 kg 1.75 mm",
                product_url="https://grilon3.com.ar/producto/pla-negro/",
                image_url="",
            )
        }

    def fake_sitemap():
        return {
            "pla-blanco-285-1000-grilon3": CatalogProduct(
                product_id="pla-blanco-285-1000-grilon3",
                title="PLA Blanco Grilon3 1 kg 2.85 mm",
                product_url="https://grilon3.com.ar/producto/pla-blanco-285/",
                image_url="",
            )
        }

    monkeypatch.setattr("stockcentral.connectors.grilon3_catalog.fetch_grilon3_catalog", fake_shop)
    monkeypatch.setattr("stockcentral.connectors.grilon3_catalog.fetch_grilon3_sitemap_catalog", fake_sitemap)

    catalog = fetch_grilon3_catalog_products()

    assert set(catalog) == {"pla-negro-175-1000-grilon3", "pla-blanco-285-1000-grilon3"}


def test_write_payload_creates_json_file(tmp_path):
    output = tmp_path / "stock.json"
    payload = build_payload([], sources=SOURCES, manufacturers=MANUFACTURERS, generated_at="2026-05-12T13:00:00-03:00")

    write_payload(payload, output)

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["generated_at"] == "2026-05-12T13:00:00-03:00"
    assert written["products"] == []
