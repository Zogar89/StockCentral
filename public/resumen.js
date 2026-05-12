const state = {
  products: [],
  sources: [],
  rows: [],
  query: "",
};

const zoneOrder = {
  "Zona Norte": 0,
  "Zona Oeste": 1,
  "Zona Sur": 2,
};

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
  render();
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
        <td class="summary-presentation"></td>
        ${state.sources.map((source) => `<td class="summary-total">${formatInteger(providerTotals[source.id])}</td>`).join("")}
        <td class="summary-total">${formatInteger(grandTotal)}</td>
      </tr>
    </tfoot>
  `;
}

function groupRows(rows) {
  const groups = new Map();
  rows.forEach((row) => {
    const key = groupKey(row.product);
    if (!groups.has(key)) {
      groups.set(key, {
        title: groupTitle(row.product),
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
  return [...groups.values()];
}

function groupTemplate(group) {
  return `
    <tr class="summary-group-row">
      <th>${escapeHtml(group.title)}</th>
      <td class="summary-presentation"></td>
      ${state.sources.map((source) => `<td>${formatInteger(group.totals[source.id])}</td>`).join("")}
      <td class="summary-total">${formatInteger(group.total)}</td>
    </tr>
    ${group.rows.map(rowTemplate).join("")}
  `;
}

function sourceHeader(source) {
  const total = source.stats?.total_stock_units ?? 0;
  return `<th><a href="${escapeAttribute(source.homepage_url)}" target="_blank" rel="noopener" title="${formatInteger(total)} carretes">${escapeHtml(source.name)}</a></th>`;
}

function rowTemplate(row) {
  return `
    <tr>
      <th>${summaryProductTemplate(row.product)}</th>
      <td class="summary-presentation">${escapeHtml(formatPresentation(row.product))}</td>
      ${state.sources.map((source) => cellTemplate(row.cells[source.id])).join("")}
      <td class="summary-total">${formatInteger(row.total)}</td>
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
  return [
    product.brand || "Sin marca",
    product.diameter_mm ? `${product.diameter_mm} mm` : "Sin diámetro",
    lineLabel(product),
  ].join(" · ");
}

function cellTemplate(cell) {
  if (!cell) return `<td class="stock-out">0</td>`;
  if (cell.units > 0) return `<td class="stock-in">${formatInteger(cell.units)}</td>`;
  if (cell.unknown) return `<td class="stock-unknown" title="El proveedor seguramente no maneja esta variante">0*</td>`;
  return `<td class="stock-out">0</td>`;
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

function summaryProductTemplate(product) {
  const pantone = product.pantone ? `<small>${escapeHtml(product.pantone)}</small>` : "";
  return `
    <span class="summary-product">
      ${summaryColorSwatchTemplate(product)}
      <span class="summary-product-name">
        ${productTitle(product)}
        ${pantone}
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
  const product = row.product;
  return [product.display_name, product.material, product.variant, product.color, product.pantone, product.brand].join(" ").toLowerCase().includes(state.query);
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
