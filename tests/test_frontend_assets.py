import json
from collections import Counter
from pathlib import Path


PUBLIC = Path("public")
SRC = Path("src")


def test_static_frontend_files_exist_and_are_linked():
    index = Path("index.html").read_text(encoding="utf-8")
    resumen = Path("resumen.html").read_text(encoding="utf-8")
    internal = Path("estadisticas.html").read_text(encoding="utf-8")
    flags = json.loads((PUBLIC / "data" / "feature_flags.json").read_text(encoding="utf-8"))
    catalog_view = (SRC / "CatalogApp.svelte").read_text(encoding="utf-8")
    site_header = (SRC / "components" / "SiteHeader.svelte").read_text(encoding="utf-8")

    assert 'type="module" src="/src/catalog.js"' in index
    assert 'href: "resumen.html"' in site_header
    assert 'href: "index.html#site-footer"' in site_header
    assert "provider-status" in site_header
    assert "brand-mark" in site_header
    assert "SiteHeader" in catalog_view
    assert 'type="module" src="/src/summary.js"' in resumen
    assert 'id="merge-brands-toggle"' not in resumen
    assert "Fusionar Grilon3 + 3N3" not in resumen
    assert "estadisticas.html" not in index
    assert "estadisticas.html" not in resumen
    assert "vendedores-interno.html" not in index
    assert "vendedores-interno.html" not in resumen
    assert 'type="module" src="/src/vendor-stats.js"' in internal
    assert 'noindex,nofollow' in internal
    assert flags["vendorStatsEnabled"] is True
    for entry in ["catalog.js", "summary.js", "vendor-stats.js"]:
        js = (SRC / entry).read_text(encoding="utf-8")
        assert 'import { mount } from "svelte"' in js
        assert "mount(" in js
        assert "new " not in js


def test_catalog_svelte_fetches_json_and_supports_required_filters():
    view = (SRC / "CatalogApp.svelte").read_text(encoding="utf-8")
    shared = (SRC / "lib" / "shared.js").read_text(encoding="utf-8")
    footer = (SRC / "components" / "SiteFooter.svelte").read_text(encoding="utf-8")
    quick_lines = (SRC / "components" / "QuickLines.svelte").read_text(encoding="utf-8")
    js = view + shared + footer + quick_lines

    assert "data/stock.json" in js
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
    assert "PLA Flexible" in js
    assert "brillo tipo glitter" in js
    assert "E-PET - PET reciclado" in js
    assert "PP-T - polipropileno" in js
    assert "Sampler / lápiz 3D" in js
    assert "isSamplerProduct" in js
    assert "formatPresentation" in js
    assert "samplerLengthLabel" in js
    assert "groupBaseProducts" in js
    assert "official-product-link" in js
    assert "Página oficial" in js
    assert "data-preview-src" in js
    assert "thumbnail_url" in js
    assert 'loading="lazy"' in js
    assert 'decoding="async"' in js
    assert "image-preview" in js
    assert "compareImagePresentations" in js
    assert "imagePresentationRank" in js
    assert ".filter((item) => item.image_url)" in js
    assert "Number(product.weight_g) === 1000" in js
    assert "Number(product.weight_g) === 2500" in js
    assert "pantoneSwatchLabel" in js
    assert "colorSwatchStyle" in js
    assert "baseColorFor" in js
    assert "foldText" in js
    assert "matchesSearchTerms" in js
    assert "setFilter" in js
    assert "filters, categoryOrder, products.filter" in js
    assert "materialOptions = (products, valuesFor" in js
    assert "providerOptions = (products, providerValues" in js
    assert "matchesSearchToken" in js
    assert "searchTokens" in js
    assert 'term === "pla"' in js
    assert 'token === "pla+"' in js
    assert "token.startsWith(term)" in js
    assert "queryText.includes" not in js
    assert "presentation-row" in js
    assert "productBaseName" in js
    assert "quickLineValues" in js
    assert "visibleLines" in js
    assert "products, lineValues()" in js
    assert "quickLabel" in js
    assert "quickTone" in js
    assert '"ABS"' in js
    assert '"PLA Boutique"' in js
    assert '"Nylon 6"' in js
    assert "PLA Wood" in js
    assert "categoryOrder" in js
    assert "compareGroups" in js
    assert "compareProductGroups" in js
    assert "scrollIntoView" in js
    assert "quick-target" in js
    assert "groupTargetId" in js
    assert "slugText" in js
    assert "state.filters.variant = button.dataset.line" not in js
    assert "sin stock online registrado" in js
    assert "offer-main" in js
    assert "providerTitle" in js
    assert "Sin cantidad" in js
    assert "0*" not in js
    assert "El proveedor seguramente no maneja esta variante." not in js
    assert "providerAnchorId" in js
    assert "proveedor-" in js
    assert "sourceWhatsappUrl" in js
    assert "contactContext" in js
    assert "stockDelta" in js
    assert "stock_delta_units" in js
    assert "vs ayer" in js
    assert "Creado por Gabriel" in js
    assert "Reportar error" in js
    assert "Sumar proveedor" in js
    assert "https://github.com/Zogar89/CentraldeFilamentos/issues/new" in js
    assert "encodeURIComponent" in js
    assert "Rev." not in js
    assert "whatsappLink" not in js
    assert 'class="chips"' not in js
    assert "function chip" not in js
    assert "<span>${escapeHtml(offer.provider_zone)}</span>" not in js
    assert "product.pantone ? chip(product.pantone)" not in js


def test_summary_svelte_uses_carretes_totals_and_provider_order():
    view = (SRC / "SummaryApp.svelte").read_text(encoding="utf-8")
    shared = (SRC / "lib" / "shared.js").read_text(encoding="utf-8")
    footer = (SRC / "components" / "SiteFooter.svelte").read_text(encoding="utf-8")
    quick_lines = (SRC / "components" / "QuickLines.svelte").read_text(encoding="utf-8")
    js = view + shared + footer + quick_lines

    assert "data/stock.json" in js
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
    assert "summary-product" in js
    assert "summary-color-swatch" in js
    assert "colorSwatchStyle" in js
    assert "row.product.pantone" in js
    assert "mergeBrands" not in js
    assert "mergeCompatibleBrands" not in js
    assert "mergeRowKey" not in js
    assert "mergedBrandKey" not in js
    assert "brandsLabel" not in js
    assert "Grilon3 + 3N3" not in js
    assert "matchesSearchTerms" in js
    assert "query, rows.filter" in js
    assert "matchesSearchToken" in js
    assert "searchTokens" in js
    assert 'term === "pla"' in js
    assert 'token === "pla+"' in js
    assert "token.startsWith(term)" in js
    assert "summary-group-row" in js
    assert "quickLineValues" in js
    assert '"ABS"' in js
    assert '"PLA Boutique"' in js
    assert '"Nylon 6"' in js
    assert "summaryGroupTargetId" in js
    assert "updateStickyGroupRows" not in js
    assert "summaryStickyTop" not in js
    assert "is-stuck" not in js
    assert "footer-grid" in js
    assert "sourceWhatsappUrl" in js
    assert "contactContext" in js
    assert "Creado por Gabriel" in js
    assert "Reportar error" in js
    assert "Sumar proveedor" in js
    assert "https://github.com/Zogar89/CentraldeFilamentos/issues/new" in js
    assert "slugText" in js
    assert "groupRows" in js
    assert "0*" not in js
    assert "El proveedor seguramente no maneja esta variante" not in js
    assert "A revisar" not in js
    assert "Rev." not in js
    assert "total_stock_units" in js
    assert "stockDelta" in js
    assert "stock_delta_units" in js
    assert "vs ayer" in js
    assert "const stockDelta = stockDeltaTemplate(source.stats || {});" not in js
    assert "total_stock_kg" not in js


def test_internal_vendor_svelte_uses_feature_flag_and_30_day_history():
    js = (SRC / "VendorStatsApp.svelte").read_text(encoding="utf-8") + (SRC / "lib" / "shared.js").read_text(encoding="utf-8")

    assert "data/feature_flags.json" in js
    assert "data/provider_stock_history.json" in js
    assert "data/build_business_log.json" in js
    assert "noCache" in js
    assert "cache: options.noCache ? \"no-store\" : \"default\"" in js
    assert "url.searchParams.set(\"v\"" in js
    assert "vendorStatsEnabled" in js
    assert "build-health" in js
    assert "last_good_sources" in js
    assert "slice(-30)" in js
    assert "stockSeriesForProvider" in js
    assert "stockChartForProvider" in js
    assert "vendor-stock-chart" in js
    assert "Evolucion 30d" in js
    assert "chart-line" in js
    assert "chart-point" in js
    assert "deltaForProvider" in js
    assert "vs dia anterior" in js
    assert "checksForDay" in js
    assert "details" in js
    assert "Chequeos del dia" in js
    assert "vs 09:00" in js
    assert "intraday-list" in js
    assert "intraday-row" in js
    assert "America/Argentina/Buenos_Aires" in js
    assert "vendor-dashboard" in js
    assert "vendor-disabled" in js
    assert "Cantidad por dia" in js
    assert "Variacion" in js


def test_styles_are_compact_and_responsive():
    css = (SRC / "styles" / "global.css").read_text(encoding="utf-8")

    assert "@media" in css
    assert "position: sticky" in css
    assert "grid-template-columns" in css
    assert "border-radius: 8px" in css
    assert ".group-section" in css
    assert ".group-section.quick-target" in css
    assert ".group-heading" in css
    assert ".quick-line::before" in css
    assert ".quick-lines-shell" in css
    assert ".quick-line-abs" in css
    assert ".quick-line-boutique" in css
    assert ".quick-line-wood" in css
    assert ".quick-line-nylon" in css
    assert "flex-wrap: nowrap" in css
    assert "scroll-snap-type: x proximity" in css
    assert "-webkit-overflow-scrolling: touch" in css
    assert "scrollbar-width: none" in css
    assert "top: var(--quick-lines-height)" in css
    assert "scroll-margin-top" in css
    assert "repeat(auto-fit, minmax(320px, 1fr))" in css
    assert ".offer-main" in css
    assert ".presentation-list" in css
    assert ".presentation-row" in css
    assert ".chips" not in css
    assert ".chip" not in css
    assert ".product-visuals" in css
    assert ".media-presentation" in css
    assert ".color-swatch" in css
    assert ".swatch-pantone" in css
    assert ".product-media" in css
    assert ".official-product-link" in css
    assert ".image-preview" in css
    assert ".image-preview.visible" in css
    assert "cursor: zoom-in" in css
    assert "scroll-behavior: smooth" in css
    assert ".footer-provider:target" in css
    assert ".stock-delta" in css
    assert ".stock-delta-up" in css
    assert ".stock-delta-down" in css
    assert ".footer-meta" in css
    assert ".summary-presentation" in css
    assert ".summary-product" in css
    assert ".summary-color-swatch" in css
    assert ".summary-product-name" in css
    assert ".category-sort" in css
    assert ".soft-button.active" in css
    assert ".summary-group-row" in css
    assert ".summary-group-row.quick-target" in css
    assert ".summary-group-row.is-stuck td" not in css
    assert "color: transparent" not in css
    assert "top: calc(var(--quick-lines-height) + var(--summary-head-height))" in css
    assert ".summary-table tbody .summary-group-row th" in css
    assert ".internal-shell" in css
    assert ".build-health" in css
    assert ".build-health-events" in css
    assert ".vendor-stat-grid" in css
    assert ".vendor-stock-chart" in css
    assert ".chart-line" in css
    assert ".chart-area" in css
    assert ".chart-point" in css
    assert ".vendor-history-table" in css
    assert ".intraday-checks" in css
    assert ".intraday-panel" in css
    assert ".intraday-list" in css
    assert ".intraday-row" in css
    assert ".delta-positive" in css
    assert ".delta-negative" in css


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


def test_generated_stock_data_keeps_presentation_specific_images():
    payload = json.loads((PUBLIC / "data" / "stock.json").read_text(encoding="utf-8"))
    groups = {}
    for product in payload["products"]:
        if product["brand"] != "Grilon3" or not product["image_url"]:
            continue
        key = (
            product["material"],
            product["variant"],
            product["color"],
            product["brand"],
            product["diameter_mm"],
        )
        groups.setdefault(key, []).append(product)

    presentation_groups = [
        products
        for products in groups.values()
        if len({product["weight_g"] for product in products}) > 1
        and len({product["image_url"] for product in products}) > 1
    ]

    checked_groups = 0
    assert presentation_groups
    for products in presentation_groups:
        one_kg = [product for product in products if product["weight_g"] == 1000]
        larger = [product for product in products if product["weight_g"] and product["weight_g"] > 1000]
        if not one_kg or not larger:
            continue

        one_kg_image = one_kg[0]["image_url"]
        larger_images = {product["image_url"] for product in larger}
        checked_groups += 1
        assert one_kg_image not in larger_images
    assert checked_groups > 0


def test_generated_stock_data_does_not_use_large_spool_images_for_1kg_products():
    payload = json.loads((PUBLIC / "data" / "stock.json").read_text(encoding="utf-8"))
    large_markers = ("megafill", "maxicarrete")
    mismatches = [
        (product["id"], product["image_url"])
        for product in payload["products"]
        if product.get("weight_g") == 1000
        and any(marker in product.get("image_url", "").lower() for marker in large_markers)
    ]

    assert mismatches == []


def test_generated_stock_data_keeps_sampler_products_without_roll_images():
    payload = json.loads((PUBLIC / "data" / "stock.json").read_text(encoding="utf-8"))
    sampler_products = [
        product
        for product in payload["products"]
        if any(
            "SAMPLER" in offer["original_name"].upper()
            or "LAPIZ 3D" in offer["original_name"].upper()
            or "LÁPIZ 3D" in offer["original_name"].upper()
            for offer in product["offers"]
        )
    ]

    assert sampler_products
    assert [product["image_url"] for product in sampler_products if product["image_url"]] == []
    assert [product["manufacturer_product_url"] for product in sampler_products if product["manufacturer_product_url"]] == []


def test_generated_stock_data_has_official_metadata_for_technical_grilon3_lines():
    payload = json.loads((PUBLIC / "data" / "stock.json").read_text(encoding="utf-8"))
    technical_products = [
        product
        for product in payload["products"]
        if product["brand"] == "Grilon3"
        and product["variant"] in {"PP-T", "Acetal-POM"}
        and product["weight_g"] == 1000
    ]
    urls = [product["manufacturer_product_url"] for product in technical_products if product["manufacturer_product_url"]]
    non_manufacturer_images = [
        product["id"]
        for product in technical_products
        if product["image_url"] and product["image_source"] != "manufacturer"
    ]

    assert technical_products
    assert all(url.startswith("https://grilon3.com.ar/") for url in urls)
    assert any("/producto/" in url for url in urls)
    assert any("/categoria-producto/tecnicos/" in url for url in urls)
    assert non_manufacturer_images == []


def test_generated_stock_data_uses_local_thumbnails_for_local_images():
    payload = json.loads((PUBLIC / "data" / "stock.json").read_text(encoding="utf-8"))
    products_with_images = [
        product
        for product in payload["products"]
        if product.get("image_url", "").startswith("assets/")
    ]
    missing_or_broken = []

    assert products_with_images
    for product in products_with_images:
        thumbnail_url = product.get("thumbnail_url", "")
        thumbnail_path = PUBLIC / thumbnail_url
        if (
            not thumbnail_url.startswith("assets/thumbs/")
            or thumbnail_url == product["image_url"]
            or not thumbnail_path.exists()
            or thumbnail_path.suffix != ".webp"
        ):
            missing_or_broken.append((product["id"], product["image_url"], thumbnail_url))

    assert missing_or_broken == []
