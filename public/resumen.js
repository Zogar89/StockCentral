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
  document.getElementById("summary-count").textContent = `${rows.length} filamentos`;
  document.getElementById("summary-table").innerHTML = `
    <thead>
      <tr>
        <th>Filamento</th>
        ${state.sources.map(sourceHeader).join("")}
        <th class="summary-total">Total</th>
      </tr>
    </thead>
    <tbody>${rows.map(rowTemplate).join("")}</tbody>
    <tfoot>
      <tr>
        <th>Carretes por proveedor</th>
        ${state.sources.map((source) => `<td class="summary-total">${formatInteger(providerTotals[source.id])}</td>`).join("")}
        <td class="summary-total">${formatInteger(grandTotal)}</td>
      </tr>
    </tfoot>
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
      ${state.sources.map((source) => cellTemplate(row.cells[source.id])).join("")}
      <td class="summary-total">${formatInteger(row.total)}</td>
    </tr>
  `;
}

function cellTemplate(cell) {
  if (!cell) return `<td class="stock-out">0</td>`;
  if (cell.units > 0) return `<td class="stock-in">${formatInteger(cell.units)}</td>`;
  if (cell.unknown) return `<td class="stock-unknown">Rev.</td>`;
  return `<td class="stock-out">0</td>`;
}

function productTitle(product) {
  const label = escapeHtml(product.display_name);
  if (!product.manufacturer_product_url) return label;
  return `<a href="${escapeAttribute(product.manufacturer_product_url)}" target="_blank" rel="noopener">${label}</a>`;
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
  if (!product.variant && product.material === "PLA") return "PLA Standard";
  return product.variant || product.material || "Sin clasificar";
}

function formatInteger(value) {
  return Number(value || 0).toLocaleString("es-AR");
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
