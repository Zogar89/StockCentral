<script>
  import { onMount } from "svelte";
  import QuickLines from "./components/QuickLines.svelte";
  import SiteHeader from "./components/SiteHeader.svelte";
  import SiteFooter from "./components/SiteFooter.svelte";
  import {
    brandRank,
    colorSwatchLabel,
    colorSwatchStyle,
    comparePresentations,
    dataUrl,
    diameterLabel,
    fetchJson,
    formatDate,
    formatPresentation,
    formatWeightLabel,
    lineLabel,
    lineMeta,
    lineOptionLabel,
    lineRank,
    matchesSearchTerms,
    pantoneSwatchLabel,
    productBaseName,
    providerAnchorId,
    slugText,
  } from "./lib/shared.js";

  let filters = {
    query: "",
    material: "",
    variant: "",
    color: "",
    diameter: "",
    weight: "",
    brand: "",
    provider: "",
    stock: "all",
  };

  let products = [];
  let sources = [];
  let generatedAt = "";
  let categoryOrder = "popular";
  let lineHelp = "";
  let preview = null;

  onMount(async () => {
    const payload = await fetchJson("data/stock.json", { products: [], sources: [] });
    products = payload.products || [];
    sources = payload.sources || [];
    generatedAt = payload.generated_at || "";
  });

  $: filteredProducts = (filters, categoryOrder, products.filter(matchesFilters).sort(compareProducts));
  $: groups = (categoryOrder, groupProducts(filteredProducts));
  $: lineOptions = (products, lineValues());
  $: availableLines = (products, lineValues());
  $: materialOptions = (products, valuesFor("material"));
  $: colorOptions = (products, valuesFor("color"));
  $: diameterOptions = (products, valuesFor("diameter_mm"));
  $: weightOptions = (products, valuesFor("weight_g"));
  $: brandOptions = (products, valuesFor("brand"));
  $: providerOptions = (products, providerValues());
  $: contactContext = [
    filters.query ? `"${filters.query}"` : "",
    filters.material,
    filters.variant,
    filters.color,
    filters.diameter ? `${filters.diameter} mm` : "",
    filters.weight ? formatWeightLabel(filters.weight) : "",
    filters.brand,
  ].filter(Boolean).join(", ");

  function matchesFilters(product) {
    const queryFields = [
      product.display_name,
      product.material,
      product.variant,
      product.color,
      product.pantone,
      product.sku,
      product.ean,
      product.brand,
      ...(product.offers || []).map((offer) => offer.original_name),
    ];

    if (filters.query && !matchesSearchTerms(filters.query.toLowerCase().trim(), queryFields)) return false;
    if (filters.material && product.material !== filters.material) return false;
    if (filters.variant && lineLabel(product) !== filters.variant) return false;
    if (filters.color && product.color !== filters.color) return false;
    if (filters.diameter && String(product.diameter_mm) !== filters.diameter) return false;
    if (filters.weight && String(product.weight_g) !== filters.weight) return false;
    if (filters.brand && product.brand !== filters.brand) return false;
    if (filters.provider && !(product.offers || []).some((offer) => offer.provider_name === filters.provider)) return false;
    if (filters.stock !== "all" && !(product.offers || []).some((offer) => offer.stock_status === filters.stock)) return false;
    return true;
  }

  function setFilter(name, value) {
    filters = { ...filters, [name]: value };
  }

  function setVariantFilter(value) {
    setFilter("variant", value);
    lineHelp = value ? (lineMeta[value]?.help || "") : "";
  }

  function groupProducts(items) {
    const grouped = new Map();
    items.forEach((product) => {
      const key = [product.brand || "Sin marca", diameterLabel(product), lineLabel(product)].join("||");
      if (!grouped.has(key)) {
        grouped.set(key, {
          brand: product.brand || "Sin marca",
          diameter: diameterLabel(product),
          line: lineLabel(product),
          products: [],
        });
      }
      grouped.get(key).products.push(product);
    });
    return [...grouped.values()].sort(compareGroups);
  }

  function groupBaseProducts(items) {
    const cards = new Map();
    items.forEach((product) => {
      const key = [
        product.brand || "Sin marca",
        product.diameter_mm || "Sin diametro",
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

  function compareGroups(left, right) {
    if (categoryOrder === "alpha") {
      return [left.line, left.brand, left.diameter].join(" ").localeCompare([right.line, right.brand, right.diameter].join(" "), "es-AR");
    }
    return (
      lineRank(left.line) - lineRank(right.line)
      || brandRank(left.brand).localeCompare(brandRank(right.brand), "es-AR")
      || left.diameter.localeCompare(right.diameter, "es-AR")
      || left.line.localeCompare(right.line, "es-AR")
    );
  }

  function compareProducts(left, right) {
    const groupComparison = compareProductGroups(left, right);
    if (groupComparison !== 0) return groupComparison;
    return [left.color || "", left.display_name].join(" ").localeCompare([right.color || "", right.display_name].join(" "), "es-AR");
  }

  function compareProductGroups(left, right) {
    const leftLine = lineLabel(left);
    const rightLine = lineLabel(right);
    if (categoryOrder === "alpha") {
      return [leftLine, left.brand || "", diameterLabel(left)].join(" ").localeCompare([rightLine, right.brand || "", diameterLabel(right)].join(" "), "es-AR");
    }
    return (
      lineRank(leftLine) - lineRank(rightLine)
      || brandRank(left.brand).localeCompare(brandRank(right.brand), "es-AR")
      || diameterLabel(left).localeCompare(diameterLabel(right), "es-AR")
      || leftLine.localeCompare(rightLine, "es-AR")
    );
  }

  function valuesFor(field) {
    return [...new Set(products.map((product) => product[field]).filter((value) => value !== "" && value !== null && value !== undefined))].sort();
  }

  function providerValues() {
    return [...new Set(products.flatMap((product) => (product.offers || []).map((offer) => offer.provider_name)))].sort();
  }

  function lineValues() {
    return [...new Set(products.map(lineLabel).filter(Boolean))].sort((left, right) => lineRank(left) - lineRank(right) || left.localeCompare(right, "es-AR"));
  }

  function groupTargetId(group) {
    return `linea-${slugText([group.line, group.brand, group.diameter].join(" "))}`;
  }

  function productVisual(product, cardProducts) {
    const imageProducts = cardProducts.filter((item) => item.image_url).sort(compareImagePresentations);
    return imageProducts.length ? imageProducts[0] : product;
  }

  function compareImagePresentations(left, right) {
    return imagePresentationRank(left) - imagePresentationRank(right) || comparePresentations(left, right);
  }

  function imagePresentationRank(product) {
    if (Number(product.weight_g) === 1000) return 0;
    if (Number(product.weight_g) === 2500) return 1;
    return 2;
  }

  function assetPath(path) {
    if (!path || /^https?:\/\//.test(path)) return path;
    return dataUrl(path);
  }

  function showPreview(event, product) {
    if (!product.image_url) return;
    preview = {
      src: assetPath(product.image_url),
      title: [product.color || "Sin color", product.pantone, formatPresentation(product)].filter(Boolean).join(" · "),
      x: event.clientX + 16,
      y: event.clientY + 16,
      modal: false,
    };
  }

  function movePreview(event) {
    if (!preview || preview.modal) return;
    preview = { ...preview, x: event.clientX + 16, y: event.clientY + 16 };
  }

  function hideHoverPreview() {
    if (!preview?.modal) preview = null;
  }

  function openImagePreview(product) {
    if (!product.image_url) return;
    preview = {
      src: assetPath(product.image_url),
      title: productBaseName(product),
      meta: [product.color || "Sin color", product.pantone, formatPresentation(product)].filter(Boolean).join(" · "),
      modal: true,
    };
  }

  function closePreviewBackdrop(event) {
    if (event.target === event.currentTarget) preview = null;
  }

  function handlePreviewKeydown(event) {
    if (event.key === "Escape" && preview?.modal) preview = null;
  }

  function providerTitle(offer) {
    return `${offer.provider_name} · ${offer.provider_zone}`;
  }
</script>

<main class="shell">
  <SiteHeader active="catalog" updatedAt={generatedAt} providerCount={sources.length} subtitle="AMBA · filamentos 3D" />

  <section class="status-strip">
    <span id="last-update">Última actualización: {formatDate(generatedAt)}</span>
  </section>

  <section class="filters" aria-label="Filtros">
    <label class="search-field">
      <span>Buscar</span>
      <input id="search-input" type="search" value={filters.query} on:input={(event) => setFilter("query", event.currentTarget.value)} placeholder="PLA negro, PETG, Grilon3...">
    </label>
    <select id="material-filter" value={filters.material} on:change={(event) => setFilter("material", event.currentTarget.value)}><option value="">Material</option>{#each materialOptions as value}<option value={value}>{value}</option>{/each}</select>
    <select id="variant-filter" value={filters.variant} on:change={(event) => setVariantFilter(event.currentTarget.value)}><option value="">Línea</option>{#each lineOptions as value}<option value={value}>{lineOptionLabel(value)}</option>{/each}</select>
    <select id="color-filter" value={filters.color} on:change={(event) => setFilter("color", event.currentTarget.value)}><option value="">Color</option>{#each colorOptions as value}<option value={value}>{value}</option>{/each}</select>
    <select id="diameter-filter" value={filters.diameter} on:change={(event) => setFilter("diameter", event.currentTarget.value)}><option value="">Diámetro</option>{#each diameterOptions as value}<option value={String(value)}>{value} mm</option>{/each}</select>
    <select id="weight-filter" value={filters.weight} on:change={(event) => setFilter("weight", event.currentTarget.value)}><option value="">Peso</option>{#each weightOptions as value}<option value={String(value)}>{Number(value) / 1000} kg</option>{/each}</select>
    <select id="brand-filter" value={filters.brand} on:change={(event) => setFilter("brand", event.currentTarget.value)}><option value="">Marca</option>{#each brandOptions as value}<option value={value}>{value}</option>{/each}</select>
    <select id="provider-filter" value={filters.provider} on:change={(event) => setFilter("provider", event.currentTarget.value)}><option value="">Proveedor</option>{#each providerOptions as value}<option value={value}>{value}</option>{/each}</select>
    <select id="stock-filter" value={filters.stock} on:change={(event) => setFilter("stock", event.currentTarget.value)}>
      <option value="all">Todos</option>
      <option value="in_stock">Con stock</option>
      <option value="out_of_stock">Sin stock</option>
      <option value="unknown">Sin cantidad</option>
    </select>
  </section>

  <section class="quick-lines-shell" aria-label="Líneas populares">
    <QuickLines id="quick-lines" available={availableLines} bind:help={lineHelp} targetSelector=".group-section" />
    <p id="line-help" class="line-help">{lineHelp}</p>
  </section>

  <div class="result-meta">
    <strong id="result-count">{filteredProducts.length} productos</strong>
    <div class="category-sort" role="group" aria-label="Orden de categorías">
      <span>Orden</span>
      <button id="sort-popular" class:active={categoryOrder === "popular"} class="soft-button" type="button" data-category-order="popular" on:click={() => categoryOrder = "popular"}>Popularidad</button>
      <button id="sort-alpha" class:active={categoryOrder === "alpha"} class="soft-button" type="button" data-category-order="alpha" on:click={() => categoryOrder = "alpha"}>A-Z</button>
    </div>
  </div>

  <section id="product-list" class="product-list">
    {#each groups as group}
      <section class="group-section" id={groupTargetId(group)} data-line={group.line}>
        <header class="group-heading">
          <span>{group.brand}</span>
          <span>{group.diameter}</span>
          <strong>{group.line}</strong>
        </header>
        <div class="group-products">
          {#each groupBaseProducts(group.products) as card}
            {@const product = card.products[0]}
            {@const visual = productVisual(product, card.products)}
            <article class="product-row">
              <div class={`product-visuals${card.products.filter((item) => item.image_url).length > 1 ? " multi-image" : ""}`}>
                {#if visual.image_url}
                  <button class="product-image product-media" type="button" data-preview-src={assetPath(visual.image_url)} data-preview-title={[visual.color || "Sin color", visual.pantone, formatPresentation(visual)].filter(Boolean).join(" · ")} aria-label={`Ampliar imagen de ${productBaseName(visual)}`} on:click={() => openImagePreview(visual)} on:pointerenter={(event) => showPreview(event, visual)} on:pointermove={movePreview} on:pointerleave={hideHoverPreview}>
                    <img src={assetPath(visual.thumbnail_url || visual.image_url)} alt={productBaseName(visual)} loading="lazy" decoding="async">
                  </button>
                {:else}
                  <div class="product-image color-swatch" style={colorSwatchStyle(product)} role="img" aria-label={[product.color || "Sin color", product.pantone].filter(Boolean).join(" · ")} title={[product.color || "Sin color", product.pantone].filter(Boolean).join(" · ")}>
                    <span>{colorSwatchLabel(product.color)}</span>
                  </div>
                {/if}
                {#if visual.pantone || product.pantone}
                  <small class="swatch-pantone media-pantone">{pantoneSwatchLabel(visual.pantone || product.pantone)}</small>
                {/if}
              </div>
              <div>
                <div class="product-head">
                  <h2>
                    <span>{productBaseName(product)}</span>
                    {#if product.manufacturer_product_url}
                      <a class="official-product-link" href={product.manufacturer_product_url} target="_blank" rel="noopener" aria-label={`Abrir página oficial de ${productBaseName(product)}`} title="Página oficial">↗</a>
                    {/if}
                  </h2>
                </div>
                <div class="presentation-list">
                  {#each card.products as presentation}
                    <section class="presentation-row">
                      <header><strong>{formatPresentation(presentation) || "Presentación sin dato"}</strong></header>
                      <div class="offers">
                        {#if (presentation.offers || []).length}
                          {#each presentation.offers as offer}
                            <div class="offer" title={providerTitle(offer)}>
                              <div class="offer-main">
                                <a href={`#${providerAnchorId(offer.source_id)}`} title={providerTitle(offer)}>{offer.provider_name}</a>
                                <strong class={offer.stock_status === "in_stock" ? "stock-in" : "stock-out"}>{offer.stock_status === "in_stock" ? `${offer.stock_quantity} carretes` : "0"}</strong>
                              </div>
                              <small>{offer.original_name}</small>
                            </div>
                          {/each}
                        {:else}
                          <div class="offer stock-out">0 · sin stock online registrado</div>
                        {/if}
                      </div>
                    </section>
                  {/each}
                </div>
              </div>
            </article>
          {/each}
        </div>
      </section>
    {/each}
  </section>
</main>

<SiteFooter {sources} {contactContext} />

<svelte:window on:keydown={handlePreviewKeydown} />

{#if preview && preview.modal}
  <div class="image-preview-backdrop" role="presentation" on:click={closePreviewBackdrop}>
    <div class="image-preview-modal" role="dialog" aria-modal="true" aria-label={preview.title}>
      <button class="image-preview-close" type="button" aria-label="Cerrar imagen ampliada" on:click={() => preview = null}>×</button>
      <img src={preview.src} alt={preview.title}>
      <strong>{preview.title}</strong>
      <span>{preview.meta}</span>
    </div>
  </div>
{:else if preview}
  <div class="image-preview visible" style={`left:${preview.x}px; top:${preview.y}px;`}>
    <img src={preview.src} alt={preview.title}>
    <span>{preview.title}</span>
  </div>
{/if}
