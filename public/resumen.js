const state = {
  products: [],
  sources: [],
  rows: [],
  query: "",
  categoryOrder: "popular",
};

let stickyGroupRowsReady = false;

const lineRanks = {
  "PLA Standard": 10,
  "PLA+": 20,
  "PLA Flexible": 25,
  PETG: 30,
  ABS: 40,
  TPU: 50,
  Flex: 51,
  Simpliflex: 52,
  "PLA Astra": 60,
  "PLA Silk": 61,
  "PLA Boutique": 62,
  "PLA Wood": 63,
  "PLA 850": 70,
  "PLA 870": 71,
  "PLA Zeta": 72,
  "PETG Clear": 80,
  "E-PET": 81,
  "PP-T": 90,
  "Nylon 6": 100,
  "Nylon 12": 101,
  "Acetal-POM": 110,
  "PVA Soluble": 120,
  "Sampler / lápiz 3D": 130,
};

const lineMeta = {
  "PLA Standard": { label: "PLA Standard", quickLabel: "PLA", quickTone: "pla", help: "PLA común: fácil de imprimir y el más buscado para piezas generales." },
  "PLA+": { label: "PLA+", quickLabel: "PLA+", quickTone: "plus", help: "PLA modificado: suele buscarse por mejor resistencia o terminación." },
  "PLA Flexible": { label: "PLA Flexible", quickLabel: "Flex", quickTone: "flex", help: "PLA+ flexible de 3N3/3NFLEX: piezas con algo de elasticidad." },
  PETG: { label: "PETG", quickLabel: "PETG", quickTone: "petg", help: "Más tenaz y resistente a temperatura que PLA; útil para piezas funcionales." },
  TPU: { label: "TPU", quickLabel: "TPU", quickTone: "flex", help: "Flexible/elástico, usado para piezas que necesitan doblarse o absorber impacto." },
  "PLA Astra": { label: "PLA Astra", quickLabel: "Astra", quickTone: "astra", help: "PLA con brillo tipo glitter. Ideal cuando importa la estética de la pieza." },
  "PLA Silk": { label: "PLA Silk", quickLabel: "Silk", quickTone: "silk", help: "PLA de acabado brillante/sedoso, muy usado en piezas decorativas." },
  "PLA Wood": { label: "PLA Wood", quickLabel: "Wood", quickTone: "wood", help: "PLA con terminación tipo madera." },
};

const quickLineValues = ["PLA Standard", "PLA+", "PLA Flexible", "PETG", "PLA Astra", "PLA Silk", "PLA Wood", "TPU"];

const zoneOrder = {
  "Zona Norte": 0,
  "Zona Oeste": 1,
  "Zona Sur": 2,
};

const siteContactUrl = "https://github.com/Zogar89/StockCentral/issues/new";
const siteRepoUrl = "https://github.com/Zogar89/StockCentral";

document.addEventListener("DOMContentLoaded", init);

async function init() {
  const response = await fetch("data/stock.json");
  const payload = await response.json();
  state.products = payload.products || [];
  state.sources = [...(payload.sources || [])].sort((a, b) => {
    return (zoneOrder[a.zone] ?? 99) - (zoneOrder[b.zone] ?? 99) || a.name.localeCompare(b.name, "es-AR");
  });
  state.rows = buildRows();
  document.getElementById("summary-updated").textContent = `Última actualización: ${formatDate(payload.generated_at)}`;
  document.getElementById("summary-search").addEventListener("input", (event) => {
    state.query = event.target.value.toLowerCase().trim();
    render();
  });
  setupCategorySort();
  renderQuickLines();
  render();
  renderSiteFooter();
}

function renderSiteFooter() {
  const footer = document.getElementById("site-footer");
  if (!footer) return;

  footer.innerHTML = `
    <section class="footer-meta" aria-label="Información del proyecto">
      <div>
        <h2>StockCentral</h2>
        <p>Creado por Gabriel (Zogar89) para impresores 3D del AMBA.</p>
        <p>Si encontrás un error de stock, una foto incorrecta o querés sumar tu proveedor al listado, avisame por GitHub.</p>
      </div>
      <div class="contact-actions">
        <a href="${escapeAttribute(siteContactUrl)}" target="_blank" rel="noopener">Reportar error</a>
        <a href="${escapeAttribute(siteContactUrl)}" target="_blank" rel="noopener">Sumar proveedor</a>
        <a href="${escapeAttribute(siteRepoUrl)}" target="_blank" rel="noopener">Repositorio</a>
      </div>
    </section>
  `;
}

function buildRows() {
  return state.products.map((product) => {
    const cells = Object.fromEntries(state.sources.map((source) => [source.id, { units: 0, unknown: false }]));
    (product.offers || []).forEach((offer) => {
      const cell = cells[offer.source_id];
      if (!cell) return;
      if (Number.isFinite(Number(offer.stock_quantity)) && Number(offer.stock_quantity) > 0) {
        cell.units += Number(offer.stock_quantity);
      } else if (offer.stock_status === "unknown") {
        cell.unknown = true;
      }
    });
    const total = Object.values(cells).reduce((sum, cell) => sum + cell.units, 0);
    return { product, cells, total };
  }).sort((a, b) => compareProducts(a.product, b.product));
}

function render() {
  const rows = state.rows.filter(matchesQuery);
  const providerTotals = Object.fromEntries(state.sources.map((source) => [source.id, 0]));
  rows.forEach((row) => {
    state.sources.forEach((source) => {
      providerTotals[source.id] += row.cells[source.id]?.units || 0;
    });
  });
  const grandTotal = Object.values(providerTotals).reduce((sum, value) => sum + value, 0);
  const groupedRows = groupRows(rows);
  document.getElementById("summary-count").textContent = `${rows.length} filamentos`;
  updateCategorySortButtons();
  document.getElementById("summary-table").innerHTML = `
    <thead>
      <tr>
        <th>Filamento</th>
        <th class="summary-presentation">Presentación</th>
        ${state.sources.map(sourceHeader).join("")}
        <th class="summary-total">Total</th>
      </tr>
    </thead>
    <tbody>${groupedRows.map(groupTemplate).join("")}</tbody>
    <tfoot>
      <tr>
        <th>Carretes por proveedor</th>
        <td class="summary-presentation" data-label="Presentación"></td>
        ${state.sources.map((source) => `<td class="summary-total" data-label="${escapeAttribute(source.name)}">${formatInteger(providerTotals[source.id])}</td>`).join("")}
        <td class="summary-total" data-label="Total">${formatInteger(grandTotal)}</td>
      </tr>
    </tfoot>
  `;
  setupStickyGroupRows();
}

function groupRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = groupKey(row.product);
    if (!groups.has(key)) {
      groups.set(key, {
        title: groupTitle(row.product),
        brand: row.product.brand || "Sin marca",
        diameter: row.product.diameter_mm ? `${row.product.diameter_mm} mm` : "Sin diámetro",
        line: lineLabel(row.product),
        rows: [],
        totals: Object.fromEntries(state.sources.map((source) => [source.id, 0])),
        total: 0,
      });
    }
    const group = groups.get(key);
    group.rows.push(row);
    state.sources.forEach((source) => {
      group.totals[source.id] += row.cells[source.id]?.units || 0;
    });
    group.total += row.total;
  });
  return [...groups.values()].sort(compareGroups);
}

function setupCategorySort() {
  document.querySelectorAll("[data-category-order]").forEach((button) => {
    button.addEventListener("click", () => {
      state.categoryOrder = button.dataset.categoryOrder || "popular";
      render();
    });
  });
}

function updateCategorySortButtons() {
  document.querySelectorAll("[data-category-order]").forEach((button) => {
    button.classList.toggle("active", button.dataset.categoryOrder === state.categoryOrder);
  });
}

function compareGroups(left, right) {
  if (state.categoryOrder === "alpha") {
    return left.title.localeCompare(right.title, "es-AR");
  }

  return (
    lineRank(left.line) - lineRank(right.line)
    || brandRank(left.brand).localeCompare(brandRank(right.brand), "es-AR")
    || left.diameter.localeCompare(right.diameter, "es-AR")
    || left.title.localeCompare(right.title, "es-AR")
  );
}

function groupTemplate(group) {
  const targetId = summaryGroupTargetId(group);
  return `
    <tr class="summary-group-row" id="${escapeAttribute(targetId)}" data-line="${escapeAttribute(group.line)}">
      <th>
        ${escapeHtml(group.title)}
        ${mobileProviderTotalsTemplate(group.totals, group.total)}
      </th>
      <td class="summary-presentation" data-label="Presentación"></td>
      ${state.sources.map((source) => `<td data-label="${escapeAttribute(source.name)}">${formatInteger(group.totals[source.id])}</td>`).join("")}
      <td class="summary-total" data-label="Total">${formatInteger(group.total)}</td>
    </tr>
    ${group.rows.map(rowTemplate).join("")}
  `;
}

function renderQuickLines() {
  const available = new Set(state.products.map(lineLabel).filter(Boolean));
  const buttons = quickLineValues
    .filter((line) => available.has(line))
    .map((line) => quickLineButtonTemplate(line));
  document.getElementById("summary-quick-lines").innerHTML = buttons.join("");
  document.querySelectorAll("#summary-quick-lines .quick-line").forEach((button) => {
    button.addEventListener("click", () => {
      scrollToQuickLine(button.dataset.line || "");
    });
  });
}

function quickLineButtonTemplate(line) {
  const label = quickLineLabel(line);
  const hint = quickLineHint(line);
  const tone = lineMeta[line]?.quickTone || "default";
  return `
    <button class="quick-line quick-line-${escapeAttribute(tone)}" type="button" data-line="${escapeAttribute(line)}" title="${escapeAttribute(hint)}" aria-label="${escapeAttribute(`${label}. ${hint}`)}">
      <span>${escapeHtml(label)}</span>
    </button>
  `;
}

function quickLineLabel(line) {
  return lineMeta[line]?.quickLabel || line;
}

function quickLineHint(line) {
  return lineMeta[line]?.help || `${line}: línea/material detectado desde las fuentes de stock.`;
}

function scrollToQuickLine(line) {
  const target = [...document.querySelectorAll(".summary-group-row")].find((row) => row.dataset.line === line);
  const help = document.getElementById("summary-line-help");
  help.textContent = "";

  if (!target) {
    help.textContent = `No hay resultados visibles para ${quickLineLabel(line)} con la búsqueda actual.`;
    return;
  }

  document.querySelectorAll(".summary-group-row.quick-target").forEach((row) => row.classList.remove("quick-target"));
  target.classList.add("quick-target");
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  window.setTimeout(() => target.classList.remove("quick-target"), 1400);
}

function mobileProviderTotalsTemplate(totals, total) {
  return `
    <span class="summary-mobile-totals" aria-hidden="true">
      ${state.sources.map((source) => `
        <span><b>${escapeHtml(source.name)}</b> ${formatInteger(totals[source.id])}</span>
      `).join("")}
      <span class="summary-mobile-total"><b>Total</b> ${formatInteger(total)}</span>
    </span>
  `;
}

function setupStickyGroupRows() {
  updateStickyGroupRows();
  if (stickyGroupRowsReady) return;

  stickyGroupRowsReady = true;
  window.addEventListener("scroll", updateStickyGroupRows, { passive: true });
  window.addEventListener("resize", updateStickyGroupRows);
}

function updateStickyGroupRows() {
  const stickyTop = summaryStickyTop();
  document.querySelectorAll(".summary-group-row").forEach((row) => {
    const rect = row.getBoundingClientRect();
    row.classList.toggle("is-stuck", rect.top <= stickyTop + 1 && rect.bottom > stickyTop);
  });
}

function summaryStickyTop() {
  const styles = getComputedStyle(document.documentElement);
  const quickLinesHeight = parseFloat(styles.getPropertyValue("--quick-lines-height")) || 0;
  const summaryHeadHeight = parseFloat(styles.getPropertyValue("--summary-head-height")) || 0;
  if (window.matchMedia("(max-width: 820px)").matches) return quickLinesHeight;
  return quickLinesHeight + summaryHeadHeight;
}

function sourceHeader(source) {
  const total = source.stats?.total_stock_units ?? 0;
  return `<th><a href="${escapeAttribute(source.homepage_url)}" target="_blank" rel="noopener" title="${formatInteger(total)} carretes">${escapeHtml(source.name)}</a></th>`;
}

function rowTemplate(row) {
  return `
    <tr>
      <th>${summaryProductTemplate(row)}</th>
      <td class="summary-presentation" data-label="Presentación">${escapeHtml(formatPresentation(row.product))}</td>
      ${state.sources.map((source) => cellTemplate(row.cells[source.id], source)).join("")}
      <td class="summary-total" data-label="Total">${formatInteger(row.total)}</td>
    </tr>
  `;
}

function groupKey(product) {
  return [
    brandRank(product.brand),
    product.brand || "Sin marca",
    product.diameter_mm ? `${product.diameter_mm} mm` : "Sin diámetro",
    lineLabel(product),
  ].join("||");
}

function groupTitle(product) {
  const parts = [
    product.brand || "Sin marca",
    product.diameter_mm ? `${product.diameter_mm} mm` : "Sin diámetro",
    lineLabel(product),
  ].filter(Boolean);
  return parts.join(" · ");
}

function summaryGroupTargetId(group) {
  return `resumen-linea-${slugText(group.title)}`;
}

function cellTemplate(cell, source) {
  const label = escapeAttribute(source.name);
  if (!cell) return `<td class="stock-out" data-label="${label}">0</td>`;
  if (cell.units > 0) return `<td class="stock-in" data-label="${label}">${formatInteger(cell.units)}</td>`;
  if (cell.unknown) return `<td class="stock-out" data-label="${label}">0</td>`;
  return `<td class="stock-out" data-label="${label}">0</td>`;
}

function productTitle(product) {
  const label = escapeHtml(productSummaryName(product));
  if (!product.manufacturer_product_url) return label;
  return `<a href="${escapeAttribute(product.manufacturer_product_url)}" target="_blank" rel="noopener">${label}</a>`;
}

function productSummaryName(product) {
  if (product.color && product.color !== "Sin color") return product.color;

  const repeatedParts = [
    product.brand,
    product.diameter_mm ? `${product.diameter_mm} mm` : "",
    formatPresentation(product),
    lineLabel(product),
    product.material,
  ].filter(Boolean);
  return repeatedParts.reduce((name, part) => {
    return name.replace(part, "").replace(/\s+/g, " ").trim();
  }, product.display_name) || product.display_name;
}

function summaryProductTemplate(row) {
  const product = row.product;
  const details = [product.pantone].filter(Boolean).join(" · ");
  const detail = details ? `<small>${escapeHtml(details)}</small>` : "";
  return `
    <span class="summary-product">
      ${summaryColorSwatchTemplate(product)}
      <span class="summary-product-name">
        ${productTitle(product)}
        ${detail}
      </span>
    </span>
  `;
}

function summaryColorSwatchTemplate(product) {
  const title = [product.color || "Sin color", product.pantone].filter(Boolean).join(" · ");
  return `
    <span class="summary-color-swatch" style="${escapeAttribute(colorSwatchStyle(product))}" title="${escapeAttribute(title)}" aria-label="${escapeAttribute(title)}">
    </span>
  `;
}

function matchesQuery(row) {
  if (!state.query) return true;
  const products = row.products || [row.product];
  return products.some((product) => {
    return matchesSearchTerms(state.query, [product.display_name, product.material, product.variant, product.color, product.pantone, product.brand]);
  });
}

function matchesSearchTerms(query, values) {
  const tokens = searchTokens(values.join(" "));
  return searchTokens(query).every((term) => {
    return tokens.some((token) => matchesSearchToken(term, token));
  });
}

function matchesSearchToken(term, token) {
  if (term === "pla") return token === "pla" || token === "pla+";
  return token === term || token.startsWith(term);
}

function searchTokens(value) {
  return foldText(value)
    .toLowerCase()
    .split(/[^a-z0-9+]+/)
    .filter(Boolean);
}

function compareProducts(left, right) {
  return [
    brandRank(left.brand),
    left.brand || "",
    left.diameter_mm ? `${left.diameter_mm} mm` : "Sin diámetro",
    lineLabel(left),
    left.color || "",
    left.display_name,
  ].join(" ").localeCompare([
    brandRank(right.brand),
    right.brand || "",
    right.diameter_mm ? `${right.diameter_mm} mm` : "Sin diámetro",
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

function lineRank(line) {
  return lineRanks[line] ?? 999;
}

function lineLabel(product) {
  if (isSamplerProduct(product)) return "Sampler / lápiz 3D";
  if (!product.variant && product.material === "PLA") return "PLA Standard";
  return product.variant || product.material || "Sin clasificar";
}

function isSamplerProduct(product) {
  return Boolean(samplerLengthLabel(product));
}

function formatInteger(value) {
  return Number(value || 0).toLocaleString("es-AR");
}

function formatWeightLabel(weightG) {
  if (!weightG) return "";
  return `${Number(weightG) / 1000} kg`;
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

function colorSwatchStyle(product) {
  const color = product.color || "";
  const folded = foldText(color);
  const variant = foldText(product.variant || "");
  if (folded.includes("KIT") || folded.includes("TUTTI") || folded.includes("SERIE LIMITADA")) {
    return "background: linear-gradient(135deg, #e53935, #fdd835 28%, #43a047 52%, #1e88e5 76%, #8e24aa);";
  }
  if (folded.includes("CLEAR") || folded.includes("CRISTAL") || folded.includes("TRANSPARENTE") || folded.includes("NATURAL")) {
    return `background: ${transparentSwatch(folded)};`;
  }
  if (folded.includes("FLUO") || folded.includes("UV GLOW")) {
    return `background: ${fluorescentSwatch(folded)};`;
  }
  if (variant.includes("ASTRA") || folded.includes("ASTRA") || ["DARK", "JADE", "NEBULA", "NOCHE", "NOVA", "ROBY"].includes(folded)) {
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

function foldText(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
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

function slugText(value) {
  return foldText(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
