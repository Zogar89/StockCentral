from stockcentral.models import Offer, ProductGroup, ProviderStats, SourceStatus


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
        thumbnail_url="assets/thumbs/grilon3/pla-negro.webp",
        image_source="manufacturer",
        pantone="Pantone Black 6 C",
        sku="M09INE175CJ",
        ean="7798049653037",
        display_name="PLA Negro Grilon3 1 kg",
        offers=[offer],
    )

    payload = product.to_dict()

    assert payload["id"] == "pla-negro-175-1000-grilon3"
    assert payload["material"] == "PLA"
    assert payload["offers"][0]["provider_zone"] == "Zona Sur"
    assert payload["offers"][0]["stock_status"] == "in_stock"
    assert payload["manufacturer_product_url"].startswith("https://grilon3.com.ar/")
    assert payload["thumbnail_url"] == "assets/thumbs/grilon3/pla-negro.webp"
    assert payload["image_source"] == "manufacturer"
    assert payload["pantone"] == "Pantone Black 6 C"
    assert payload["sku"] == "M09INE175CJ"
    assert payload["ean"] == "7798049653037"


def test_source_status_serializes_error_message():
    source = SourceStatus(
        id="grupo_senz",
        name="Grupo Senz",
        zone="Zona Oeste",
        homepage_url="https://docs.google.com/spreadsheets/d/14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM",
        source_url="https://docs.google.com/spreadsheets/d/14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM",
        contact_whatsapp_url="https://wa.me/5491112345678",
        contact_phone="+54 9 11 1234-5678",
        contact_email="ventas@example.com",
        address="Moron, Buenos Aires",
        contact_url="https://example.com/contacto",
        last_success_at="2026-05-12T12:00:00-03:00",
        last_attempt_at="2026-05-12T15:00:00-03:00",
        status="error",
        error_message="CSV export returned 403",
        stats=ProviderStats(
            total_stock_units=12,
            total_stock_kg=12.0,
            product_count=3,
            in_stock_product_count=1,
            out_of_stock_product_count=1,
        ),
    )

    payload = source.to_dict()

    assert payload["status"] == "error"
    assert payload["error_message"] == "CSV export returned 403"
    assert payload["contact_whatsapp_url"].startswith("https://wa.me/")
    assert payload["contact_phone"] == "+54 9 11 1234-5678"
    assert payload["stats"]["total_stock_kg"] == 12.0
