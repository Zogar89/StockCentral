from stockcentral.models import RawStockItem
from stockcentral.normalize import build_product_id, normalize_record


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
    fields = normalize_record(raw("PETG Transparente 750g 1.75mm"))

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

    assert build_product_id(fields) == "pla-silk-azul-175-1000-grilon3"
