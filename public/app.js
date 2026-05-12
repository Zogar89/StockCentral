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
  setSelect("stock", [["all", "Todos"], ["in_stock", "Con stock"], ["out_of_stock", "Sin stock"], ["unknown", "A revisar"]]);
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

function productTemplate(product) {
  const title = product.manufacturer_product_url
    ? `<a href="${escapeAttribute(product.manufacturer_product_url)}" target="_blank" rel="noopener">${escapeHtml(product.display_name)}</a>`
    : escapeHtml(product.display_name);
  const image = product.image_url
    ? `<img class="product-image" src="${escapeAttribute(product.image_url)}" alt="${escapeAttribute(product.display_name)}">`
    : `<div class="product-image image-placeholder">Sin imagen</div>`;

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
          ${product.diameter_mm ? chip(`${product.diameter_mm} mm`) : ""}
          ${product.weight_g ? chip(`${product.weight_g / 1000} kg`) : ""}
          ${product.brand ? chip(product.brand) : ""}
        </div>
        <div class="offers">${offerListTemplate(product)}</div>
      </div>
    </article>
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
  const stockLabel = offer.stock_status === "in_stock" ? `${offer.stock_quantity} carretes` : offer.stock_status === "out_of_stock" ? "0" : "A revisar";
  const reviewReason = offer.stock_status === "unknown" ? `<small class="review-reason">La fuente no publicó una cantidad numérica.</small>` : "";
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
    source.contact_whatsapp_url ? `<a href="${escapeAttribute(source.contact_whatsapp_url)}" target="_blank" rel="noopener">WhatsApp</a>` : "",
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
      <div class="group-products">${group.products.map(productTemplate).join("")}</div>
    </section>
  `;
}

function lineLabel(product) {
  if (!product.variant && product.material === "PLA") return "PLA Standard";
  return product.variant || product.material || "Sin clasificar";
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
