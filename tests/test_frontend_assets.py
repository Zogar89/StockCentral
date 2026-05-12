import json
from collections import Counter
from pathlib import Path


PUBLIC = Path("public")


def test_static_frontend_files_exist_and_are_linked():
    index = (PUBLIC / "index.html").read_text(encoding="utf-8")
    resumen = (PUBLIC / "resumen.html").read_text(encoding="utf-8")

    assert '<script src="app.js" defer></script>' in index
    assert 'href="styles.css"' in index
    assert 'href="resumen.html"' in index
    assert 'id="quick-lines"' in index
    assert 'id="line-help"' in index
    assert "0* indica que el proveedor seguramente no maneja esa variante." in index
    assert '<script src="resumen.js" defer></script>' in resumen
    assert 'id="summary-table"' in resumen
    assert "0* indica que el proveedor seguramente no maneja esa variante." in resumen


def test_catalog_script_fetches_json_and_supports_required_filters():
    js = (PUBLIC / "app.js").read_text(encoding="utf-8")

    assert 'fetch("data/stock.json")' in js
    for filter_id in [
        "material-filter",
        "variant-filter",
        "color-filter",
        "diameter-filter",
        "weight-filter",
        "brand-filter",
        "provider-filter",
        "stock-filter",
    ]:
        assert filter_id in js
    assert "contact_whatsapp_url" in js
    assert "groupProducts" in js
    assert "group-section" in js
    assert "product.pantone" in js
    assert "product.sku" in js
    assert "product.ean" in js
    assert "PLA Standard" in js
    assert "glitter/brillitos" in js
    assert "E-PET · PET reciclado" in js
    assert "PP-T · polipropileno" in js
    assert "Sampler / lápiz 3D" in js
    assert "isSamplerProduct" in js
    assert "formatPresentation" in js
    assert "samplerLengthLabel" in js
    assert "groupBaseProducts" in js
    assert "productCardTemplate" in js
    assert "cardImageProduct" in js
    assert "product.weight_g === 1000 && product.image_url" in js
    assert "colorSwatchTemplate" in js
    assert "colorSwatchStyle" in js
    assert "baseColorFor" in js
    assert "foldText" in js
    assert "presentationTemplate" in js
    assert "productBaseName" in js
    assert "quickLineValues" in js
    assert "sin stock online registrado" in js
    assert "offer-main" in js
    assert "Sin cantidad" in js
    assert "0*" in js
    assert "El proveedor seguramente no maneja esta variante." in js
    assert "providerAnchorId" in js
    assert "proveedor-" in js
    assert "sourceWhatsappUrl" in js
    assert "whatsappMessage" in js
    assert "contactContext" in js
    assert "encodeURIComponent" in js
    assert "Rev." not in js
    assert "whatsappLink" not in js


def test_summary_script_uses_carretes_totals_and_provider_order():
    js = (PUBLIC / "resumen.js").read_text(encoding="utf-8")

    assert 'fetch("data/stock.json")' in js
    assert "Zona Norte" in js
    assert "Zona Oeste" in js
    assert "Zona Sur" in js
    assert "Carretes por proveedor" in js
    assert "summary-presentation" in js
    assert "formatWeightLabel" in js
    assert "formatPresentation" in js
    assert "samplerLengthLabel" in js
    assert "isSamplerProduct" in js
    assert "productSummaryName" in js
    assert "summary-group-row" in js
    assert "groupRows" in js
    assert "0*" in js
    assert "El proveedor seguramente no maneja esta variante" in js
    assert "A revisar" not in js
    assert "Rev." not in js
    assert "total_stock_units" in js
    assert "total_stock_kg" not in js


def test_styles_are_compact_and_responsive():
    css = (PUBLIC / "styles.css").read_text(encoding="utf-8")

    assert "@media" in css
    assert "position: sticky" in css
    assert "grid-template-columns" in css
    assert "border-radius: 8px" in css
    assert ".group-section" in css
    assert "repeat(auto-fit, minmax(320px, 1fr))" in css
    assert ".offer-main" in css
    assert ".presentation-list" in css
    assert ".presentation-row" in css
    assert ".color-swatch" in css
    assert ".review-reason" in css
    assert "scroll-behavior: smooth" in css
    assert ".footer-provider:target" in css
    assert ".summary-presentation" in css
    assert ".summary-group-row" in css
    assert ".stock-note" in css


def test_generated_stock_data_has_one_offer_per_provider_per_card():
    payload = json.loads((PUBLIC / "data" / "stock.json").read_text(encoding="utf-8"))

    for product in payload["products"]:
        provider_counts = Counter(offer["provider_name"] for offer in product["offers"])
        repeated_providers = [provider for provider, count in provider_counts.items() if count > 1]

        assert repeated_providers == [], product["display_name"]


def test_generated_stock_data_has_no_stocked_products_without_color():
    payload = json.loads((PUBLIC / "data" / "stock.json").read_text(encoding="utf-8"))
    stocked_without_color = [
        product["display_name"]
        for product in payload["products"]
        if product["color"] == "Sin color" and product["offers"]
    ]

    assert stocked_without_color == []
