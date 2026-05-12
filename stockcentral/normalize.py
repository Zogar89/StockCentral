from __future__ import annotations

import re
import unicodedata

from stockcentral.models import NormalizedFields, RawStockItem

MATERIAL_RULES = [
    ("ACETAL-POM", "Acetal"),
    ("ACETAL", "Acetal"),
    ("PVA", "PVA"),
    ("PP-T", "PP"),
    ("PPT", "PP"),
    (" PP ", "PP"),
    ("EPET", "PET"),
    ("E-PET", "PET"),
    ("PETG", "PETG"),
    ("PET-G", "PETG"),
    ("NYLON12", "Nylon"),
    ("NYLON 12", "Nylon"),
    ("NYLON6", "Nylon"),
    ("NYLON 6", "Nylon"),
    ("NYLON", "Nylon"),
    ("SIMPLIFLEX", "TPU"),
    ("3NFLEX", "TPU"),
    ("TPU", "TPU"),
    ("FLEX", "TPU"),
    ("ASA", "ASA"),
    ("ABS", "ABS"),
    ("HIPS", "HIPS"),
    ("ASTRA", "PLA"),
    ("BOUTIQUE", "PLA"),
    ("SILK", "PLA"),
    ("WOOD", "PLA"),
    ("ZETA", "PLA"),
    ("PLA", "PLA"),
]

VARIANT_RULES = [
    ("PLA 870", "PLA 870"),
    ("PLA 850", "PLA 850"),
    ("PLA ZETA", "PLA Zeta"),
    ("ZETA", "PLA Zeta"),
    ("BOUTIQUE", "PLA Boutique"),
    ("ASTRA", "PLA Astra"),
    ("SILK", "PLA Silk"),
    ("WOOD", "PLA Wood"),
    ("PLA+", "PLA+"),
    ("PLUS", "PLA+"),
    ("PETG CLEAR", "PETG Clear"),
    ("PP-T", "PP-T"),
    ("PPT", "PP-T"),
    ("EPET", "E-PET"),
    ("E-PET", "E-PET"),
    ("ACETAL-POM", "Acetal-POM"),
    ("NYLON12", "Nylon 12"),
    ("NYLON 12", "Nylon 12"),
    ("NYLON6", "Nylon 6"),
    ("NYLON 6", "Nylon 6"),
    ("PVA", "PVA Soluble"),
    ("SIMPLIFLEX", "Simpliflex"),
    ("3NFLEX", "Flex"),
    ("FLEX", "Flex"),
    ("GALAXY", "Galaxy"),
    ("MATE", "Mate"),
    ("PRO", "Pro"),
]

COLOR_RULES = [
    ("GRIS PLATA", "Gris Plata"),
    ("GRIS ACERO", "Gris Acero"),
    ("GRIS PLOMO", "Gris Plomo"),
    ("AMARILLO FLUO", "Amarillo Fluo"),
    ("NARANJA FLUO", "Naranja Fluo"),
    ("NARANJA UV GLOW", "Naranja UV Glow"),
    ("VERDE UV GLOW", "Verde UV Glow"),
    ("NARANJA PRAGA", "Naranja Praga"),
    ("VERDE FLUO", "Verde Fluo"),
    ("CLEAR AMARILLO", "Clear Amarillo"),
    ("CLEAR AZUL", "Clear Azul"),
    ("CLEAR ROJO", "Clear Rojo"),
    ("CLEAR VERDE", "Clear Verde"),
    ("CLEAR AMBAR", "Clear Ambar"),
    ("CLEAR CRISTAL", "Clear Cristal"),
    ("PERLA CALIDO", "Perla Calido"),
    ("PERLA FRIO", "Perla Frio"),
    ("DULCE DE LECHE", "Dulce de Leche"),
    ("VERDE AVIADOR", "Verde Aviador"),
    ("VERDE MANZANA", "Verde Manzana"),
    ("AZUL TRAFUL", "Azul Traful"),
    ("AZUL DE PRUSIA", "Azul de Prusia"),
    ("AZUL PRUSIA", "Azul de Prusia"),
    ("ROJO CARMIN", "Rojo Carmin"),
    ("VERDE LIMA", "Verde Lima"),
    ("MAGENTA FLUO", "Magenta Fluo"),
    ("GRIS ESPACIAL", "Gris Espacial"),
    ("BLANCO PERLA", "Blanco Perla"),
    ("CREMA DEL CIELO", "Crema del Cielo"),
    ("TUTTI FRUTTI", "Tutti Frutti"),
    ("PIEL-162", "Piel 162"),
    ("PIEL 162", "Piel 162"),
    ("PIEL-720", "Piel 720"),
    ("PIEL 720", "Piel 720"),
    ("SERIE LIMITADA", "Serie Limitada"),
    ("20 COLORES", "Kit 20 Colores"),
    ("10 COLORES", "Kit 10 Colores"),
    ("CARPINCHO", "Carpincho"),
    ("ESMERALDA", "Esmeralda"),
    ("PLATINO", "Platino"),
    ("RUSTICO", "Rustico"),
    ("CALIPSO", "Calipso"),
    ("NEBULA", "Nebula"),
    ("BORDO", "Bordo"),
    ("HABANO", "Habano"),
    ("HUESO", "Hueso"),
    ("NOCHE", "Noche"),
    ("NOGAL", "Nogal"),
    ("PERLA", "Perla"),
    ("PINO", "Pino"),
    ("ROBY", "Roby"),
    ("JADE", "Jade"),
    ("ORO", "Oro"),
    ("UVA", "Uva"),
    ("CARBON", "Carbon"),
    ("RUBI", "Rubi"),
    ("ARENA", "Arena"),
    ("CARIBE", "Caribe"),
    ("ZAFIRO", "Zafiro"),
    ("FRUTILLA", "Frutilla"),
    ("LAVANDA", "Lavanda"),
    ("SALMON", "Salmon"),
    ("ACQUA", "Acqua"),
    ("FUCSIA", "Fucsia"),
    ("CELESTE", "Celeste"),
    ("LILA", "Lila"),
    ("BRONCE", "Bronce"),
    ("TURQUESA", "Turquesa"),
    ("PIEL", "Piel"),
    ("CAOBA", "Caoba"),
    ("CEREZO", "Cerezo"),
    ("DORADO", "Dorado"),
    ("COBRE", "Cobre"),
    ("AZABACHE", "Azabache"),
    ("DARK", "Dark"),
    ("CHOCOLATE", "Chocolate"),
    ("AMBAR", "Ambar"),
    ("NOVA", "Nova"),
    ("OPTICO", "Optico"),
    ("TITANIO", "Titanio"),
    ("NEGRO", "Negro"),
    ("BLANCO", "Blanco"),
    ("ROJO", "Rojo"),
    ("AZUL", "Azul"),
    ("VERDE", "Verde"),
    ("AMARILLO", "Amarillo"),
    ("NARANJA", "Naranja"),
    ("VIOLETA", "Violeta"),
    ("GRIS", "Gris"),
    ("ROSA", "Rosa"),
    ("MARRON", "Marron"),
    ("NATURAL", "Natural"),
    ("TRANSPARENTE", "Transparente"),
    ("CRISTAL", "Cristal"),
]

BRAND_RULES = [
    ("3NEPET", "3N3"),
    ("3NMAX", "3N3"),
    ("3NFLEX", "3N3"),
    ("3N3", "3N3"),
    ("GRILON3", "Grilon3"),
    ("GRILON 3", "Grilon3"),
]


def normalize_record(item: RawStockItem) -> NormalizedFields:
    text = _fold(f"{item.original_name} {item.brand_hint}")
    material = _detect_material(text)
    variant = _detect_variant(text)
    color = _detect_color(text)
    diameter_mm = _detect_diameter(text)
    weight_g = _detect_weight(text)
    brand = _detect_brand(text, item.brand_hint)

    return NormalizedFields(
        material=material,
        variant=variant,
        color=color,
        diameter_mm=diameter_mm,
        weight_g=weight_g,
        brand=brand,
        manufacturer_name=brand,
    )


def build_product_id(fields: NormalizedFields) -> str:
    diameter = "unknown"
    if fields.diameter_mm is not None:
        diameter = str(fields.diameter_mm).replace(".", "")
    weight = str(fields.weight_g) if fields.weight_g is not None else "unknown"
    parts = [
        fields.material,
        fields.variant,
        fields.color,
        diameter,
        weight,
        fields.brand,
    ]
    return "-".join(_slug(part) for part in parts if part)


def build_display_name(fields: NormalizedFields) -> str:
    line = fields.variant or fields.material
    pieces = [line]
    if fields.color:
        pieces.append(fields.color)
    if fields.brand:
        pieces.append(fields.brand)
    if fields.weight_g:
        pieces.append(f"{fields.weight_g / 1000:g} kg")
    if fields.diameter_mm:
        pieces.append(f"{fields.diameter_mm:g} mm")
    return " ".join(pieces)


def _detect_material(text: str) -> str:
    if "3NFLEX" in text and _matches_rule(text, "PLA+"):
        return "PLA"
    padded = f" {text} "
    for token, value in MATERIAL_RULES:
        if _matches_rule(padded, token):
            return value
    return "Sin clasificar"


def _detect_variant(text: str) -> str:
    if "3NFLEX" in text and _matches_rule(text, "PLA+"):
        return "PLA Flexible"
    for token, value in VARIANT_RULES:
        if _matches_rule(text, token):
            return value
    return ""


def _detect_color(text: str) -> str:
    for token, value in COLOR_RULES:
        if _matches_rule(text, token):
            return value
    return "Sin color"


def _detect_diameter(text: str) -> float | None:
    if re.search(r"1[,.]?7[45]\s*(?:MM)?\b", text):
        return 1.75
    if re.search(r"(?<!\d)[,.]75\s*MM\b", text):
        return 1.75
    if re.search(r"\b175\s*MM\b", text):
        return 1.75
    if re.search(r"2[,.]?85\s*(?:MM)?\b", text):
        return 2.85
    return None


def _detect_weight(text: str) -> int | None:
    kg_match = re.search(r"(\d+(?:[,.]\d+)?)\s*KG\b", text)
    if kg_match:
        return int(float(kg_match.group(1).replace(",", ".")) * 1000)
    if re.search(r"\bX\s*KG\b", text):
        return 1000

    g_match = re.search(r"(\d{3,5})\s*(?:G|GR)\b", text)
    if g_match:
        return int(g_match.group(1))

    return None


def _detect_brand(text: str, brand_hint: str) -> str:
    for token, value in BRAND_RULES:
        if _matches_rule(text, token):
            return value
    folded_hint = _fold(brand_hint)
    for token, value in BRAND_RULES:
        if _matches_rule(folded_hint, token):
            return value
    return brand_hint.strip() if brand_hint.strip() else ""


def _contains_token(text: str, token: str) -> bool:
    token_pattern = re.escape(token).replace(r"\ ", r"\s+")
    return re.search(rf"(?<![A-Z0-9]){token_pattern}(?![A-Z])", text) is not None


def _matches_rule(text: str, token: str) -> bool:
    if token in {"EPET", "E-PET", "3NEPET", "3NMAX", "3NFLEX"}:
        return token in text
    return _contains_token(text, token)


def _slug(value: str) -> str:
    folded = _fold(value).lower()
    folded = folded.replace("+", "plus")
    folded = re.sub(r"[^a-z0-9]+", "-", folded)
    return folded.strip("-")


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.upper()
