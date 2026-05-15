<script>
  import { afterUpdate, onMount } from "svelte";
  import QuickLines from "./components/QuickLines.svelte";
  import SiteFooter from "./components/SiteFooter.svelte";
  import {
    brandRank,
    colorSwatchStyle,
    fetchJson,
    formatDate,
    formatInteger,
    formatPresentation,
    lineLabel,
    lineRank,
    matchesSearchTerms,
    slugText,
    stockDelta,
    zoneOrder,
  } from "./lib/shared.js";

  let products = [];
  let sources = [];
  let rows = [];
  let generatedAt = "";
  let query = "";
  let categoryOrder = "popular";
  let lineHelp = "";
  let stickyReady = false;

  onMount(async () => {
    const payload = await fetchJson("data/stock.json", { products: [], sources: [] });
    products = payload.products || [];
    sources = [...(payload.sources || [])].sort((a, b) => (zoneOrder[a.zone] ?? 99) - (zoneOrder[b.zone] ?? 99) || a.name.localeCompare(b.name, "es-AR"));
    generatedAt = payload.generated_at || "";
    rows = buildRows();
    window.addEventListener("scroll", updateStickyGroupRows, { passive: true });
    window.addEventListener("resize", updateStickyGroupRows);
    return () => {
      window.removeEventListener("scroll", updateStickyGroupRows);
      window.removeEventListener("resize", updateStickyGroupRows);
    };
  });

  afterUpdate(() => {
    if (!stickyReady) stickyReady = true;
    updateStickyGroupRows();
  });

  $: visibleRows = rows.filter(matchesQuery);
  $: providerTotals = totalsForRows(visibleRows);
  $: grandTotal = Object.values(providerTotals).reduce((sum, value) => sum + value, 0);
  $: groupedRows = groupRows(visibleRows);
  $: availableLines = [...new Set(products.map(lineLabel).filter(Boolean))];

  function buildRows() {
    return products.map((product) => {
      const cells = Object.fromEntries(sources.map((source) => [source.id, { units: 0, unknown: false }]));
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

  function totalsForRows(items) {
    const totals = Object.fromEntries(sources.map((source) => [source.id, 0]));
    items.forEach((row) => {
      sources.forEach((source) => {
        totals[source.id] += row.cells[source.id]?.units || 0;
      });
    });
    return totals;
  }

  function groupRows(items) {
    const groups = new Map();
    items.forEach((row) => {
      const key = groupKey(row.product);
      if (!groups.has(key)) {
        groups.set(key, {
          title: groupTitle(row.product),
          brand: row.product.brand || "Sin marca",
          diameter: row.product.diameter_mm ? `${row.product.diameter_mm} mm` : "Sin diámetro",
          line: lineLabel(row.product),
          rows: [],
          totals: Object.fromEntries(sources.map((source) => [source.id, 0])),
          total: 0,
        });
      }
      const group = groups.get(key);
      group.rows.push(row);
      sources.forEach((source) => {
        group.totals[source.id] += row.cells[source.id]?.units || 0;
      });
      group.total += row.total;
    });
    return [...groups.values()].sort(compareGroups);
  }

  function groupKey(product) {
    return [brandRank(product.brand), product.brand || "Sin marca", product.diameter_mm ? `${product.diameter_mm} mm` : "Sin diámetro", lineLabel(product)].join("||");
  }

  function groupTitle(product) {
    return [product.brand || "Sin marca", product.diameter_mm ? `${product.diameter_mm} mm` : "Sin diámetro", lineLabel(product)].filter(Boolean).join(" · ");
  }

  function compareGroups(left, right) {
    if (categoryOrder === "alpha") return left.title.localeCompare(right.title, "es-AR");
    return lineRank(left.line) - lineRank(right.line)
      || brandRank(left.brand).localeCompare(brandRank(right.brand), "es-AR")
      || left.diameter.localeCompare(right.diameter, "es-AR")
      || left.title.localeCompare(right.title, "es-AR");
  }

  function compareProducts(left, right) {
    return [
      brandRank(left.brand), left.brand || "", left.diameter_mm ? `${left.diameter_mm} mm` : "Sin diámetro", lineLabel(left), left.color || "", left.display_name,
    ].join(" ").localeCompare([
      brandRank(right.brand), right.brand || "", right.diameter_mm ? `${right.diameter_mm} mm` : "Sin diámetro", lineLabel(right), right.color || "", right.display_name,
    ].join(" "), "es-AR");
  }

  function matchesQuery(row) {
    if (!query) return true;
    return matchesSearchTerms(query.toLowerCase().trim(), [row.product.display_name, row.product.material, row.product.variant, row.product.color, row.product.pantone, row.product.brand]);
  }

  function productSummaryName(product) {
    if (product.color && product.color !== "Sin color") return product.color;
    const repeatedParts = [product.brand, product.diameter_mm ? `${product.diameter_mm} mm` : "", formatPresentation(product), lineLabel(product), product.material].filter(Boolean);
    return repeatedParts.reduce((name, part) => name.replace(part, "").replace(/\s+/g, " ").trim(), product.display_name) || product.display_name;
  }

  function summaryGroupTargetId(group) {
    return `resumen-linea-${slugText(group.title)}`;
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
</script>

<main class="shell">
  <header class="topbar">
    <div>
      <p class="eyebrow">Resumen por proveedor</p>
      <h1>Central de Filamentos</h1>
    </div>
    <nav class="view-switch" aria-label="Cambiar vista">
      <a class="nav-link" href="index.html">Catálogo</a>
      <a class="nav-link active" href="resumen.html">Resumen</a>
    </nav>
  </header>

  <section class="status-strip">
    <span id="summary-updated">Última actualización: {formatDate(generatedAt)}</span>
    <div class="category-sort" role="group" aria-label="Orden de categorías">
      <strong id="summary-count">{visibleRows.length} filamentos</strong>
      <span>Orden</span>
      <button id="summary-sort-popular" class="soft-button" class:active={categoryOrder === "popular"} type="button" data-category-order="popular" on:click={() => categoryOrder = "popular"}>Popularidad</button>
      <button id="summary-sort-alpha" class="soft-button" class:active={categoryOrder === "alpha"} type="button" data-category-order="alpha" on:click={() => categoryOrder = "alpha"}>A-Z</button>
    </div>
  </section>

  <section class="filters" aria-label="Filtros">
    <label class="search-field">
      <span>Buscar</span>
      <input id="summary-search" type="search" bind:value={query} placeholder="Filamento, color, marca...">
    </label>
  </section>

  <section aria-label="Líneas populares">
    <QuickLines id="summary-quick-lines" available={availableLines} bind:help={lineHelp} targetSelector=".summary-group-row" />
    <p id="summary-line-help" class="line-help">{lineHelp}</p>
  </section>

  <div class="table-shell">
    <table id="summary-table" class="summary-table">
      <thead>
        <tr>
          <th>Filamento</th>
          <th class="summary-presentation">Presentación</th>
          {#each sources as source}
            <th><a href={source.homepage_url} target="_blank" rel="noopener" title={`${formatInteger(source.stats?.total_stock_units ?? 0)} carretes`}>{source.name}</a></th>
          {/each}
          <th class="summary-total">Total</th>
        </tr>
      </thead>
      <tbody>
        {#each groupedRows as group}
          <tr class="summary-group-row" id={summaryGroupTargetId(group)} data-line={group.line}>
            <th>
              {group.title}
              <span class="summary-mobile-totals" aria-hidden="true">
                {#each sources as source}<span><b>{source.name}</b> {formatInteger(group.totals[source.id])}</span>{/each}
                <span class="summary-mobile-total"><b>Total</b> {formatInteger(group.total)}</span>
              </span>
            </th>
            <td class="summary-presentation" data-label="Presentación"></td>
            {#each sources as source}<td data-label={source.name}>{formatInteger(group.totals[source.id])}</td>{/each}
            <td class="summary-total" data-label="Total">{formatInteger(group.total)}</td>
          </tr>
          {#each group.rows as row}
            <tr>
              <th>
                <span class="summary-product">
                  <span class="summary-color-swatch" style={colorSwatchStyle(row.product)} title={[row.product.color || "Sin color", row.product.pantone].filter(Boolean).join(" · ")} aria-label={[row.product.color || "Sin color", row.product.pantone].filter(Boolean).join(" · ")}></span>
                  <span class="summary-product-name">
                    {#if row.product.manufacturer_product_url}
                      <a href={row.product.manufacturer_product_url} target="_blank" rel="noopener">{productSummaryName(row.product)}</a>
                    {:else}
                      {productSummaryName(row.product)}
                    {/if}
                    {#if row.product.pantone}<small>{row.product.pantone}</small>{/if}
                  </span>
                </span>
              </th>
              <td class="summary-presentation" data-label="Presentación">{formatPresentation(row.product)}</td>
              {#each sources as source}
                {@const cell = row.cells[source.id]}
                <td class={cell?.units > 0 ? "stock-in" : "stock-out"} data-label={source.name}>{formatInteger(cell?.units || 0)}</td>
              {/each}
              <td class="summary-total" data-label="Total">{formatInteger(row.total)}</td>
            </tr>
          {/each}
        {/each}
      </tbody>
      <tfoot>
        <tr>
          <th>Carretes por proveedor</th>
          <td class="summary-presentation" data-label="Presentación"></td>
          {#each sources as source}<td class="summary-total" data-label={source.name}>{formatInteger(providerTotals[source.id])}</td>{/each}
          <td class="summary-total" data-label="Total">{formatInteger(grandTotal)}</td>
        </tr>
      </tfoot>
    </table>
  </div>
</main>

<SiteFooter sources={sources} contactContext={query ? `"${query}"` : ""} />
