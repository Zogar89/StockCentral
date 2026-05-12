from stockcentral.providers import MANUFACTURERS, SOURCES


def test_sources_cover_initial_amba_providers():
    assert set(SOURCES) == {"filamentos3d", "grupo_senz", "mundoinsumos"}
    assert SOURCES["filamentos3d"].zone == "Zona Sur"
    assert SOURCES["grupo_senz"].zone == "Zona Oeste"
    assert SOURCES["mundoinsumos"].zone == "Zona Norte"


def test_google_sheet_sources_include_sheet_ids_and_gids():
    assert SOURCES["grupo_senz"].sheet_id == "14nblAeXZfx_TEeHj4xnK90hSmUp3hk6KSO4nUTrb9zM"
    assert SOURCES["grupo_senz"].gid == "614179668"
    assert SOURCES["mundoinsumos"].sheet_id == "1r-nKy4tRRtZ-5xwgxAcia8REDVW0Dv0h"
    assert SOURCES["mundoinsumos"].gid == "1981641819"


def test_provider_contacts_use_public_official_data():
    assert SOURCES["filamentos3d"].contact_url == "https://filamentos3d.com.ar/contactenos.php"
    assert SOURCES["filamentos3d"].contact_whatsapp_url == "https://wa.me/5491154648121"
    assert SOURCES["filamentos3d"].contact_email == "info@filamentos3d.com.ar"
    assert SOURCES["filamentos3d"].address == "Av. H. Yrigoyen 9689, Lomas de Zamora, Buenos Aires"

    assert SOURCES["grupo_senz"].contact_whatsapp_url == ""
    assert SOURCES["grupo_senz"].contact_phone == "+54 11 3605-9099"
    assert SOURCES["grupo_senz"].contact_email == "contacto@gruposenz.com.ar"
    assert SOURCES["grupo_senz"].address == ""

    assert SOURCES["mundoinsumos"].contact_url == "https://mundoinsumos.com.ar/contacto/"
    assert SOURCES["mundoinsumos"].contact_whatsapp_url == "https://wa.me/541165863008"
    assert SOURCES["mundoinsumos"].contact_email == "info@mundoinsumos.com.ar"
    assert SOURCES["mundoinsumos"].address == "Gral. Jose de San Martin 2345, Florida, Buenos Aires"


def test_manufacturer_configuration_keeps_3n3_without_official_site():
    assert MANUFACTURERS["grilon3"].products_url == "https://grilon3.com.ar/productos/"
    assert MANUFACTURERS["grilon3"].has_official_product_pages is True
    assert MANUFACTURERS["3n3"].official_site_url == ""
    assert MANUFACTURERS["3n3"].has_official_product_pages is False
