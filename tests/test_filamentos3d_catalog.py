from pathlib import Path

from stockcentral.cache_filamentos3d_metadata import download_filamentos3d_images
from stockcentral.connectors.filamentos3d_catalog import (
    ProviderCatalogProduct,
    parse_filamentos3d_category,
    parse_filamentos3d_product_detail,
)


def test_parse_filamentos3d_category_extracts_product_links_and_ids():
    html = """
    <section id="products">
      <article class="product-miniature">
        <a class="product-thumbnail" href="https://filamentos3d.com.ar/pla-3n3-175mm-1kg/3n3-box-pla-175mm-negro-x1kg-182.html">
          <img alt="3N3 Box PLA 1.75mm NEGRO x1KG" src="https://filamentos3d.com.ar/1482-home_default/3n3-box-pla-175mm-negro-x1kg.jpg">
        </a>
        <h2><a href="https://filamentos3d.com.ar/pla-3n3-175mm-1kg/3n3-box-pla-175mm-negro-x1kg-182.html">3N3 Box PLA 1.75mm NEGRO x1KG</a></h2>
      </article>
      <article class="product-miniature">
        <a href="/3nmax-pla/3nmax-pla-plus-rojo-175mm-x750g-301.html">3NMAX PLA+ ROJO 1.75mm x750g</a>
      </article>
    </section>
    """

    products = parse_filamentos3d_category(html, "https://filamentos3d.com.ar/43-pla-3n3-175mm-1kg", "3n3-pla")

    assert [product.product_id for product in products] == [
        "pla-negro-175-1000-3n3",
        "pla-plaplus-rojo-175-750-3n3",
    ]
    assert products[0].line_code == "3n3-pla"
    assert products[0].image_url == "https://filamentos3d.com.ar/1482-home_default/3n3-box-pla-175mm-negro-x1kg.jpg"
    assert products[1].product_url == "https://filamentos3d.com.ar/3nmax-pla/3nmax-pla-plus-rojo-175mm-x750g-301.html"


def test_parse_filamentos3d_product_detail_prefers_main_image_and_ignores_related_products():
    html = """
    <main>
      <h1>3N3 Box PLA 1.75mm NEGRO x1KG</h1>
      <section class="product-cover">
        <img class="img-fluid w-100 js-qv-product-cover"
             alt="3N3 Box PLA 1.75mm NEGRO x1KG"
             src="https://filamentos3d.com.ar/1482-product_main/3n3-box-pla-175mm-negro-x1kg.jpg"
             srcset="https://filamentos3d.com.ar/1482-default_xl/3n3-box-pla-175mm-negro-x1kg.jpg 400w, https://filamentos3d.com.ar/1482-product_main/3n3-box-pla-175mm-negro-x1kg.jpg 720w, https://filamentos3d.com.ar/1482-product_main_2x/3n3-box-pla-175mm-negro-x1kg.jpg 1440w">
      </section>
      <section class="featured-products">
        <img class="product-miniature__image" src="https://filamentos3d.com.ar/999-product_main/related-product.jpg" alt="Relacionado">
      </section>
      <span class="product-reference">SKU: F3D-PLA-NEGRO</span>
    </main>
    """

    detail = parse_filamentos3d_product_detail(html, "https://filamentos3d.com.ar/producto.html")

    assert detail["title"] == "3N3 Box PLA 1.75mm NEGRO x1KG"
    assert detail["sku"] == "F3D-PLA-NEGRO"
    assert detail["image_url"] == "https://filamentos3d.com.ar/1482-product_main_2x/3n3-box-pla-175mm-negro-x1kg.jpg"


def test_parse_filamentos3d_category_maps_3n3_lines_without_mixing_flexible_or_epet():
    html = """
    <article><a href="/66-3nflex-pla-175mm/3nflex-pla-plus-azul-175mm-x1kg.html">3NFLEX PLA+ AZUL 1.75mm x1kg</a></article>
    <article><a href="/40-3n3-epet-175mm/3n3-epet-cristal-175mm-x1kg.html">3N3 EPET CRISTAL 1.75mm x1kg</a></article>
    <article><a href="/48-3n3-petg-175mm/3n3-petg-negro-175mm-x1kg.html">3N3 PETG NEGRO 1.75mm x1kg</a></article>
    """

    products = parse_filamentos3d_category(html, "https://filamentos3d.com.ar/66-3nflex-pla-175mm", "mixed")

    assert [product.product_id for product in products] == [
        "pla-pla-flexible-azul-175-1000-3n3",
        "pet-e-pet-cristal-175-1000-3n3",
        "petg-negro-175-1000-3n3",
    ]


def test_parse_filamentos3d_category_uses_3nflex_category_weight_when_title_omits_it():
    html = """
    <article class="product-miniature">
      <a href="/66-3nflex-pla-175mm/3nflex-pla-plus-negro-175mm.html">3NFLEX PLA+ NEGRO 1.75mm</a>
    </article>
    """

    products = parse_filamentos3d_category(html, "https://filamentos3d.com.ar/66-3nflex-pla-175mm", "3nflex-pla-plus")

    assert products[0].product_id == "pla-pla-flexible-negro-175-1000-3n3"


def test_parse_filamentos3d_category_ignores_category_links_and_placeholder_images():
    html = """
    <article class="product-miniature">
      <a href="/43-pla-3n3-175mm-1kg">PLA 3N3 1KG</a>
      <img src="https://filamentos3d.com.ar/img/logo-16883932851.jpg" alt="3N3 PLA">
    </article>
    <article class="product-miniature">
      <a href="/pla-3n3-175mm-1kg/3n3-box-pla-175mm-verde-x1kg-180.html">3N3 Box PLA 1.75mm VERDE x1KG</a>
      <img src="https://filamentos3d.com.ar/img/p/es-default-default_xl.jpg" alt="3N3 Box PLA 1.75mm VERDE x1KG">
      <img src="https://filamentos3d.com.ar/modules/whatsappbutton/views/img/whatsapp-icon.svg" alt="WhatsApp">
    </article>
    """

    products = parse_filamentos3d_category(html, "https://filamentos3d.com.ar/43-pla-3n3-175mm-1kg", "3n3-pla")

    assert len(products) == 1
    assert products[0].product_id == "pla-verde-175-1000-3n3"
    assert products[0].image_url == ""


def test_download_filamentos3d_images_caches_provider_images_locally(tmp_path, monkeypatch):
    calls = []

    class Response:
        content = b"image-bytes"

        def raise_for_status(self):
            calls.append("raise_for_status")

    def fake_get(url, timeout, follow_redirects=True):
        calls.append((url, timeout, follow_redirects))
        return Response()

    monkeypatch.setattr("stockcentral.cache_filamentos3d_metadata.httpx.get", fake_get)

    cache = download_filamentos3d_images(
        {
            "pla-negro-175-1000-3n3": {
                "provider_product_url": "https://filamentos3d.com.ar/producto.html",
                "image_url": "https://filamentos3d.com.ar/1482-product_main_2x/3n3-box-pla-175mm-negro-x1kg.jpg",
            }
        },
        assets_dir=tmp_path / "assets",
        image_url_prefix="assets/filamentos3d",
        timeout_seconds=9,
    )

    image_url = cache["pla-negro-175-1000-3n3"]["image_url"]
    assert image_url.startswith("assets/filamentos3d/3n3-box-pla-175mm-negro-x1kg-")
    assert cache["pla-negro-175-1000-3n3"]["image_remote_url"] == "https://filamentos3d.com.ar/1482-product_main_2x/3n3-box-pla-175mm-negro-x1kg.jpg"
    assert (tmp_path / "assets" / Path(image_url).name).read_bytes() == b"image-bytes"
    assert calls == [
        ("https://filamentos3d.com.ar/1482-product_main_2x/3n3-box-pla-175mm-negro-x1kg.jpg", 9, True),
        "raise_for_status",
    ]
