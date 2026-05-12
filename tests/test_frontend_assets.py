from pathlib import Path


PUBLIC = Path("public")


def test_static_frontend_files_exist_and_are_linked():
    index = (PUBLIC / "index.html").read_text(encoding="utf-8")
    resumen = (PUBLIC / "resumen.html").read_text(encoding="utf-8")

    assert '<script src="app.js" defer></script>' in index
    assert 'href="styles.css"' in index
    assert 'href="resumen.html"' in index
    assert '<script src="resumen.js" defer></script>' in resumen
    assert 'id="summary-table"' in resumen


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
    assert "encodeURIComponent" in js


def test_summary_script_uses_carretes_totals_and_provider_order():
    js = (PUBLIC / "resumen.js").read_text(encoding="utf-8")

    assert 'fetch("data/stock.json")' in js
    assert "Zona Norte" in js
    assert "Zona Oeste" in js
    assert "Zona Sur" in js
    assert "Carretes por proveedor" in js
    assert "total_stock_units" in js
    assert "total_stock_kg" not in js


def test_styles_are_compact_and_responsive():
    css = (PUBLIC / "styles.css").read_text(encoding="utf-8")

    assert "@media" in css
    assert "position: sticky" in css
    assert "grid-template-columns" in css
    assert "border-radius: 8px" in css
