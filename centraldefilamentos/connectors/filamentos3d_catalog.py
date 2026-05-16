from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
import httpx

from centraldefilamentos.models import RawStockItem
from centraldefilamentos.normalize import build_product_id, normalize_record

FILAMENTOS3D_CATEGORY_URLS = {
    "3n3-pla": "https://filamentos3d.com.ar/43-pla-3n3-175mm-1kg",
    "3nmax-pla-plus": "https://filamentos3d.com.ar/49-3nmax-pla",
    "3nflex-pla-plus": "https://filamentos3d.com.ar/66-3nflex-pla-175mm",
    "3n3-petg": "https://filamentos3d.com.ar/48-3n3-petg-175mm",
    "3n3-epet": "https://filamentos3d.com.ar/40-3n3-epet-175mm",
}


@dataclass(frozen=True)
class ProviderCatalogProduct:
    product_id: str
    title: str
    product_url: str
    image_url: str = ""
    line_code: str = ""
    sku: str = ""


def fetch_filamentos3d_catalog(
    category_urls: dict[str, str] | None = None,
    timeout_seconds: int = 12,
) -> dict[str, ProviderCatalogProduct]:
    products: dict[str, ProviderCatalogProduct] = {}
    for line_code, category_url in (category_urls or FILAMENTOS3D_CATEGORY_URLS).items():
        response = httpx.get(category_url, timeout=timeout_seconds, follow_redirects=True)
        response.raise_for_status()
        for product in parse_filamentos3d_category(response.text, category_url, line_code):
            products[product.product_id] = product
    return products


def enrich_filamentos3d_catalog_details(
    catalog: dict[str, ProviderCatalogProduct],
    timeout_seconds: int = 12,
) -> dict[str, ProviderCatalogProduct]:
    enriched: dict[str, ProviderCatalogProduct] = {}
    for product_id, product in catalog.items():
        try:
            response = httpx.get(product.product_url, timeout=timeout_seconds, follow_redirects=True)
            response.raise_for_status()
            detail = parse_filamentos3d_product_detail(response.text, product.product_url)
        except Exception:
            enriched[product_id] = product
            continue

        title = detail.get("title") or product.title
        normalized_id = _product_id_from_title(title, product.line_code)
        enriched[normalized_id] = ProviderCatalogProduct(
            product_id=normalized_id,
            title=title,
            product_url=product.product_url,
            image_url=detail.get("image_url") or product.image_url,
            line_code=product.line_code,
            sku=detail.get("sku") or product.sku,
        )
    return enriched


def parse_filamentos3d_category(
    html_text: str,
    category_url: str,
    line_code: str,
) -> list[ProviderCatalogProduct]:
    soup = _soup(html_text)
    products: list[ProviderCatalogProduct] = []
    seen_urls: set[str] = set()

    for article in soup.find_all(["article", "li", "div"]):
        if not _looks_like_product_card(article):
            continue
        product = _product_from_card(article, category_url, line_code)
        if product is None or product.product_url in seen_urls:
            continue
        seen_urls.add(product.product_url)
        products.append(product)

    if products:
        return products

    for link in soup.find_all("a", href=True):
        title = _clean_text(link.get_text(" ", strip=True)) or _clean_text(link.get("title", ""))
        href = str(link.get("href", ""))
        if not _is_product_link(href, title):
            continue
        product_url = urljoin(category_url, href)
        if product_url in seen_urls:
            continue
        seen_urls.add(product_url)
        products.append(
            ProviderCatalogProduct(
                product_id=_product_id_from_title(title, line_code),
                title=title,
                product_url=product_url,
                line_code=line_code,
            )
        )
    return products


def parse_filamentos3d_product_detail(html_text: str, product_url: str) -> dict[str, str]:
    soup = _soup(html_text)
    title = _extract_title(soup)
    return {
        "title": title,
        "image_url": _extract_main_image(soup, product_url),
        "sku": _extract_sku(soup),
    }


def _product_from_card(card: Tag, category_url: str, line_code: str) -> ProviderCatalogProduct | None:
    title = _card_title(card)
    link = _card_link(card, title)
    if link is None:
        return None
    product_url = urljoin(category_url, str(link.get("href", "")))
    if not title:
        title = _clean_text(link.get_text(" ", strip=True)) or _clean_text(link.get("title", ""))
    if not _is_product_link(product_url, title):
        return None
    return ProviderCatalogProduct(
                product_id=_product_id_from_title(title, line_code),
        title=title,
        product_url=product_url,
        image_url=_card_image(card, category_url),
        line_code=line_code,
    )


def _looks_like_product_card(tag: Tag) -> bool:
    classes = " ".join(str(value) for value in tag.get("class", []))
    if any(marker in classes for marker in ["product-miniature", "js-product-miniature", "product"]):
        return True
    link = tag.find("a", href=True)
    if link is None:
        return False
    return _is_product_link(str(link.get("href", "")), _clean_text(link.get_text(" ", strip=True)))


def _card_link(card: Tag, title: str) -> Tag | None:
    for selector in [".product-thumbnail", ".thumbnail", "h2 a", "h3 a", "a"]:
        link = card.select_one(selector)
        if isinstance(link, Tag) and link.get("href"):
            link_title = _clean_text(link.get_text(" ", strip=True)) or _clean_text(link.get("title", ""))
            if _is_product_link(str(link.get("href", "")), title or link_title):
                return link
    return None


def _card_title(card: Tag) -> str:
    for selector in [".product-title", "h1", "h2", "h3", "a"]:
        element = card.select_one(selector)
        if isinstance(element, Tag):
            text = _clean_text(element.get_text(" ", strip=True)) or _clean_text(element.get("title", ""))
            if _looks_like_3n3_title(text):
                return text
    image = card.find("img")
    if isinstance(image, Tag):
        return _clean_text(image.get("alt", ""))
    return ""


def _card_image(card: Tag, base_url: str) -> str:
    image = card.find("img")
    if not isinstance(image, Tag):
        return ""
    image_url = _best_image_from_tag(image)
    return urljoin(base_url, image_url) if image_url else ""


def _is_product_link(href: str, title: str) -> bool:
    if not href or ".html" not in href:
        return False
    if not _looks_like_3n3_title(title):
        return False
    return ".html" in href or re.search(r"/\d", href) is not None or "filamentos3d.com.ar" in href


def _looks_like_3n3_title(title: str) -> bool:
    folded = title.upper()
    return any(marker in folded for marker in ["3N3", "3NMAX", "3NFLEX", "3NEPET", "EPET", "PETG"])


def _extract_title(soup: BeautifulSoup) -> str:
    heading = soup.find("h1")
    if isinstance(heading, Tag):
        text = _clean_text(heading.get_text(" ", strip=True))
        if text:
            return text
    meta_title = soup.find("meta", property="og:title")
    if isinstance(meta_title, Tag) and meta_title.get("content"):
        return _clean_text(meta_title["content"])
    if soup.title is not None:
        return _clean_text(soup.title.get_text(" ", strip=True).split("|")[0])
    return ""


def _extract_main_image(soup: BeautifulSoup, base_url: str) -> str:
    candidates: list[tuple[int, str]] = []
    for image in soup.find_all("img"):
        if not isinstance(image, Tag) or _is_related_or_miniature_image(image):
            continue
        image_url = _best_image_from_tag(image)
        if not image_url:
            continue
        candidates.append((_image_score(image, image_url), urljoin(base_url, image_url)))
    if not candidates:
        return ""
    candidates.sort(key=lambda candidate: candidate[0], reverse=True)
    return candidates[0][1]


def _best_image_from_tag(image: Tag) -> str:
    srcset = _clean_text(image.get("srcset", ""))
    if srcset:
        return _largest_srcset_image(srcset)
    for attr in ["data-full-size-image-url", "data-src", "src"]:
        value = _clean_text(image.get(attr, ""))
        if value and _looks_like_product_image_url(value):
            return value
    return ""


def _largest_srcset_image(srcset: str) -> str:
    best_url = ""
    best_width = -1
    for part in srcset.split(","):
        pieces = part.strip().split()
        if not pieces:
            continue
        url = pieces[0]
        width = 0
        if len(pieces) > 1 and pieces[1].endswith("w"):
            try:
                width = int(pieces[1][:-1])
            except ValueError:
                width = 0
        if _looks_like_product_image_url(url) and width >= best_width:
            best_url = url
            best_width = width
    return best_url


def _looks_like_product_image_url(value: str) -> bool:
    lowered = value.lower()
    if any(
        blocked in lowered
        for blocked in ["logo-", "default-product", "es-default", "no-image", "placeholder", "whatsapp", "/modules/"]
    ):
        return False
    return True


def _is_related_or_miniature_image(image: Tag) -> bool:
    for element in [image, *list(image.parents)]:
        if not isinstance(element, Tag):
            continue
        classes = " ".join(str(value) for value in element.get("class", []))
        element_id = str(element.get("id", ""))
        marker = f"{classes} {element_id}".lower()
        if any(
            blocked in marker
            for blocked in [
                "product-miniature",
                "featured-products",
                "related-products",
                "product-accessories",
                "crossselling",
            ]
        ):
            return True
    return False


def _image_score(image: Tag, image_url: str) -> int:
    classes = " ".join(str(value) for value in image.get("class", []))
    score = 0
    if "js-qv-product-cover" in classes or "w-100" in classes:
        score += 80
    if "product_main_2x" in image_url:
        score += 60
    elif "product_main" in image_url:
        score += 50
    elif "default_xl" in image_url:
        score += 25
    if "home_default" in image_url:
        score += 10
    return score


def _extract_sku(soup: BeautifulSoup) -> str:
    selectors = [".product-reference", ".product-reference span", "[itemprop='sku']", "[data-product-reference]"]
    for selector in selectors:
        element = soup.select_one(selector)
        if not isinstance(element, Tag):
            continue
        value = _clean_text(element.get("content", "") or element.get("data-product-reference", "") or element.get_text(" ", strip=True))
        value = re.sub(r"^(SKU|Referencia|Reference)\s*:?\s*", "", value, flags=re.IGNORECASE)
        if value:
            return value
    text = soup.get_text(" ", strip=True)
    match = re.search(r"\bSKU\s*:?\s*([A-Z0-9._-]+)", text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _product_id_from_title(title: str, line_code: str = "") -> str:
    fields = normalize_record(
        RawStockItem(
            source_id="filamentos3d_catalog",
            provider_name="Filamentos3D",
            provider_zone="Zona Sur",
            provider_url="https://filamentos3d.com.ar/",
            original_name=_title_for_normalization(title, line_code),
            stock_quantity=None,
            source_url="",
            brand_hint="3N3",
        )
    )
    return build_product_id(fields)


def _title_for_normalization(title: str, line_code: str = "") -> str:
    fixed = title
    fixed = re.sub(r"\b3N3\s*EPET\b", "3N3 EPET", fixed, flags=re.IGNORECASE)
    fixed = re.sub(r"\b3NEPET\b", "3N3 EPET", fixed, flags=re.IGNORECASE)
    if line_code == "3nflex-pla-plus" and not re.search(r"\b\d+(?:[,.]\d+)?\s*KG\b", fixed, flags=re.IGNORECASE):
        fixed = f"{fixed} x1kg"
    return fixed


def _soup(html_text: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html_text, "lxml")
    except Exception:
        return BeautifulSoup(html_text, "html.parser")


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())
