from pathlib import Path

from stockcentral.connectors.grilon3_catalog import (
    enrich_with_grilon3_catalog,
    fetch_grilon3_catalog,
    fetch_grilon3_product_detail,
    fetch_grilon3_sitemap_catalog,
    parse_grilon3_catalog,
    parse_grilon3_product_detail,
    parse_grilon3_sitemap,
)
from stockcentral.models import NormalizedFields


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "grilon3_catalog.html"


def fields(
    material: str = "PLA",
    color: str = "Negro",
    brand: str = "Grilon3",
    variant: str = "",
    weight_g: int | None = 1000,
) -> NormalizedFields:
    return NormalizedFields(
        material=material,
        variant=variant,
        color=color,
        diameter_mm=1.75,
        weight_g=weight_g,
        brand=brand,
        manufacturer_name=brand,
    )


def test_parse_grilon3_catalog_indexes_official_links_and_images():
    catalog = parse_grilon3_catalog(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert set(catalog) == {
        "pla-negro-175-1000-grilon3",
        "petg-cristal-175-1000-grilon3",
        "pla-rojo-175-1000-grilon3",
    }
    assert catalog["pla-negro-175-1000-grilon3"].product_url == "https://grilon3.com.ar/producto/pla-negro/"
    assert catalog["pla-negro-175-1000-grilon3"].image_url == "https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg"
    assert catalog["pla-negro-175-1000-grilon3"].pantone == ""
    assert catalog["pla-rojo-175-1000-grilon3"].image_url == ""


def test_enrich_with_grilon3_catalog_matches_only_confident_grilon3_products():
    catalog = parse_grilon3_catalog(FIXTURE_PATH.read_text(encoding="utf-8"))

    enriched = enrich_with_grilon3_catalog(fields(), catalog)
    not_grilon3 = enrich_with_grilon3_catalog(fields(brand="3N3"), catalog)
    unknown = enrich_with_grilon3_catalog(fields(color="Azul"), catalog)

    assert enriched == {
        "manufacturer_product_url": "https://grilon3.com.ar/producto/pla-negro/",
        "image_url": "https://grilon3.com.ar/wp-content/uploads/pla-negro.jpg",
        "image_source": "manufacturer",
        "pantone": "",
        "sku": "",
        "ean": "",
    }
    assert not_grilon3 == {"manufacturer_product_url": "", "image_url": "", "image_source": "", "pantone": "", "sku": "", "ean": ""}
    assert unknown == {"manufacturer_product_url": "", "image_url": "", "image_source": "", "pantone": "", "sku": "", "ean": ""}


def test_parse_grilon3_product_detail_extracts_pantone_and_image():
    html = """
    <html><body>
      <img src="/wp-content/uploads/abs-amarillo.jpg" alt="Filamento Grilon3 ABS">
      <h1>ABS Amarillo</h1>
      <p>SKU: M09IAM175CJ EAN: 7798049653051</p>
      <p>PANTONE Yellow</p>
    </body></html>
    """

    detail = parse_grilon3_product_detail(html, base_url="https://grilon3.com.ar/producto/abs-amarillo/")

    assert detail == {
        "pantone": "Pantone Yellow",
        "image_url": "https://grilon3.com.ar/wp-content/uploads/abs-amarillo.jpg",
        "sku": "M09IAM175CJ",
        "ean": "7798049653051",
    }


def test_parse_grilon3_product_detail_prefers_clean_spool_gallery_image():
    html = """
    <html><body>
      <img src="/wp-content/uploads/logo_grilon3_10.png" alt="Grilon3">
      <img src="/wp-content/uploads/2021/10/astra_calipso4-600x600.jpg" alt="pieza impresa calipso">
      <img src="/wp-content/uploads/2021/10/astra_calipso_web-100x100.jpg"
        srcset="/wp-content/uploads/2021/10/astra_calipso_web-100x100.jpg 100w,
                /wp-content/uploads/2021/10/astra_calipso_web-600x600.jpg 600w"
        alt="Filamento Grilon3 Astra Calipso">
      <img src="/wp-content/uploads/2021/10/astra_calipso2_web-600x600.jpg" alt="Filamento Grilon3 Astra Calipso caja">
      <p>SKU: M10ICA175CJ EAN: 7798049653000</p>
    </body></html>
    """

    detail = parse_grilon3_product_detail(html, base_url="https://grilon3.com.ar/producto/pla-astra-calipso/")

    assert detail["image_url"] == "https://grilon3.com.ar/wp-content/uploads/2021/10/astra_calipso_web-600x600.jpg"


def test_parse_grilon3_product_detail_prefers_angle_spool_when_no_web_image():
    html = """
    <html><body>
      <img src="/wp-content/uploads/2020/09/pla_850_turquesa-600x600.jpg" alt="PLA 850 Grilon3 caja">
      <img src="/wp-content/uploads/2020/09/pla_850_turquesa3-600x600.jpg" alt="PLA 850 Grilon3 frontal">
      <img src="/wp-content/uploads/2020/09/pla_850_turquesa2-600x600.jpg" alt="PLA 850 Grilon3">
      <p>SKU: M11ITU175CJ EAN: 7798049653440</p>
    </body></html>
    """

    detail = parse_grilon3_product_detail(html, base_url="https://grilon3.com.ar/producto/filamento-3d-pla-turquesa-2/")

    assert detail["image_url"] == "https://grilon3.com.ar/wp-content/uploads/2020/09/pla_850_turquesa2-600x600.jpg"


def test_fetch_grilon3_product_detail_downloads_product_page(monkeypatch):
    calls = []

    class Response:
        text = "<html><body><p>SKU: M09IAM175CJ EAN: 7798049653051</p><p>PANTONE Yellow</p></body></html>"

        def raise_for_status(self):
            calls.append("raise_for_status")

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr("stockcentral.connectors.grilon3_catalog.requests.get", fake_get)

    detail = fetch_grilon3_product_detail("https://grilon3.com.ar/producto/abs-amarillo/", timeout_seconds=7)

    assert calls == [("https://grilon3.com.ar/producto/abs-amarillo/", 7), "raise_for_status"]
    assert detail["pantone"] == "Pantone Yellow"
    assert detail["sku"] == "M09IAM175CJ"
    assert detail["ean"] == "7798049653051"


def test_fetch_grilon3_catalog_downloads_products_url(monkeypatch):
    fixture_html = FIXTURE_PATH.read_text(encoding="utf-8")
    calls = []

    class Response:
        text = fixture_html

        def raise_for_status(self):
            calls.append("raise_for_status")

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr("stockcentral.connectors.grilon3_catalog.requests.get", fake_get)

    catalog = fetch_grilon3_catalog("https://grilon3.com.ar/productos/", timeout_seconds=8)

    assert calls == [("https://grilon3.com.ar/productos/", 8), "raise_for_status"]
    assert "pla-negro-175-1000-grilon3" in catalog


def test_parse_grilon3_sitemap_adds_285_catalog_products():
    xml = """
    <urlset>
      <url><loc>https://grilon3.com.ar/producto/pla-blanco-285/</loc></url>
      <url><loc>https://grilon3.com.ar/producto/petg-negro-285/</loc></url>
      <url><loc>https://grilon3.com.ar/no-producto/pla/</loc></url>
    </urlset>
    """

    catalog = parse_grilon3_sitemap(xml)

    assert catalog["pla-blanco-285-1000-grilon3"].title == "PLA Blanco Grilon3 1 kg 2.85 mm"
    assert catalog["pla-blanco-285-1000-grilon3"].product_url == "https://grilon3.com.ar/producto/pla-blanco-285/"
    assert catalog["petg-negro-285-1000-grilon3"].title == "PETG Negro Grilon3 1 kg 2.85 mm"


def test_fetch_grilon3_sitemap_catalog_downloads_sitemap(monkeypatch):
    calls = []

    class Response:
        text = "<urlset><url><loc>https://grilon3.com.ar/producto/pla-blanco-285/</loc></url></urlset>"

        def raise_for_status(self):
            calls.append("raise_for_status")

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return Response()

    monkeypatch.setattr("stockcentral.connectors.grilon3_catalog.requests.get", fake_get)

    catalog = fetch_grilon3_sitemap_catalog("https://grilon3.com.ar/product-sitemap.xml", timeout_seconds=9)

    assert calls == [("https://grilon3.com.ar/product-sitemap.xml", 9), "raise_for_status"]
    assert "pla-blanco-285-1000-grilon3" in catalog
