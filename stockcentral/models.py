from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

StockStatus = Literal["in_stock", "out_of_stock", "unknown"]
SourceRunStatus = Literal["ok", "error"]
ImageSource = Literal["manufacturer", "provider", ""]


@dataclass(frozen=True)
class RawStockItem:
    source_id: str
    provider_name: str
    provider_zone: str
    provider_url: str
    original_name: str
    stock_quantity: int | None
    source_url: str
    brand_hint: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class NormalizedFields:
    material: str
    variant: str
    color: str
    diameter_mm: float | None
    weight_g: int | None
    brand: str
    manufacturer_name: str


@dataclass(frozen=True)
class Offer:
    source_id: str
    provider_name: str
    provider_zone: str
    provider_url: str
    original_name: str
    stock_quantity: int | None
    stock_status: StockStatus
    source_url: str
    updated_at: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ProductGroup:
    id: str
    material: str
    variant: str
    color: str
    diameter_mm: float | None
    weight_g: int | None
    brand: str
    manufacturer_name: str
    manufacturer_product_url: str
    image_url: str
    thumbnail_url: str
    image_source: ImageSource
    pantone: str
    sku: str
    ean: str
    display_name: str
    offers: list[Offer]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["offers"] = [offer.to_dict() for offer in self.offers]
        return payload


@dataclass(frozen=True)
class ProviderStats:
    total_stock_units: int
    total_stock_kg: float
    product_count: int
    in_stock_product_count: int
    out_of_stock_product_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SourceStatus:
    id: str
    name: str
    zone: str
    homepage_url: str
    source_url: str
    contact_whatsapp_url: str
    contact_phone: str
    contact_email: str
    address: str
    contact_url: str
    last_success_at: str
    last_attempt_at: str
    status: SourceRunStatus
    error_message: str
    stats: ProviderStats

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["stats"] = self.stats.to_dict()
        return payload


@dataclass(frozen=True)
class ManufacturerInfo:
    id: str
    name: str
    official_site_url: str
    products_url: str
    has_official_product_pages: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
