import json
from pathlib import Path

import pytest

from centraldefilamentos.cache_grilon3_metadata import build_grilon3_metadata_cache, download_grilon3_images, load_metadata_cache
from centraldefilamentos.build_data import (
    build_filamentos3d_enrichments,
    build_grilon3_enrichments,
    build_payload,
    collect_raw_items,
    evaluate_build_quality,
    fetch_grilon3_catalog_products,
    load_grilon3_metadata,
    load_filamentos3d_metadata,
    write_build_logs,
    write_payload,
)
from centraldefilamentos.connectors.grilon3_catalog import CatalogProduct
from centraldefilamentos.models import RawStockItem
from centraldefilamentos.providers import MANUFACTURERS, SOURCES
from centraldefilamentos.thumbnails import apply_thumbnails_to_stock, thumbnail_url_for
from centraldefilamentos.update_filamentos3d_images import apply_filamentos3d_images


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
                "manufacturer_product_url": "https://grilon3.com.ar/producto/catalog-product/",
                "image_url": "assets/grilon3/catalog-product.jpg",
                "image_source": "manufacturer",
            }
        },
    )

    assert payload["generated_at"] == "2026-05-12T13:00:00-03:00"
    assert len(payload["products"]) == 2
    assert payload["products"][0]["id"] == "pla-negro-175-1000-grilon3"
    assert payload["products"][0]["manufacturer_product_url"] == "https://grilon3.com.ar/producto/catalog-product/"
    assert payload["products"][0]["image_url"] == "assets/grilon3/catalog-product.jpg"
    assert payload["products"][0]["thumbnail_url"] == "assets/thumbs/grilon3/catalog-product.webp"
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


def test_build_payload_deduplicates_provider_alias_rows_after_normalization():
    payload = build_payload(
        [
            raw("grupo_senz", "Grupo Senz", "Zona Oeste", "GRILON3 BOUTIQUE PERLA CÁLIDO 1.75 MM X 1 KG", 19, "Grilon3"),
            raw("grupo_senz", "Grupo Senz", "Zona Oeste", "GRILON3 BOUTIQUE PERLA  CALIDO 1.75 MM X 1 KG", 0, "Grilon3"),
        ],
        sources=SOURCES,
        manufacturers=MANUFACTURERS,
        generated_at="2026-05-12T13:00:00-03:00",
    )

    assert len(payload["products"][0]["offers"]) == 1
    assert payload["products"][0]["offers"][0]["stock_quantity"] == 19


def test_build_payload_rejects_repeated_provider_inside_product_card():
    with pytest.raises(ValueError, match="repeated provider offers"):
        build_payload(
            [
                raw("filamentos3d", "Filamentos3D", "Zona Sur", "GRILON3 PLA Negro 1kg 1.75mm", 4, "Grilon3"),
                raw("filamentos3d", "Filamentos3D", "Zona Sur", "GRILON3 PLA NEGRO 1.75 MM X KG", 2, "Grilon3"),
            ],
            sources=SOURCES,
            manufacturers=MANUFACTURERS,
            generated_at="2026-05-12T13:00:00-03:00",
        )


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

    monkeypatch.setattr("centraldefilamentos.build_data._fetch_source_items", fake_fetch)

    items, errors = collect_raw_items(sources=SOURCES, updated_at="2026-05-12T13:00:00-03:00")

    assert [item.source_id for item in items] == ["filamentos3d", "mundoinsumos"]
    assert errors == {"grupo_senz": "boom"}


def test_collect_raw_items_retries_transient_source_failures(monkeypatch):
    attempts = {"mundoinsumos": 0}

    def fake_fetch(source, updated_at):
        if source.id == "mundoinsumos":
            attempts[source.id] += 1
            if attempts[source.id] == 1:
                raise RuntimeError("temporary timeout")
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

    monkeypatch.setattr("centraldefilamentos.build_data._fetch_source_items", fake_fetch)

    items, errors = collect_raw_items(sources={"mundoinsumos": SOURCES["mundoinsumos"]}, updated_at="2026-05-12T13:00:00-03:00", retry_attempts=2)

    assert [item.source_id for item in items] == ["mundoinsumos"]
    assert attempts == {"mundoinsumos": 2}
    assert errors == {}


def test_evaluate_build_quality_blocks_source_errors():
    current = build_payload(
        [
            raw("mundoinsumos", "MundoInsumos", "Zona Norte", "GRILON3 PLA Negro 1kg", 10, brand_hint="Grilon3"),
            raw("filamentos3d", "Filamentos3D", "Zona Sur", "GRILON3 PLA Rojo 1kg", 20, brand_hint="Grilon3"),
        ],
        generated_at="2026-05-15T12:00:00-03:00",
        source_errors={"grupo_senz": "CSV export returned 403"},
    )
    previous = build_payload(
        [
            raw("mundoinsumos", "MundoInsumos", "Zona Norte", "GRILON3 PLA Negro 1kg", 10, brand_hint="Grilon3"),
            raw("grupo_senz", "Grupo Senz", "Zona Oeste", "GRILON3 PLA Azul 1kg", 30, brand_hint="Grilon3"),
            raw("filamentos3d", "Filamentos3D", "Zona Sur", "GRILON3 PLA Rojo 1kg", 20, brand_hint="Grilon3"),
        ],
        generated_at="2026-05-15T09:00:00-03:00",
    )

    report = evaluate_build_quality(current, previous, {"grupo_senz": "CSV export returned 403"})

    assert report["should_publish"] is False
    assert report["status"] == "blocked"
    assert report["last_good_sources"]["grupo_senz"]["total_stock_units"] == 30
    assert report["last_good_sources"]["grupo_senz"]["generated_at"] == "2026-05-15T09:00:00-03:00"
    assert any(event["code"] == "source_error" for event in report["technical_events"])
    assert any("Grupo Senz" in event["message"] and "ultimo dato bueno" in event["message"] for event in report["business_events"])


def test_evaluate_build_quality_blocks_invalid_payload_schema():
    report = evaluate_build_quality(
        {"generated_at": "2026-05-15T12:00:00-03:00", "products": [{"id": "ok"}]},
        {"products": [{"id": "ok"}], "sources": []},
        {},
    )

    assert report["should_publish"] is False
    assert any(event["code"] == "schema_error" for event in report["technical_events"])
    assert any("estructura" in event["message"] for event in report["business_events"])


def test_evaluate_build_quality_blocks_suspicious_provider_stock_drop():
    current = {
        "generated_at": "2026-05-15T12:00:00-03:00",
        "products": [{"id": f"product-{index}"} for index in range(100)],
        "sources": [
            {"id": "mundoinsumos", "name": "MundoInsumos", "status": "ok", "stats": {"total_stock_units": 120, "product_count": 100}},
        ],
    }
    previous = {
        "generated_at": "2026-05-15T09:00:00-03:00",
        "products": [{"id": f"product-{index}"} for index in range(100)],
        "sources": [
            {"id": "mundoinsumos", "name": "MundoInsumos", "status": "ok", "stats": {"total_stock_units": 1000, "product_count": 100}},
        ],
    }

    report = evaluate_build_quality(current, previous, {})

    assert report["should_publish"] is False
    assert any(event["code"] == "provider_stock_drop" and event["source_id"] == "mundoinsumos" for event in report["technical_events"])
    assert any("MundoInsumos" in event["message"] for event in report["business_events"])


def test_write_build_logs_splits_business_and_technical_logs(tmp_path):
    report = {
        "generated_at": "2026-05-15T12:00:00-03:00",
        "status": "blocked",
        "should_publish": False,
        "summary": "Publicacion bloqueada por datos sospechosos.",
        "business_events": [
            {"level": "error", "code": "source_error", "message": "Grupo Senz no respondio."},
        ],
        "technical_events": [
            {"level": "error", "code": "source_error", "source_id": "grupo_senz", "message": "CSV export returned 403"},
        ],
        "last_good_sources": {
            "grupo_senz": {"name": "Grupo Senz", "generated_at": "2026-05-15T09:00:00-03:00", "total_stock_units": 11785},
        },
        "metrics": {"current": {"product_count": 0}, "previous": {"product_count": 346}},
        "checks": [{"name": "source_errors", "status": "failed"}],
    }
    business_path = tmp_path / "business.json"
    technical_path = tmp_path / "technical.json"

    write_build_logs(report, business_path, technical_path)

    business = json.loads(business_path.read_text(encoding="utf-8"))
    technical = json.loads(technical_path.read_text(encoding="utf-8"))
    assert business == {
        "generated_at": "2026-05-15T12:00:00-03:00",
        "status": "blocked",
        "should_publish": False,
        "summary": "Publicacion bloqueada por datos sospechosos.",
        "events": [{"level": "error", "code": "source_error", "message": "Grupo Senz no respondio."}],
        "last_good_sources": {
            "grupo_senz": {"name": "Grupo Senz", "generated_at": "2026-05-15T09:00:00-03:00", "total_stock_units": 11785},
        },
    }
    assert technical["events"][0]["source_id"] == "grupo_senz"
    assert technical["last_good_sources"]["grupo_senz"]["name"] == "Grupo Senz"
    assert technical["checks"] == [{"name": "source_errors", "status": "failed"}]


def test_evaluate_build_quality_logs_enrichment_warnings_without_blocking():
    payload = build_payload(
        [raw("mundoinsumos", "MundoInsumos", "Zona Norte", "GRILON3 PLA Negro 1kg", 10, brand_hint="Grilon3")],
        generated_at="2026-05-15T12:00:00-03:00",
    )

    report = evaluate_build_quality(payload, {}, {}, enrichment_errors={"grilon3_catalog": "read timeout"})

    assert report["should_publish"] is True
    assert any(event["code"] == "enrichment_error" for event in report["technical_events"])
    assert any("imagenes" in event["message"] for event in report["business_events"])


def test_build_grilon3_enrichments_indexes_raw_grilon_products(monkeypatch):
    class CatalogProduct:
        product_url = "https://grilon3.com.ar/producto/pla-negro/"
        image_url = "https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg"

    def fake_fetch_catalog(products_url):
        assert products_url == "https://grilon3.com.ar/productos/"
        return {"pla-negro-175-1000-grilon3": CatalogProduct()}

    monkeypatch.setattr("centraldefilamentos.connectors.grilon3_catalog.fetch_grilon3_catalog", fake_fetch_catalog)

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


def test_build_filamentos3d_enrichments_uses_provider_images_for_3n3_only(monkeypatch):
    monkeypatch.setattr(
        "centraldefilamentos.build_data.load_filamentos3d_metadata",
        lambda: {
            "pla-negro-175-1000-3n3": {
                "provider_product_url": "https://filamentos3d.com.ar/3n3-negro.html",
                "image_url": "assets/filamentos3d/3n3-negro.jpg",
                "sku": "F3D-PLA-NEGRO",
            },
            "pla-negro-175-1000-grilon3": {
                "provider_product_url": "https://filamentos3d.com.ar/grilon-negro.html",
                "image_url": "assets/filamentos3d/grilon-negro.jpg",
            },
        },
    )

    enrichments = build_filamentos3d_enrichments(
        [
            raw("filamentos3d", "Filamentos3D", "Zona Sur", "3N3 Box PLA 1.75mm NEGRO x1KG", 4),
            raw("filamentos3d", "Filamentos3D", "Zona Sur", "GRILON3 PLA Negro 1kg 1.75mm", 4, "Grilon3"),
        ]
    )

    assert enrichments == {
        "pla-negro-175-1000-3n3": {
            "image_url": "assets/filamentos3d/3n3-negro.jpg",
            "image_source": "provider",
            "sku": "F3D-PLA-NEGRO",
        }
    }


def test_build_payload_can_render_3n3_provider_image_without_official_link(monkeypatch):
    monkeypatch.setattr(
        "centraldefilamentos.build_data.load_filamentos3d_metadata",
        lambda: {
            "pla-negro-175-1000-3n3": {
                "provider_product_url": "https://filamentos3d.com.ar/3n3-negro.html",
                "image_url": "assets/filamentos3d/3n3-negro.jpg",
            }
        },
    )

    payload = build_payload(
        [
            raw("filamentos3d", "Filamentos3D", "Zona Sur", "3N3 Box PLA 1.75mm NEGRO x1KG", 4),
        ],
        sources=SOURCES,
        manufacturers=MANUFACTURERS,
        generated_at="2026-05-12T13:00:00-03:00",
        enrichments=build_filamentos3d_enrichments(
            [raw("filamentos3d", "Filamentos3D", "Zona Sur", "3N3 Box PLA 1.75mm NEGRO x1KG", 4)]
        ),
    )

    product = payload["products"][0]
    assert product["image_url"] == "assets/filamentos3d/3n3-negro.jpg"
    assert product["thumbnail_url"] == "assets/thumbs/filamentos3d/3n3-negro.webp"
    assert product["image_source"] == "provider"
    assert product["manufacturer_product_url"] == ""


def test_load_filamentos3d_metadata_reads_provider_cache(tmp_path):
    cache = tmp_path / "filamentos3d_metadata.json"
    cache.write_text(
        '{"pla-negro-175-1000-3n3": {"provider_product_url": "https://filamentos3d.com.ar/3n3-negro.html", "image_url": "assets/filamentos3d/3n3-negro.jpg", "sku": "F3D-PLA-NEGRO"}, "empty": {}}',
        encoding="utf-8",
    )

    assert load_filamentos3d_metadata(cache) == {
        "pla-negro-175-1000-3n3": {
            "provider_product_url": "https://filamentos3d.com.ar/3n3-negro.html",
            "image_url": "assets/filamentos3d/3n3-negro.jpg",
            "sku": "F3D-PLA-NEGRO",
        }
    }


def test_apply_filamentos3d_images_updates_existing_public_payload_without_stock_refresh(tmp_path):
    stock = tmp_path / "stock.json"
    metadata = tmp_path / "filamentos3d_metadata.json"
    stock.write_text(
        json.dumps(
            {
                "products": [
                    {
                        "id": "pla-negro-175-1000-3n3",
                        "brand": "3N3",
                        "image_url": "",
                        "image_source": "",
                        "sku": "",
                        "offers": [{"stock_quantity": 7}],
                    },
                    {
                        "id": "pla-negro-175-1000-grilon3",
                        "brand": "Grilon3",
                        "image_url": "",
                        "image_source": "",
                        "offers": [{"stock_quantity": 9}],
                    },
                    {
                        "id": "pla-bronce-175-1000-3n3",
                        "brand": "3N3",
                        "image_url": "assets/filamentos3d/old-placeholder.jpg",
                        "image_source": "provider",
                        "offers": [{"stock_quantity": 2}],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    metadata.write_text(
        json.dumps(
            {
                "pla-negro-175-1000-3n3": {
                    "image_url": "assets/filamentos3d/3n3-negro.jpg",
                    "sku": "F3D-PLA-NEGRO",
                }
            }
        ),
        encoding="utf-8",
    )

    updated_count = apply_filamentos3d_images(stock, metadata)

    payload = json.loads(stock.read_text(encoding="utf-8"))
    assert updated_count == 2
    assert payload["products"][0]["image_url"] == "assets/filamentos3d/3n3-negro.jpg"
    assert payload["products"][0]["thumbnail_url"] == ""
    assert payload["products"][0]["image_source"] == "provider"
    assert payload["products"][0]["sku"] == "F3D-PLA-NEGRO"
    assert payload["products"][0]["offers"][0]["stock_quantity"] == 7
    assert payload["products"][1]["image_url"] == ""
    assert payload["products"][2]["image_url"] == ""
    assert payload["products"][2]["thumbnail_url"] == ""
    assert payload["products"][2]["image_source"] == ""
    assert payload["products"][2]["offers"][0]["stock_quantity"] == 2


def test_thumbnail_url_for_maps_local_assets_to_webp_thumb_path():
    assert thumbnail_url_for("assets/grilon3/pla-negro.jpg") == "assets/thumbs/grilon3/pla-negro.webp"
    assert thumbnail_url_for("assets/filamentos3d/3n3-negro.png") == "assets/thumbs/filamentos3d/3n3-negro.webp"
    assert thumbnail_url_for("https://example.com/image.jpg") == ""


def test_apply_thumbnails_to_stock_generates_webp_and_updates_payload(tmp_path):
    from PIL import Image

    public_dir = tmp_path / "public"
    asset = public_dir / "assets" / "grilon3" / "pla-negro.jpg"
    stock = public_dir / "data" / "stock.json"
    asset.parent.mkdir(parents=True)
    stock.parent.mkdir(parents=True)
    Image.new("RGB", (640, 480), color="#111111").save(asset)
    stock.write_text(
        json.dumps(
            {
                "products": [
                    {
                        "id": "pla-negro-175-1000-grilon3",
                        "image_url": "assets/grilon3/pla-negro.jpg",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    changes = apply_thumbnails_to_stock(stock, public_dir)

    payload = json.loads(stock.read_text(encoding="utf-8"))
    thumbnail = public_dir / "assets" / "thumbs" / "grilon3" / "pla-negro.webp"
    assert changes == 1
    assert payload["products"][0]["thumbnail_url"] == "assets/thumbs/grilon3/pla-negro.webp"
    assert thumbnail.exists()
    with Image.open(thumbnail) as image:
        assert image.width <= 160
        assert image.height <= 160


def test_build_grilon3_enrichments_uses_local_metadata_cache(monkeypatch):
    monkeypatch.setattr(
        "centraldefilamentos.build_data.load_grilon3_metadata",
        lambda: {"pla-negro-grilon3": {"pantone": "Pantone Black", "sku": "M09INE175CJ", "ean": "7798049653037"}},
    )

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
        ],
        catalog={},
    )

    assert enrichments["pla-negro-175-1000-grilon3"]["pantone"] == "Pantone Black"
    assert enrichments["pla-negro-175-1000-grilon3"]["sku"] == "M09INE175CJ"
    assert enrichments["pla-negro-175-1000-grilon3"]["ean"] == "7798049653037"


def test_build_grilon3_enrichments_prefers_presentation_specific_metadata(monkeypatch):
    monkeypatch.setattr(
        "centraldefilamentos.build_data.load_grilon3_metadata",
        lambda: {
            "pla-azul-grilon3": {
                "image_url": "assets/grilon3/megafill-large-roll.jpg",
                "sku": "SKU-LARGE",
            },
            "pla-azul-175-1000-grilon3": {
                "manufacturer_product_url": "https://grilon3.com.ar/producto/standard-roll/",
                "image_url": "assets/grilon3/standard-roll.jpg",
                "sku": "SKU-STANDARD",
            },
        },
    )

    enrichments = build_grilon3_enrichments(
        [
            raw(
                "filamentos3d",
                "Filamentos3D",
                "Zona Sur",
                "GRILON3 PLA Azul 1kg 1.75mm",
                4,
                brand_hint="Grilon3",
            )
        ],
        catalog={},
    )

    enrichment = next(iter(enrichments.values()))
    assert enrichment["manufacturer_product_url"] == "https://grilon3.com.ar/producto/standard-roll/"
    assert enrichment["image_url"] == "assets/grilon3/standard-roll.jpg"
    assert enrichment["sku"] == "SKU-STANDARD"


def test_build_grilon3_enrichments_uses_unknown_diameter_metadata_before_legacy_megafill(monkeypatch):
    monkeypatch.setattr(
        "centraldefilamentos.build_data.load_grilon3_metadata",
        lambda: {
            "pla-azul-grilon3": {
                "image_url": "assets/grilon3/megafill-large-roll.jpg",
                "sku": "SKU-LARGE",
            },
            "pla-azul-unknown-1000-grilon3": {
                "manufacturer_product_url": "https://grilon3.com.ar/producto/standard-roll/",
                "image_url": "assets/grilon3/standard-roll.jpg",
                "sku": "SKU-STANDARD",
            },
        },
    )

    enrichments = build_grilon3_enrichments(
        [
            raw(
                "filamentos3d",
                "Filamentos3D",
                "Zona Sur",
                "GRILON3 PLA Azul 1kg 1.75mm",
                4,
                brand_hint="Grilon3",
            )
        ],
        catalog={},
    )

    enrichment = next(iter(enrichments.values()))
    assert enrichment["manufacturer_product_url"] == "https://grilon3.com.ar/producto/standard-roll/"
    assert enrichment["image_url"] == "assets/grilon3/standard-roll.jpg"
    assert enrichment["sku"] == "SKU-STANDARD"


def test_build_grilon3_enrichments_does_not_use_megafill_image_for_1kg_product(monkeypatch):
    monkeypatch.setattr(
        "centraldefilamentos.build_data.load_grilon3_metadata",
        lambda: {
            "pla-azul-grilon3": {
                "image_url": "assets/grilon3/megafill-large-roll.jpg",
                "pantone": "Pantone Test",
                "sku": "SKU-LARGE",
            },
        },
    )

    enrichments = build_grilon3_enrichments(
        [
            raw(
                "filamentos3d",
                "Filamentos3D",
                "Zona Sur",
                "GRILON3 PLA Azul 1kg 1.75mm",
                4,
                brand_hint="Grilon3",
            )
        ],
        catalog={},
    )

    enrichment = next(iter(enrichments.values()))
    assert enrichment["pantone"] == "Pantone Test"
    assert "image_url" not in enrichment or enrichment["image_url"] == ""
    assert "sku" not in enrichment or enrichment["sku"] == ""


@pytest.mark.parametrize(
    ("product_name", "cache_key", "wrong_image"),
    [
        (
            "GRILON3 PLA Azul 1kg 1.75mm",
            "pla-azul-grilon3",
            "assets/grilon3/pla-natural-350x350.jpg",
        ),
        (
            "GRILON3 ABS Rojo 1kg 1.75mm",
            "abs-rojo-grilon3",
            "assets/grilon3/abs-natural-350x350.jpg",
        ),
        (
            "GRILON3 PETG Gris Plata 1kg 1.75mm",
            "petg-gris-plata-grilon3",
            "assets/grilon3/petg-blanco-350x350.jpg",
        ),
    ],
)
def test_build_grilon3_enrichments_rejects_cached_image_from_another_color(
    monkeypatch,
    product_name,
    cache_key,
    wrong_image,
):
    monkeypatch.setattr(
        "centraldefilamentos.build_data.load_grilon3_metadata",
        lambda: {
            cache_key: {
                "image_url": wrong_image,
                "pantone": "Pantone Test",
                "sku": "SKU-TEST",
            },
        },
    )

    enrichments = build_grilon3_enrichments(
        [
            raw(
                "filamentos3d",
                "Filamentos3D",
                "Zona Sur",
                product_name,
                4,
                brand_hint="Grilon3",
            )
        ],
        catalog={},
    )

    enrichment = next(iter(enrichments.values()))
    assert enrichment["pantone"] == "Pantone Test"
    assert enrichment["sku"] == "SKU-TEST"
    assert "image_url" not in enrichment or enrichment["image_url"] == ""


def test_build_grilon3_enrichments_does_not_apply_roll_images_to_sampler_products(monkeypatch):
    monkeypatch.setattr(
        "centraldefilamentos.build_data.load_grilon3_metadata",
        lambda: {
            "product-key": {
                "manufacturer_product_url": "https://grilon3.com.ar/producto/standard-roll/",
                "image_url": "assets/grilon3/standard-roll.jpg",
            },
        },
    )

    enrichments = build_grilon3_enrichments(
        [
            raw(
                "filamentos3d",
                "Filamentos3D",
                "Zona Sur",
                "SAMPLER GRILON3 SILK AZUL 1.75 MM X 17 M",
                None,
                brand_hint="Grilon3",
            )
        ],
        catalog={},
    )

    assert enrichments == {}


def test_load_grilon3_metadata_reads_cache_file(tmp_path):
    cache = tmp_path / "metadata.json"
    cache.write_text(
        '{"pla-negro-grilon3": {"manufacturer_product_url": "https://grilon3.com.ar/producto/pla-negro/", "pantone": "Pantone Black", "sku": "M09INE175CJ", "ean": "7798049653037"}, "old": "Pantone Old", "empty": {}}',
        encoding="utf-8",
    )

    assert load_grilon3_metadata(cache) == {
        "pla-negro-grilon3": {
            "manufacturer_product_url": "https://grilon3.com.ar/producto/pla-negro/",
            "pantone": "Pantone Black",
            "sku": "M09INE175CJ",
            "ean": "7798049653037",
        },
        "old": {"pantone": "Pantone Old"},
    }


def test_load_metadata_cache_reads_extended_local_image_metadata(tmp_path):
    cache = tmp_path / "metadata.json"
    cache.write_text(
        '{"product-key": {"image_url": "assets/grilon3/local-product.jpg", "image_remote_url": "https://grilon3.com.ar/product.jpg"}}',
        encoding="utf-8",
    )

    assert load_metadata_cache(cache) == {
        "product-key": {
            "image_url": "assets/grilon3/local-product.jpg",
            "image_remote_url": "https://grilon3.com.ar/product.jpg",
        }
    }


def test_download_grilon3_images_caches_remote_images_locally(tmp_path, monkeypatch):
    calls = []

    class Response:
        content = b"image-bytes"

        def raise_for_status(self):
            calls.append("raise_for_status")

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr("centraldefilamentos.cache_grilon3_metadata.requests.get", fake_get)

    cache = download_grilon3_images(
        {"product-key": {"image_url": "https://grilon3.com.ar/wp-content/uploads/sample-spool.jpg"}},
        assets_dir=tmp_path / "assets",
        image_url_prefix="assets/grilon3",
        timeout_seconds=9,
    )

    image_url = cache["product-key"]["image_url"]
    assert image_url.startswith("assets/grilon3/sample-spool-")
    assert cache["product-key"]["image_remote_url"] == "https://grilon3.com.ar/wp-content/uploads/sample-spool.jpg"
    assert (tmp_path / "assets" / Path(image_url).name).read_bytes() == b"image-bytes"
    assert calls == [("https://grilon3.com.ar/wp-content/uploads/sample-spool.jpg", 9), "raise_for_status"]


def test_build_grilon3_metadata_cache_keeps_duplicate_normalized_titles(monkeypatch):
    shop_catalog = {
        "pla-amarillo-unknown-1000-grilon3": CatalogProduct(
            product_id="pla-amarillo-unknown-1000-grilon3",
            title="PLA Amarillo Grilon3",
            product_url="https://grilon3.com.ar/producto/filamento-3d-pla-amarillo/",
            image_url="https://grilon3.com.ar/wp-content/uploads/pla_amarillo2.jpg",
        ),
        "pla-amarillo-unknown-1000-grilon3-megafill": CatalogProduct(
            product_id="pla-amarillo-unknown-1000-grilon3-megafill",
            title="PLA Amarillo Grilon3",
            product_url="https://grilon3.com.ar/producto/megafill-pla-amarillo/",
            image_url="https://grilon3.com.ar/wp-content/uploads/megafill_amarillo2.jpg",
        ),
    }

    monkeypatch.setattr("centraldefilamentos.cache_grilon3_metadata.fetch_grilon3_catalog", lambda url: shop_catalog)
    monkeypatch.setattr("centraldefilamentos.cache_grilon3_metadata.fetch_grilon3_sitemap_catalog", lambda: {})
    monkeypatch.setattr("centraldefilamentos.cache_grilon3_metadata.enrich_grilon3_catalog_details", lambda catalog, timeout_seconds, max_workers: catalog)

    cache = build_grilon3_metadata_cache()
    urls = {data["manufacturer_product_url"] for data in cache.values()}

    assert urls == {
        "https://grilon3.com.ar/producto/filamento-3d-pla-amarillo/",
        "https://grilon3.com.ar/producto/megafill-pla-amarillo/",
    }


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

    monkeypatch.setattr("centraldefilamentos.connectors.grilon3_catalog.fetch_grilon3_catalog", fake_shop)
    monkeypatch.setattr("centraldefilamentos.connectors.grilon3_catalog.fetch_grilon3_sitemap_catalog", fake_sitemap)
    monkeypatch.setattr("centraldefilamentos.build_data.load_grilon3_metadata", lambda: {})

    catalog = fetch_grilon3_catalog_products()

    assert set(catalog) == {"pla-negro-175-1000-grilon3", "pla-blanco-285-1000-grilon3"}


def test_write_payload_creates_json_file(tmp_path):
    output = tmp_path / "stock.json"
    payload = build_payload([], sources=SOURCES, manufacturers=MANUFACTURERS, generated_at="2026-05-12T13:00:00-03:00")

    write_payload(payload, output)

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["generated_at"] == "2026-05-12T13:00:00-03:00"
    assert written["products"] == []
