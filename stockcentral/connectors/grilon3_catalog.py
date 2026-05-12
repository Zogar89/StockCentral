from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests

from stockcentral.models import NormalizedFields, RawStockItem
from stockcentral.normalize import build_product_id, normalize_record

BASE_URL = "https://grilon3.com.ar/productos/"
EMPTY_ENRICHMENT = {"manufacturer_product_url": "", "image_url": "", "image_source": ""}


@dataclass(frozen=True)
class CatalogProduct:
    product_id: str
    title: str
    product_url: str
    image_url: str


def fetch_grilon3_catalog(products_url: str = BASE_URL, timeout_seconds: int = 30) -> dict[str, CatalogProduct]:
    response = requests.get(products_url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_grilon3_catalog(response.text, base_url=products_url)


def parse_grilon3_catalog(html_text: str, base_url: str = BASE_URL) -> dict[str, CatalogProduct]:
    links = _ProductLinkParser.parse(html_text, base_url)
    catalog: dict[str, CatalogProduct] = {}

    for link in links:
        title = _clean_text(link["title"])
        if not title:
            continue
        item = RawStockItem(
            source_id="grilon3_catalog",
            provider_name="Grilon3",
            provider_zone="",
            provider_url="https://grilon3.com.ar/",
            original_name=title,
            stock_quantity=None,
            source_url=link["product_url"],
            brand_hint="Grilon3",
        )
        fields = normalize_record(item)
        product_id = build_product_id(fields)
        if fields.brand != "Grilon3" or fields.material == "Sin clasificar" or fields.color == "Sin color":
            continue
        catalog[product_id] = CatalogProduct(
            product_id=product_id,
            title=title,
            product_url=link["product_url"],
            image_url=link["image_url"],
        )

    return catalog


def enrich_with_grilon3_catalog(
    fields: NormalizedFields,
    catalog: dict[str, CatalogProduct],
) -> dict[str, str]:
    if fields.brand != "Grilon3":
        return dict(EMPTY_ENRICHMENT)

    product = catalog.get(build_product_id(fields))
    if product is None:
        return dict(EMPTY_ENRICHMENT)

    return {
        "manufacturer_product_url": product.product_url,
        "image_url": product.image_url,
        "image_source": "manufacturer" if product.image_url else "",
    }


class _ProductLinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._text_stack: list[str] = []

    @classmethod
    def parse(cls, html_text: str, base_url: str) -> list[dict[str, str]]:
        parser = cls(base_url)
        parser.feed(html_text)
        return parser.links

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = dict(attrs)
        if tag == "a" and "href" in attributes:
            href = attributes["href"]
            if "/producto/" in href:
                self._current = {
                    "product_url": urljoin(self.base_url, href),
                    "image_url": "",
                    "title": "",
                }
                self._text_stack = []
            return

        if self._current is not None and tag == "img" and not self._current["image_url"]:
            src = attributes.get("src") or attributes.get("data-src") or ""
            if src:
                self._current["image_url"] = urljoin(self.base_url, src)
            alt = attributes.get("alt", "")
            if alt:
                self._text_stack.append(alt)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current is not None:
            self._current["title"] = _clean_text(" ".join(self._text_stack))
            self.links.append(self._current)
            self._current = None
            self._text_stack = []

    def handle_data(self, data: str) -> None:
        if self._current is not None:
            self._text_stack.append(data)


def _clean_text(value: str) -> str:
    return " ".join(value.split())
