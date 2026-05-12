const state = {
  products: [],
  sources: [],
  filters: {
    query: "",
    material: "",
    variant: "",
    color: "",
    diameter: "",
    weight: "",
    brand: "",
    provider: "",
    stock: "all",
  },
};

const filterIds = {
  material: "material-filter",
  variant: "variant-filter",
  color: "color-filter",
  diameter: "diameter-filter",
  weight: "weight-filter",
  brand: "brand-filter",
  provider: "provider-filter",
  stock: "stock-filter",
};

const lineMeta = {
  "PLA Standard": { label: "PLA Standard", help: "El PLA común: fácil de imprimir y el más buscado para piezas generales.", rank: 10 },
  "PLA+": { label: "PLA+", help: "PLA modificado: suele buscarse por mejor resistencia o terminación que el PLA común.", rank: 20 },
  "PETG": { label: "PETG", help: "Más tenaz y resistente a temperatura que PLA; útil para piezas funcionales.", rank: 30 },
  "ABS": { label: "ABS", help: "Material técnico para piezas resistentes; suele requerir cama caliente y buena ventilación.", rank: 40 },
  "TPU": { label: "TPU", help: "Flexible/elástico, usado para piezas que necesitan doblarse o absorber impacto.", rank: 50 },
  "Flex": { label: "Flex", help: "Línea flexible de 3N3; pensada para piezas blandas o elásticas.", rank: 51 },
  "Simpliflex": { label: "Simpliflex", help: "Flexible de Grilon3: alternativa elástica con impresión más amigable.", rank: 52 },
  "PLA Astra": { label: "PLA Astra · glitter/brillitos", help: "PLA con brillo tipo glitter. Ideal cuando importa la estética de la pieza.", rank: 60 },
  "PLA Silk": { label: "PLA Silk · efecto seda", help: "PLA de acabado brillante/sedoso, muy usado en piezas decorativas.", rank: 61 },
  "PLA Boutique": { label: "PLA Boutique · colores especiales", help: "Línea de colores especiales de Grilon3.", rank: 62 },
  "PLA Wood": { label: "PLA Wood · símil madera", help: "PLA con terminación tipo madera.", rank: 63 },
  "PLA 850": { label: "PLA 850 · técnico", help: "PLA de línea específica, distinto del PLA Standard.", rank: 70 },
  "PLA 870": { label: "PLA 870 · técnico", help: "PLA de línea específica, distinto del PLA Standard.", rank: 71 },
  "PLA Zeta": { label: "PLA Zeta · translúcido/especial", help: "Línea especial de Grilon3; no es PLA Standard.", rank: 72 },
  "PETG Clear": { label: "PETG Clear · translúcido", help: "PETG translúcido/clear para piezas donde importa el pasaje de luz.", rank: 80 },
  "E-PET": { label: "E-PET · PET reciclado", help: "PET reciclado. Distinto de PETG.", rank: 81 },
  "PP-T": { label: "PP-T · polipropileno", help: "Polipropileno técnico; útil por su resistencia química y flexibilidad.", rank: 90 },
  "Nylon 6": { label: "Nylon 6", help: "Nylon técnico para piezas exigentes.", rank: 100 },
  "Nylon 12": { label: "Nylon 12", help: "Nylon técnico con otra formulación; no mezclar con Nylon 6.", rank: 101 },
  "Acetal-POM": { label: "Acetal-POM", help: "Material técnico de baja fricción, usado en piezas mecánicas.", rank: 110 },
  "PVA Soluble": { label: "PVA soluble", help: "Material soluble, usualmente para soportes.", rank: 120 },
  "Sampler / lápiz 3D": { label: "Sampler / lápiz 3D", help: "Muestras cortas en metros, pensadas para lápiz 3D o prueba de material; no son bobinas.", rank: 130 },
};

const quickLineValues = ["PLA Standard", "PLA+", "PETG", "PLA Astra", "PLA Silk", "TPU"];

document.addEventListener("DOMContentLoaded", init);

async function init() {
  const response = await fetch("data/stock.json");
  const payload = await response.json();
  state.products = payload.products || [];
  state.sources = payload.sources || [];
  document.getElementById("last-update").textContent = `Última actualización: ${formatDate(payload.generated_at)}`;
  setupFilters();
  render();
}

function setupFilters() {
  setSelect("material", valuesFor("material"), "Material");
  setSelect("variant", lineValues(), "Línea");
  setSelect("color", valuesFor("color"), "Color");
  setSelect("diameter", valuesFor("diameter_mm").map((value) => [String(value), `${value} mm`]), "Diámetro");
  setSelect("weight", valuesFor("weight_g").map((value) => [String(value), `${Number(value) / 1000} kg`]), "Peso");
  setSelect("brand", valuesFor("brand"), "Marca");
  setSelect("provider", providerValues(), "Proveedor");
  setSelect("stock", [["all", "Todos"], ["in_stock", "Con stock"], ["out_of_stock", "Sin stock"], ["unknown", "Sin cantidad"]]);
  renderQuickLines();
  updateLineHelp();

  document.getElementById("search-input").addEventListener("input", (event) => {
    state.filters.query = event.target.value.toLowerCase().trim();
    render();
  });
  Object.entries(filterIds).forEach(([key, id]) => {
    document.getElementById(id).addEventListener("change", (event) => {
      state.filters[key] = event.target.value;
      if (key === "variant") updateLineHelp();
      render();
    });
  });
  document.getElementById("pla-shortcut").addEventListener("click", () => {
    state.filters.material = "PLA";
    document.getElementById("material-filter").value = "PLA";
    render();
  });
}

function render() {
  const products = state.products.filter(matchesFilters).sort(compareProducts);
  document.getElementById("result-count").textContent = `${products.length} productos`;
  document.getElementById("product-list").innerHTML = groupProducts(products).map(groupTemplate).join("");
  renderFooter();
}

function matchesFilters(product) {
  const queryText = [
    product.display_name,
    product.material,
    product.variant,
    product.color,
    product.pantone,
    product.sku,
    product.ean,
    product.brand,
    ...(product.offers || []).map((offer) => offer.original_name),
  ].join(" ").toLowerCase();

  if (state.filters.query && !queryText.includes(state.filters.query)) return false;
  if (state.filters.material && product.material !== state.filters.material) return false;
  if (state.filters.variant && lineLabel(product) !== state.filters.variant) return false;
  if (state.filters.color && product.color !== state.filters.color) return false;
  if (state.filters.diameter && String(product.diameter_mm) !== state.filters.diameter) return false;
  if (state.filters.weight && String(product.weight_g) !== state.filters.weight) return false;
  if (state.filters.brand && product.brand !== state.filters.brand) return false;
  if (state.filters.provider && !(product.offers || []).some((offer) => offer.provider_name === state.filters.provider)) return false;
  if (state.filters.stock !== "all" && !(product.offers || []).some((offer) => offer.stock_status === state.filters.stock)) return false;
  return true;
}

function productCardTemplate(card) {
  const product = card.products[0];
  const imageProduct = cardImageProduct(card.products);
  const titleText = productBaseName(product);
  const title = product.manufacturer_product_url
    ? `<a href="${escapeAttribute(product.manufacturer_product_url)}" target="_blank" rel="noopener">${escapeHtml(titleText)}</a>`
    : escapeHtml(titleText);
  const image = imageProduct.image_url
    ? `<img class="product-image" src="${escapeAttribute(imageProduct.image_url)}" alt="${escapeAttribute(productBaseName(imageProduct))}">`
    : colorSwatchTemplate(product);

  return `
    <article class="product-row">
      ${image}
      <div>
        <div class="product-head">
          <h2>${title}</h2>
        </div>
        <div class="chips">
          ${chip(product.material)}
          ${product.variant ? chip(product.variant) : ""}
          ${chip(product.color)}
          ${product.pantone ? chip(product.pantone) : ""}
          ${product.diameter_mm ? chip(`${product.diameter_mm} mm`) : ""}
          ${product.brand ? chip(product.brand) : ""}
        </div>
        <div class="presentation-list">${card.products.map(presentationTemplate).join("")}</div>
      </div>
    </article>
  `;
}

function cardImageProduct(products) {
  return products.find((product) => product.weight_g === 1000 && product.image_url)
    || products.find((product) => product.image_url)
    || products[0];
}

function colorSwatchTemplate(product) {
  return `
    <div class="product-image color-swatch" style="${escapeAttribute(colorSwatchStyle(product))}" role="img" aria-label="${escapeAttribute(product.color || "Sin color")}">
      <span>${escapeHtml(colorSwatchLabel(product.color))}</span>
    </div>
  `;
}

function colorSwatchStyle(product) {
  const color = product.color || "";
  const folded = foldText(color);
  if (folded.includes("KIT") || folded.includes("TUTTI") || folded.includes("SERIE LIMITADA")) {
    return "background: linear-gradient(135deg, #e53935, #fdd835 28%, #43a047 52%, #1e88e5 76%, #8e24aa);";
  }
  if (folded.includes("CLEAR") || folded.includes("CRISTAL") || folded.includes("TRANSPARENTE") || folded.includes("NATURAL")) {
    return `background: ${transparentSwatch(folded)};`;
  }
  if (folded.includes("FLUO") || folded.includes("UV GLOW")) {
    return `background: ${fluorescentSwatch(folded)};`;
  }
  if (folded.includes("ASTRA") || ["DARK", "JADE", "NEBULA", "NOCHE", "NOVA", "ROBY"].includes(folded)) {
    return `background: ${glitterSwatch(baseColorFor(folded))};`;
  }
  return `background: ${baseColorFor(folded)};`;
}

function transparentSwatch(folded) {
  const base = baseColorFor(folded);
  return `linear-gradient(135deg, rgba(255,255,255,.85), ${base}66), repeating-linear-gradient(45deg, #ffffff 0 6px, #d7d7dc 6px 12px)`;
}

function fluorescentSwatch(folded) {
  if (folded.includes("AMARILLO")) return "linear-gradient(135deg, #f4ff00, #fff86b)";
  if (folded.includes("NARANJA")) return "linear-gradient(135deg, #ff5a00, #ffb000)";
  if (folded.includes("VERDE")) return "linear-gradient(135deg, #39ff14, #b7ff00)";
  if (folded.includes("MAGENTA")) return "linear-gradient(135deg, #ff00cc, #ff5bea)";
  return "linear-gradient(135deg, #f4ff00, #39ff14)";
}

function glitterSwatch(base) {
  return `radial-gradient(circle at 24% 28%, rgba(255,255,255,.9) 0 1px, transparent 2px), radial-gradient(circle at 72% 36%, rgba(255,255,255,.75) 0 1px, transparent 2px), radial-gradient(circle at 44% 70%, rgba(255,255,255,.65) 0 1px, transparent 2px), ${base}`;
}

function baseColorFor(folded) {
  const rules = [
    ["BLANCO PERLA", "#f6f1df"],
    ["BLANCO", "#f8f8f2"],
    ["NEGRO", "#111111"],
    ["GRIS PLATA", "#b8bec6"],
    ["GRIS ACERO", "#8e98a3"],
    ["GRIS ESPACIAL", "#6f747b"],
    ["GRIS PLOMO", "#565b63"],
    ["GRIS", "#9ea3aa"],
    ["AZUL DE PRUSIA", "#003153"],
    ["AZUL TRAFUL", "#1976a3"],
    ["ZAFIRO", "#0f52ba"],
    ["AZUL", "#1f6feb"],
    ["VERDE MANZANA", "#8bc34a"],
    ["VERDE LIMA", "#9bdc28"],
    ["VERDE AVIADOR", "#4f6f52"],
    ["ESMERALDA", "#1f9d73"],
    ["PINO", "#2f5d50"],
    ["VERDE", "#2e7d32"],
    ["ROJO CARMIN", "#960018"],
    ["ROJO", "#d32f2f"],
    ["RUBI", "#9b111e"],
    ["BORDO", "#6d1a25"],
    ["ROBY", "#8e1233"],
    ["AMARILLO", "#f5c400"],
    ["NARANJA PRAGA", "#e87522"],
    ["NARANJA", "#f57c00"],
    ["FUCSIA", "#c2185b"],
    ["MAGENTA", "#d81b60"],
    ["ROSA", "#f3a6bd"],
    ["VIOLETA", "#7b3fb3"],
    ["UVA", "#6f2da8"],
    ["LILA", "#b58ad6"],
    ["LAVANDA", "#b7a0d8"],
    ["TURQUESA", "#00a6a6"],
    ["CALIPSO", "#00a9c7"],
    ["CELESTE", "#8ecae6"],
    ["ACQUA", "#7ddfd4"],
    ["DORADO", "#c9a227"],
    ["ORO", "#d4af37"],
    ["BRONCE", "#a97142"],
    ["COBRE", "#b87333"],
    ["PLATINO", "#c7c7c7"],
    ["TITANIO", "#7f7f7f"],
    ["CHOCOLATE", "#5d342f"],
    ["CAOBA", "#704214"],
    ["CEREZO", "#8d3f2d"],
    ["NOGAL", "#6f4e37"],
    ["CARPINCHO", "#9b7653"],
    ["DULCE DE LECHE", "#c6925b"],
    ["HABANO", "#8f6b4a"],
    ["ARENA", "#d6c6a8"],
    ["HUESO", "#e5dcc3"],
    ["PIEL", "#e3b38e"],
    ["SALMON", "#fa8072"],
    ["CREMA", "#f4e3bd"],
    ["PERLA CALIDO", "#eadfca"],
    ["PERLA FRIO", "#dbe3ea"],
    ["PERLA", "#e8e3d3"],
    ["CARBON", "#2f3437"],
    ["AZABACHE", "#161819"],
    ["DARK", "#1d1b2f"],
    ["NOCHE", "#13172b"],
    ["NEBULA", "#3a255f"],
    ["JADE", "#00a86b"],
    ["NOVA", "#4b3f72"],
    ["OPTICO", "#f8f8ff"],
    ["RUSTICO", "#a9825a"],
  ];
  const match = rules.find(([token]) => folded.includes(token));
  return match ? match[1] : "#d7d7dc";
}

function colorSwatchLabel(color) {
  if (!color) return "";
  return color.split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
}

function foldText(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
}

function presentationTemplate(product) {
  return `
    <section class="presentation-row">
      <header>
        <strong>${escapeHtml(formatPresentation(product) || "Presentación sin dato")}</strong>
      </header>
      <div class="offers">${offerListTemplate(product)}</div>
    </section>
  `;
}

function offerListTemplate(product) {
  const offers = product.offers || [];
  if (!offers.length) {
    return `<div class="offer stock-out">0 · sin stock online registrado</div>`;
  }
  return offers.map((offer) => offerTemplate(offer)).join("");
}

function offerTemplate(offer) {
  const stockClass = offer.stock_status === "in_stock" ? "stock-in" : offer.stock_status === "out_of_stock" ? "stock-out" : "stock-unknown";
  const stockLabel = offer.stock_status === "in_stock" ? `${offer.stock_quantity} carretes` : offer.stock_status === "out_of_stock" ? "0" : "0*";
  const reviewReason = offer.stock_status === "unknown" ? `<small class="review-reason">El proveedor seguramente no maneja esta variante.</small>` : "";
  return `
    <div class="offer">
      <div class="offer-main">
        <a href="#${escapeAttribute(providerAnchorId(offer.source_id))}">${escapeHtml(offer.provider_name)}</a>
        <span>${escapeHtml(offer.provider_zone)}</span>
        <strong class="${stockClass}">${escapeHtml(stockLabel)}</strong>
      </div>
      <small>${escapeHtml(offer.original_name)}</small>
      ${reviewReason}
    </div>
  `;
}

function renderFooter() {
  document.getElementById("site-footer").innerHTML = `
    <div class="footer-grid">
      ${state.sources.map(sourceFooter).join("")}
    </div>
  `;
}

function sourceFooter(source) {
  const stats = source.stats || {};
  const actions = [
    source.contact_whatsapp_url ? `<a href="${escapeAttribute(sourceWhatsappUrl(source))}" target="_blank" rel="noopener">WhatsApp</a>` : "",
    source.contact_phone ? `<a href="tel:${escapeAttribute(source.contact_phone.replaceAll(" ", ""))}">Teléfono</a>` : "",
    source.contact_email ? `<a href="mailto:${escapeAttribute(source.contact_email)}">Mail</a>` : "",
    source.source_url ? `<a href="${escapeAttribute(source.source_url)}" target="_blank" rel="noopener">Fuente</a>` : "",
  ].filter(Boolean).join("");
  return `
    <section class="footer-provider" id="${escapeAttribute(providerAnchorId(source.id))}">
      <h3><a href="${escapeAttribute(source.homepage_url)}" target="_blank" rel="noopener">${escapeHtml(source.name)}</a></h3>
      <p>${escapeHtml(source.zone)}${source.address ? ` · ${escapeHtml(source.address)}` : ""}</p>
      <p>${escapeHtml(stats.total_stock_units || 0)} carretes · ${escapeHtml(stats.product_count || 0)} productos</p>
      <p>Actualizado: ${escapeHtml(formatDate(source.last_success_at || source.last_attempt_at))}</p>
      <div class="contact-actions">${actions}</div>
    </section>
  `;
}

function sourceWhatsappUrl(source) {
  const separator = source.contact_whatsapp_url.includes("?") ? "&" : "?";
  return `${source.contact_whatsapp_url}${separator}text=${encodeURIComponent(whatsappMessage())}`;
}

function whatsappMessage() {
  const context = contactContext();
  const suffix = context ? ` Estoy buscando ${context}.` : " Quería consultar disponibilidad y precio.";
  return `Hola, vi su stock publicado en StockCentral.${suffix}`;
}

function contactContext() {
  const parts = [
    state.filters.query ? `"${state.filters.query}"` : "",
    state.filters.material,
    state.filters.variant,
    state.filters.color,
    state.filters.diameter ? `${state.filters.diameter} mm` : "",
    state.filters.weight ? formatWeightLabel(state.filters.weight) : "",
    state.filters.brand,
  ].filter(Boolean);
  return parts.join(", ");
}

function providerAnchorId(sourceId) {
  return `proveedor-${sourceId}`;
}

function groupProducts(products) {
  const groups = new Map();
  products.forEach((product) => {
    const key = [product.brand || "Sin marca", diameterLabel(product), lineLabel(product)].join("||");
    if (!groups.has(key)) {
      groups.set(key, {
        brand: product.brand || "Sin marca",
        diameter: diameterLabel(product),
        line: lineLabel(product),
        products: [],
      });
    }
    groups.get(key).products.push(product);
  });
  return [...groups.values()];
}

function groupTemplate(group) {
  return `
    <section class="group-section">
      <header class="group-heading">
        <span>${escapeHtml(group.brand)}</span>
        <span>${escapeHtml(group.diameter)}</span>
        <strong>${escapeHtml(group.line)}</strong>
      </header>
      <div class="group-products">${groupBaseProducts(group.products).map(productCardTemplate).join("")}</div>
    </section>
  `;
}

function groupBaseProducts(products) {
  const cards = new Map();
  products.forEach((product) => {
    const key = [
      product.brand || "Sin marca",
      product.diameter_mm || "Sin diámetro",
      lineLabel(product),
      product.material || "Sin material",
      product.variant || "",
      product.color || "Sin color",
    ].join("||");
    if (!cards.has(key)) cards.set(key, { products: [] });
    cards.get(key).products.push(product);
  });
  return [...cards.values()].map((card) => {
    card.products.sort(comparePresentations);
    return card;
  });
}

function lineLabel(product) {
  if (isSamplerProduct(product)) return "Sampler / lápiz 3D";
  if (!product.variant && product.material === "PLA") return "PLA Standard";
  return product.variant || product.material || "Sin clasificar";
}

function isSamplerProduct(product) {
  return Boolean(samplerLengthLabel(product));
}

function formatPresentation(product) {
  const weight = formatWeightLabel(product.weight_g);
  if (weight) return weight;

  const samplerLength = samplerLengthLabel(product);
  if (samplerLength) return `Sampler ${samplerLength}`;

  return "";
}

function samplerLengthLabel(product) {
  const names = (product.offers || []).map((offer) => offer.original_name).join(" ");
  const match = names.match(/\bSAMPLER\b.*?\bX\s*(\d+(?:[,.]\d+)?)\s*M\b/i);
  if (!match) return "";
  return `${match[1].replace(",", ".")} m`;
}

function diameterLabel(product) {
  return product.diameter_mm ? `${product.diameter_mm} mm` : "Sin diámetro";
}

function compareProducts(left, right) {
  return [
    brandRank(left.brand),
    left.brand || "",
    diameterLabel(left),
    lineLabel(left),
    left.color || "",
    left.display_name,
  ].join(" ").localeCompare([
    brandRank(right.brand),
    right.brand || "",
    diameterLabel(right),
    lineLabel(right),
    right.color || "",
    right.display_name,
  ].join(" "), "es-AR");
}

function comparePresentations(left, right) {
  return presentationRank(left) - presentationRank(right) || left.display_name.localeCompare(right.display_name, "es-AR");
}

function presentationRank(product) {
  if (Number.isFinite(Number(product.weight_g)) && Number(product.weight_g) > 0) return Number(product.weight_g);
  if (isSamplerProduct(product)) return 10_000_000;
  return 20_000_000;
}

function productBaseName(product) {
  const presentation = formatWeightLabel(product.weight_g);
  if (!presentation) return product.display_name;
  return product.display_name.replace(` ${presentation}`, "").replace(/\s+/g, " ").trim();
}

function brandRank(brand) {
  if (brand === "Grilon3") return "0";
  if (brand === "3N3") return "1";
  return "9";
}

function setSelect(key, values, emptyLabel = "") {
  const select = document.getElementById(filterIds[key]);
  const normalized = values.map((value) => {
    if (Array.isArray(value)) return value;
    return [value, key === "variant" ? lineOptionLabel(value) : value];
  });
  const options = emptyLabel ? [["", emptyLabel], ...normalized] : normalized;
  select.innerHTML = options.map(([value, label]) => `<option value="${escapeAttribute(value)}">${escapeHtml(label)}</option>`).join("");
}

function valuesFor(field) {
  return [...new Set(state.products.map((product) => product[field]).filter((value) => value !== "" && value !== null && value !== undefined))].sort();
}

function providerValues() {
  return [...new Set(state.products.flatMap((product) => (product.offers || []).map((offer) => offer.provider_name)))].sort();
}

function lineValues() {
  return [...new Set(state.products.map(lineLabel).filter(Boolean))].sort((left, right) => {
    return lineRank(left) - lineRank(right) || left.localeCompare(right, "es-AR");
  });
}

function lineOptionLabel(line) {
  return lineMeta[line]?.label || line;
}

function lineRank(line) {
  return lineMeta[line]?.rank ?? 999;
}

function updateLineHelp() {
  const line = state.filters.variant;
  const help = document.getElementById("line-help");
  if (!line) {
    help.textContent = "Líneas más usadas: PLA Standard, PLA+, PETG y flexibles. Algunas líneas especiales tienen descripción para elegir sin adivinar.";
    return;
  }
  help.textContent = lineMeta[line]?.help || `${line}: línea/material detectado desde las fuentes de stock.`;
}

function renderQuickLines() {
  const available = new Set(lineValues());
  const buttons = quickLineValues
    .filter((line) => available.has(line))
    .map((line) => `<button class="quick-line" type="button" data-line="${escapeAttribute(line)}">${escapeHtml(lineOptionLabel(line))}</button>`);
  document.getElementById("quick-lines").innerHTML = buttons.join("");
  document.querySelectorAll(".quick-line").forEach((button) => {
    button.addEventListener("click", () => {
      state.filters.variant = button.dataset.line || "";
      document.getElementById("variant-filter").value = state.filters.variant;
      updateLineHelp();
      render();
    });
  });
}

function formatWeightLabel(weightG) {
  if (!weightG) return "";
  return `${Number(weightG) / 1000} kg`;
}

function chip(value) {
  return `<span class="chip">${escapeHtml(value)}</span>`;
}

function formatDate(value) {
  if (!value) return "Sin datos";
  return new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
