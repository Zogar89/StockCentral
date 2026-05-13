from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse

import requests

from stockcentral.models import NormalizedFields, RawStockItem
from stockcentral.normalize import build_product_id, normalize_record

BASE_URL = "https://grilon3.com.ar/productos/"
SITEMAP_URL = "https://grilon3.com.ar/product-sitemap.xml"
EMPTY_ENRICHMENT = {"manufacturer_product_url": "", "image_url": "", "image_source": "", "pantone": "", "sku": "", "ean": ""}


@dataclass(frozen=True)
class CatalogProduct:
    product_id: str
    title: str
    product_url: str
    image_url: str
    pantone: str = ""
    sku: str = ""
    ean: str = ""


def fetch_grilon3_catalog(products_url: str = BASE_URL, timeout_seconds: int = 30) -> dict[str, CatalogProduct]:
    response = requests.get(products_url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_grilon3_catalog(response.text, base_url=products_url)


def fetch_grilon3_sitemap_catalog(sitemap_url: str = SITEMAP_URL, timeout_seconds: int = 30) -> dict[str, CatalogProduct]:
    response = requests.get(sitemap_url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_grilon3_sitemap(response.text)


def enrich_grilon3_catalog_details(
    catalog: dict[str, CatalogProduct],
    timeout_seconds: int = 4,
    max_workers: int = 12,
) -> dict[str, CatalogProduct]:
    enriched = dict(catalog)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_grilon3_product_detail, product.product_url, timeout_seconds): (product_id, product)
            for product_id, product in catalog.items()
        }
        for future in as_completed(futures):
            product_id, product = futures[future]
            try:
                detail = future.result()
            except Exception:
                continue
            enriched[product_id] = CatalogProduct(
                product_id=product.product_id,
                title=product.title,
                product_url=product.product_url,
                image_url=product.image_url or detail["image_url"],
                pantone=detail["pantone"],
                sku=detail["sku"],
                ean=detail["ean"],
            )
    return enriched


def enrich_grilon3_selected_details(
    catalog: dict[str, CatalogProduct],
    product_ids: set[str],
    timeout_seconds: int = 4,
    max_workers: int = 12,
) -> dict[str, CatalogProduct]:
    selected = {
        product_id: product
        for product_id, product in catalog.items()
        if product_id in product_ids and not product.pantone
    }
    if not selected:
        return dict(catalog)

    enriched = dict(catalog)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_grilon3_product_detail, product.product_url, timeout_seconds): (product_id, product)
            for product_id, product in selected.items()
        }
        for future in as_completed(futures):
            product_id, product = futures[future]
            try:
                detail = future.result()
            except Exception:
                continue
            enriched[product_id] = CatalogProduct(
                product_id=product.product_id,
                title=product.title,
                product_url=product.product_url,
                image_url=product.image_url or detail["image_url"],
                pantone=detail["pantone"],
                sku=detail["sku"],
                ean=detail["ean"],
            )
    return enriched


def apply_grilon3_metadata(
    catalog: dict[str, CatalogProduct],
    metadata: dict[str, dict[str, str]],
) -> dict[str, CatalogProduct]:
    if not metadata:
        return dict(catalog)
    enriched: dict[str, CatalogProduct] = {}
    for product_id, product in catalog.items():
        data = metadata.get(product_id, {})
        enriched[product_id] = CatalogProduct(
            product_id=product.product_id,
            title=product.title,
            product_url=product.product_url,
            image_url=product.image_url or data.get("image_url", ""),
            pantone=product.pantone or data.get("pantone", ""),
            sku=product.sku or data.get("sku", ""),
            ean=product.ean or data.get("ean", ""),
        )
    return enriched


def fetch_grilon3_product_detail(product_url: str, timeout_seconds: int = 10) -> dict[str, str]:
    response = requests.get(product_url, timeout=timeout_seconds)
    response.raise_for_status()
    return parse_grilon3_product_detail(response.text, base_url=product_url)


def parse_grilon3_product_detail(html_text: str, base_url: str = BASE_URL) -> dict[str, str]:
    detail = _ProductDetailParser.parse(html_text, base_url)
    sku, ean = _extract_sku_ean_from_html(html_text)
    return {
        **detail,
        "sku": detail["sku"] or sku,
        "ean": detail["ean"] or ean,
    }


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
            pantone="",
            sku="",
            ean="",
        )

    return catalog


def parse_grilon3_sitemap(xml_text: str) -> dict[str, CatalogProduct]:
    catalog: dict[str, CatalogProduct] = {}
    for url in re.findall(r"<loc>(.*?)</loc>", xml_text):
        if "/producto/" not in url:
            continue
        title = _title_from_product_url(url)
        if not title:
            continue
        item = RawStockItem(
            source_id="grilon3_catalog",
            provider_name="Grilon3",
            provider_zone="",
            provider_url="https://grilon3.com.ar/",
            original_name=title,
            stock_quantity=None,
            source_url=url,
            brand_hint="Grilon3",
        )
        fields = normalize_record(item)
        if fields.brand != "Grilon3" or fields.material == "Sin clasificar" or fields.color == "Sin color":
            continue
        product_id = build_product_id(fields)
        catalog[product_id] = CatalogProduct(
            product_id=product_id,
            title=title,
            product_url=url,
            image_url="",
            pantone="",
            sku="",
            ean="",
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
        "pantone": getattr(product, "pantone", ""),
        "sku": getattr(product, "sku", ""),
        "ean": getattr(product, "ean", ""),
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


class _ProductDetailParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.pantone = ""
        self.image_candidates: list[str] = []
        self.sku = ""
        self.ean = ""

    @classmethod
    def parse(cls, html_text: str, base_url: str) -> dict[str, str]:
        parser = cls(base_url)
        parser.feed(html_text)
        return {"pantone": parser.pantone, "image_url": _preferred_product_image(parser.image_candidates), "sku": parser.sku, "ean": parser.ean}

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag != "img":
            return
        attributes = dict(attrs)
        src = (
            attributes.get("data-large_image")
            or _largest_srcset_image(attributes.get("srcset", "") or attributes.get("data-srcset", ""))
            or attributes.get("data-src")
            or attributes.get("src")
            or ""
        )
        alt = attributes.get("alt", "")
        image_url = urljoin(self.base_url, src)
        if _is_product_image_candidate(image_url, alt):
            self.image_candidates.append(image_url)

    def handle_data(self, data: str) -> None:
        if self.pantone:
            return
        pantone = _extract_pantone(data)
        if pantone:
            self.pantone = pantone
        sku, ean = _extract_sku_ean(data)
        if sku and not self.sku:
            self.sku = sku
        if ean and not self.ean:
            self.ean = ean


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _extract_pantone(value: str) -> str:
    match = re.search(r"\bPANTONE\s+([^*<\n\r]+)", value, flags=re.IGNORECASE)
    if not match:
        return ""
    color = _clean_text(match.group(1)).strip(" .:-")
    return f"Pantone {color}" if color else ""


def _extract_sku_ean(value: str) -> tuple[str, str]:
    text = _clean_text(value)
    sku_match = re.search(r"\bSKU:\s*([A-Z0-9_-]+)", text, flags=re.IGNORECASE)
    ean_match = re.search(r"\bEAN:\s*([0-9]{8,14})", text, flags=re.IGNORECASE)
    return (
        sku_match.group(1).strip() if sku_match else "",
        ean_match.group(1).strip() if ean_match else "",
    )


def _largest_srcset_image(srcset: str) -> str:
    candidates = []
    for item in srcset.split(","):
        parts = item.strip().split()
        if not parts:
            continue
        url = parts[0]
        width = 0
        if len(parts) > 1 and parts[1].endswith("w"):
            width_text = parts[1][:-1]
            width = int(width_text) if width_text.isdigit() else 0
        candidates.append((width, url))
    if not candidates:
        return ""
    return max(candidates, key=lambda candidate: candidate[0])[1]


def _is_product_image_candidate(image_url: str, alt: str) -> bool:
    folded = _image_token(f"{image_url} {alt}")
    if "/wp-content/uploads/" not in image_url:
        return False
    blocked = ["favicon", "logo", "auspicia", "iso", "tabla", "perfil", "icon"]
    return not any(token in folded for token in blocked)


def _preferred_product_image(image_urls: list[str]) -> str:
    unique_urls = list(dict.fromkeys(image_urls))
    if not unique_urls:
        return ""
    return max(unique_urls, key=_product_image_score)


def _product_image_score(image_url: str) -> tuple[int, str]:
    filename = _image_token(urlparse(image_url).path.rsplit("/", 1)[-1])
    score = 0
    if "600x600" in filename:
        score += 20
    if "350x350" in filename:
        score += 10
    if "web" in filename:
        score += 80
    if re.search(r"(?:^|[-_])web(?:[-_.]|$)", filename):
        score += 25
    if re.search(r"[a-z]+2(?:-\d+x\d+)?\.", filename):
        score += 12
    if re.search(r"[a-z]+3(?:-\d+x\d+)?\.", filename):
        score -= 4
    if re.search(r"\d+[-_]web", filename):
        score -= 8
    if re.search(r"\d+(?:[-_]\d+x\d+)?\.", filename):
        score -= 12
    if any(token in filename for token in ["caja", "box", "leon", "dragon", "pieza", "textura"]):
        score -= 50
    return (score, image_url)


def _image_token(value: str) -> str:
    return value.lower().replace("%20", "-").replace("_", "-")


def _extract_sku_ean_from_html(html_text: str) -> tuple[str, str]:
    sku_match = re.search(r'class=["\']sku["\'][^>]*>\s*([^<\s]+)', html_text, flags=re.IGNORECASE)
    ean_match = re.search(r'class=["\']ean["\'][^>]*>\s*([0-9]{8,14})', html_text, flags=re.IGNORECASE)
    if sku_match or ean_match:
        return (
            sku_match.group(1).strip() if sku_match else "",
            ean_match.group(1).strip() if ean_match else "",
        )
    return _extract_sku_ean(_clean_text(re.sub(r"<[^>]+>", " ", html_text)))


def _title_from_product_url(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    if slug in {"producto", ""}:
        return ""

    parts = slug.split("-")
    diameter = ""
    if parts and parts[-1] == "285":
        diameter = "2.85 mm"
        parts = parts[:-1]
    title = " ".join(part.upper() if part in {"pla", "petg", "abs", "hips"} else part.title() for part in parts)
    pieces = [title, "Grilon3", "1 kg"]
    if diameter:
        pieces.append(diameter)
    return " ".join(pieces)
