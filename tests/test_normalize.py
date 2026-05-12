from stockcentral.models import RawStockItem
from stockcentral.normalize import build_display_name, build_product_id, normalize_record


def raw(name: str, source_id: str = "filamentos3d", brand_hint: str = "") -> RawStockItem:
    return RawStockItem(
        source_id=source_id,
        provider_name="Proveedor",
        provider_zone="Zona Sur",
        provider_url="https://example.com",
        original_name=name,
        stock_quantity=1,
        source_url="https://example.com/source",
        brand_hint=brand_hint,
        updated_at="2026-05-12T12:00:00-03:00",
    )


def test_normalizes_grilon3_pla_negro():
    fields = normalize_record(raw("GRILON3 PLA Negro 1.75mm 1kg", brand_hint="Grilon3"))

    assert fields.material == "PLA"
    assert fields.variant == ""
    assert fields.color == "Negro"
    assert fields.diameter_mm == 1.75
    assert fields.weight_g == 1000
    assert fields.brand == "Grilon3"
    assert fields.manufacturer_name == "Grilon3"


def test_normalizes_3n3_pla_plus_rojo():
    fields = normalize_record(raw("3N3 PLA+ Rojo 1 kg 1.75 mm", source_id="grupo_senz"))

    assert fields.material == "PLA"
    assert fields.variant == "PLA+"
    assert fields.color == "Rojo"
    assert fields.diameter_mm == 1.75
    assert fields.weight_g == 1000
    assert fields.brand == "3N3"
    assert fields.manufacturer_name == "3N3"


def test_keeps_other_weights_separate():
    fields = normalize_record(raw("PETG Transparente 750 GR 1.75mm"))

    assert fields.material == "PETG"
    assert fields.color == "Transparente"
    assert fields.weight_g == 750


def test_keeps_special_colors_separate():
    natural = normalize_record(raw("PLA Natural 1kg 1.75mm"))
    transparent = normalize_record(raw("PLA Transparente 1kg 1.75mm"))
    crystal = normalize_record(raw("PLA Cristal 1kg 1.75mm"))

    assert natural.color == "Natural"
    assert transparent.color == "Transparente"
    assert crystal.color == "Cristal"


def test_product_id_includes_brand_and_format():
    fields = normalize_record(raw("PLA Silk Azul 1kg 1.75mm Grilon3"))

    assert build_product_id(fields) == "pla-pla-silk-azul-175-1000-grilon3"


def test_normalizes_grilon3_official_lines():
    astra = normalize_record(raw("GRILON3 ASTRA DARK 1.75 MM X 1 KG", brand_hint="Grilon3"))
    boutique = normalize_record(raw("MEGAFILL GRILON3 BOUTIQUE PERLA 1.75 MM X 4 KG", brand_hint="Grilon3"))
    pp = normalize_record(raw("GRILON3 PP-T 06_AMARILLO 1.75 MM X 1 KG", brand_hint="Grilon3"))
    nylon = normalize_record(raw("GRILON3 NYLON12 AZUL 1.75 MM X 1 KG", brand_hint="Grilon3"))
    pva = normalize_record(raw("GRILON3 PVA NATURAL 1.75 MM X 500 GR", brand_hint="Grilon3"))

    assert (astra.material, astra.variant, astra.color) == ("PLA", "PLA Astra", "Dark")
    assert (boutique.material, boutique.variant, boutique.weight_g) == ("PLA", "PLA Boutique", 4000)
    assert (pp.material, pp.variant) == ("PP", "PP-T")
    assert (nylon.material, nylon.variant) == ("Nylon", "Nylon 12")
    assert (pva.material, pva.variant, pva.weight_g) == ("PVA", "PVA Soluble", 500)


def test_normalizes_epet_as_recycled_pet_and_3n_subbrands_as_3n3():
    fields = normalize_record(raw("3nEPET AZUL TRAFUL 1KG", brand_hint=""))
    flex = normalize_record(raw("3nFLEX BLANCO 500G", brand_hint="Grilon3"))
    pla_flex = normalize_record(raw("3NFLEX PLA+ 06_AMARILLO 1.75 MM X 1 KG", brand_hint=""))

    assert (fields.material, fields.variant, fields.color, fields.brand) == ("PET", "E-PET", "Azul Traful", "3N3")
    assert (flex.material, flex.variant, flex.brand) == ("TPU", "Flex", "3N3")
    assert (pla_flex.material, pla_flex.variant, pla_flex.color, pla_flex.brand) == ("PLA", "PLA Flexible", "Amarillo", "3N3")


def test_detects_compact_color_and_wide_diameters():
    compact = normalize_record(raw("3nFLEX AZUL500G", brand_hint=""))
    wide = normalize_record(raw("GRILON3 PLA NEGRO 2.85 MM X 1 KG", brand_hint="Grilon3"))
    carbon = normalize_record(raw("GRILON3 BOUTIQUE 02_CARBON.75 MM X 1 KG", brand_hint="Grilon3"))

    assert compact.color == "Azul"
    assert wide.diameter_mm == 2.85
    assert carbon.diameter_mm == 1.75


def test_keeps_color_variants_separate():
    blue = normalize_record(raw("GRILON3 PLA 08_AZUL 1.75 MM X 1 KG", brand_hint="Grilon3"))
    prussia = normalize_record(raw("GRILON3 PLA 23_AZUL DE PRUSIA 1.75 MM X 1 KG", brand_hint="Grilon3"))

    assert blue.color == "Azul"
    assert prussia.color == "Azul de Prusia"
    assert build_product_id(blue) != build_product_id(prussia)


def test_keeps_provider_organized_color_variants_separate():
    piel_162 = normalize_record(raw("GRILON3 PLA 91_PIEL-162 1.75 MM X 1 KG", brand_hint="Grilon3"))
    piel_720 = normalize_record(raw("GRILON3 PLA 92_PIEL-720 1.75 MM X 1 KG", brand_hint="Grilon3"))
    astra_calipso = normalize_record(raw("GRILON3 ASTRA CALIPSO 1.75 MM X 1 KG", brand_hint="Grilon3"))
    astra_jade = normalize_record(raw("GRILON3 ASTRA JADE 1.75 MM X 1 KG", brand_hint="Grilon3"))
    verde = normalize_record(raw("GRILON3 PLA 07_VERDE 1.75 MM X 1 KG", brand_hint="Grilon3"))
    verde_manzana = normalize_record(raw("GRILON3 PLA 19_VERDE MANZANA 1.75 MM X 1 KG", brand_hint="Grilon3"))
    kit_20 = normalize_record(raw("KIT LAPIZ 3D GRILON3 PLA 20 COLORES 10M POR COLOR (200M)", brand_hint="Grilon3"))
    kit_10 = normalize_record(raw("KIT LAPIZ 3D GRILON3 PLA 10 COLORES 10M POR COLOR (100M)", brand_hint="Grilon3"))
    uva = normalize_record(raw("3NMAX PLA+ 24_UVA 1.75 MM X 1 KG", brand_hint=""))
    uv_glow = normalize_record(raw("GRILON3 PLA 850 09_NARANJA UV GLOW 1.75 MM X 1 KG", brand_hint="Grilon3"))
    praga = normalize_record(raw("GRILON3 PETG NARANJA PRAGA 1.75 MM X 1 KG", brand_hint="Grilon3"))
    perla_calido = normalize_record(raw("GRILON3 BOUTIQUE PERLA  CALIDO 1.75 MM X 1 KG", brand_hint="Grilon3"))

    assert piel_162.color == "Piel 162"
    assert piel_720.color == "Piel 720"
    assert astra_calipso.color == "Calipso"
    assert astra_jade.color == "Jade"
    assert verde.color == "Verde"
    assert verde_manzana.color == "Verde Manzana"
    assert kit_20.color == "Kit 20 Colores"
    assert kit_10.color == "Kit 10 Colores"
    assert uva.color == "Uva"
    assert uv_glow.color == "Naranja UV Glow"
    assert praga.color == "Naranja Praga"
    assert perla_calido.color == "Perla Calido"
    assert len({
        build_product_id(piel_162),
        build_product_id(piel_720),
        build_product_id(astra_calipso),
        build_product_id(astra_jade),
        build_product_id(verde),
        build_product_id(verde_manzana),
        build_product_id(kit_20),
        build_product_id(kit_10),
        build_product_id(uva),
        build_product_id(uv_glow),
        build_product_id(praga),
        build_product_id(perla_calido),
    }) == 12


def test_build_display_name_avoids_repeating_material_and_variant():
    fields = normalize_record(raw("3N3 PLA+ Rojo 1kg 1.75mm"))

    assert build_display_name(fields) == "PLA+ Rojo 3N3 1 kg 1.75 mm"
