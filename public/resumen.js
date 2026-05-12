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
      <th>${productTitle(row.product)}</th>
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
  const weight = formatWeightLabel(product.weight_g);
  if (!weight) return product.display_name;
  return product.display_name.replace(` ${weight}`, "");
}

function matchesQuery(row) {
  if (!state.query) return true;
  const product = row.product;
  return [product.display_name, product.material, product.variant, product.color, product.brand].join(" ").toLowerCase().includes(state.query);
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
