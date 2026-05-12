from __future__ import annotations

import re
import unicodedata

from stockcentral.models import NormalizedFields, RawStockItem

MATERIALS = ["PLA", "PETG", "ABS", "TPU", "HIPS", "NYLON", "PA"]
VARIANTS = {
    "PLA+": "PLA+",
    "PLUS": "PLA+",
    "SILK": "Silk",
    "MATE": "Mate",
    "BOUTIQUE": "Boutique",
    "ASTRA": "Astra",
    "PRO": "Pro",
    "FLEX": "Flex",
    "WOOD": "Wood",
    "GALAXY": "Galaxy",
}
COLORS = {
    "NEGRO": "Negro",
    "BLANCO": "Blanco",
    "ROJO": "Rojo",
    "AZUL": "Azul",
    "VERDE": "Verde",
    "AMARILLO": "Amarillo",
    "NARANJA": "Naranja",
    "VIOLETA": "Violeta",
    "GRIS": "Gris",
    "ROSA": "Rosa",
    "MARRON": "Marron",
    "NATURAL": "Natural",
    "TRANSPARENTE": "Transparente",
    "CRISTAL": "Cristal",
}
BRANDS = {
    "GRILON3": "Grilon3",
    "GRILON 3": "Grilon3",
    "3N3": "3N3",
}


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
    pieces = [fields.material]
    if fields.variant and fields.variant != fields.material:
        pieces.append(fields.variant)
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
    for material in MATERIALS:
        if _contains_token(text, material):
            return "Nylon" if material in {"NYLON", "PA"} else material
    return "Sin clasificar"


def _detect_variant(text: str) -> str:
    for token, value in VARIANTS.items():
        if _contains_token(text, token):
            return value
    return ""


def _detect_color(text: str) -> str:
    for token, value in COLORS.items():
        if _contains_token(text, token):
            return value
    return "Sin color"


def _detect_diameter(text: str) -> float | None:
    if re.search(r"1[,.]?75\s*MM", text):
        return 1.75
    if re.search(r"\b175\s*MM\b", text):
        return 1.75
    if re.search(r"2[,.]?85\s*MM", text):
        return 2.85
    return None


def _detect_weight(text: str) -> int | None:
    kg_match = re.search(r"(\d+(?:[,.]\d+)?)\s*KG\b", text)
    if kg_match:
        return int(float(kg_match.group(1).replace(",", ".")) * 1000)

    g_match = re.search(r"(\d{3,5})\s*G\b", text)
    if g_match:
        return int(g_match.group(1))

    return None


def _detect_brand(text: str, brand_hint: str) -> str:
    folded_hint = _fold(brand_hint)
    for token, value in BRANDS.items():
        if token in text or token in folded_hint:
            return value
    return brand_hint.strip() if brand_hint.strip() else ""


def _contains_token(text: str, token: str) -> bool:
    return re.search(rf"(?<![A-Z0-9]){re.escape(token)}(?![A-Z0-9])", text) is not None


def _slug(value: str) -> str:
    folded = _fold(value).lower()
    folded = folded.replace("+", "plus")
    folded = re.sub(r"[^a-z0-9]+", "-", folded)
    return folded.strip("-")


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return without_marks.upper()
