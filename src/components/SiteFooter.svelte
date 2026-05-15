<script>
  import { formatDate, formatInteger, providerAnchorId, siteContactUrl, siteRepoUrl, sourceWhatsappUrl, stockDelta } from "../lib/shared.js";

  export let sources = [];
  export let contactContext = "";

  $: message = `Hola, vi su stock publicado en Central de Filamentos.${contactContext ? ` Estoy buscando ${contactContext}.` : " Quería consultar disponibilidad y precio."}`;

  function providerInitials(source) {
    return String(source.name || "")
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();
  }

  function providerAccent(sourceId) {
    if (sourceId === "mundoinsumos") return "#0f8b6f";
    if (sourceId === "grupo_senz") return "#b56a2f";
    if (sourceId === "filamentos3d") return "#0b6fbd";
    return "#117a65";
  }

  function phoneHref(phone) {
    return `tel:${String(phone || "").replace(/[^\d+]/g, "")}`;
  }
</script>

<footer id="site-footer" class="site-footer">
  <div class="footer-grid">
    {#each sources as source}
      {@const stats = source.stats || {}}
      {@const delta = stockDelta(stats)}
      <section class="footer-provider" id={providerAnchorId(source.id)} style={`--provider-accent: ${providerAccent(source.id)}`}>
        <header class="footer-provider-head">
          <a class="provider-mark" href={source.homepage_url} target="_blank" rel="noopener" aria-label={`Abrir ${source.name}`}>
            {providerInitials(source)}
          </a>
          <div>
            <h3><a href={source.homepage_url} target="_blank" rel="noopener">{source.name}</a></h3>
            <p class="provider-zone">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-5.2 7-11a7 7 0 1 0-14 0c0 5.8 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/></svg>
              <span>{source.zone}</span>
            </p>
          </div>
        </header>

        <div class="footer-provider-stats" aria-label={`Stock de ${source.name}`}>
          <span><strong>{formatInteger(stats.total_stock_units || 0)}</strong><small>carretes</small></span>
          <span><strong>{formatInteger(stats.product_count || 0)}</strong><small>productos</small></span>
          {#if delta}
            <span class={`stock-delta stock-delta-${delta.tone}`}>{delta.label}<small>vs ayer</small></span>
          {/if}
        </div>

        <div class="footer-provider-details">
          {#if source.address}
            <p>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 21h18"/><path d="M5 21V7l7-4 7 4v14"/><path d="M9 21v-7h6v7"/></svg>
              <span>{source.address}</span>
            </p>
          {/if}
          <p>
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
            <span>Actualizado: {formatDate(source.last_success_at || source.last_attempt_at)}</span>
          </p>
        </div>

        <div class="contact-actions footer-actions">
          {#if source.contact_whatsapp_url}
            <a href={sourceWhatsappUrl(source, message)} target="_blank" rel="noopener" aria-label={`Enviar WhatsApp a ${source.name}`} title="WhatsApp">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19.2 6.2 16A8 8 0 1 1 9 18.6L5 19.2Z"/><path d="M9.2 8.8c.2-.5.4-.5.7-.5h.5c.2 0 .4.1.5.4l.8 1.7c.1.3.1.5-.1.7l-.4.5c.7 1.2 1.7 2.1 3 2.8l.6-.5c.2-.2.4-.2.7-.1l1.6.8c.3.1.4.3.4.6v.4c0 .4-.2.7-.6.9-.6.3-1.4.4-2.4.1-2.9-.8-5.3-3.2-6-6-.2-.8-.1-1.4.2-1.8Z"/></svg>
              <span>WhatsApp</span>
            </a>
          {/if}
          {#if source.contact_phone}
            <a href={phoneHref(source.contact_phone)} aria-label={`Llamar a ${source.name}`} title="Teléfono">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.3 1.7.6 2.5a2 2 0 0 1-.4 2.1L8 9.6a16 16 0 0 0 6.4 6.4l1.3-1.3a2 2 0 0 1 2.1-.4c.8.3 1.6.5 2.5.6a2 2 0 0 1 1.7 2Z"/></svg>
              <span>Teléfono</span>
            </a>
          {/if}
          {#if source.contact_email}
            <a href={`mailto:${source.contact_email}`} aria-label={`Enviar mail a ${source.name}`} title="Mail">
              <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>
              <span>Mail</span>
            </a>
          {/if}
          {#if source.source_url}
            <a href={source.source_url} target="_blank" rel="noopener" aria-label={`Ver fuente de stock de ${source.name}`} title="Fuente">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3v4a2 2 0 0 0 2 2h4"/><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M8 13h8"/><path d="M8 17h5"/></svg>
              <span>Fuente</span>
            </a>
          {/if}
        </div>
      </section>
    {/each}
  </div>
  <section class="footer-meta" aria-label="Información del proyecto">
    <div>
      <h2>Central de Filamentos</h2>
      <p>Creado por Gabriel (Zogar89) para impresores 3D del AMBA.</p>
      <p>Si encontrás un error de stock, una foto incorrecta o querés sumar tu proveedor al listado, avisame por GitHub.</p>
    </div>
    <div class="contact-actions footer-actions footer-meta-actions">
      <a href={siteContactUrl} target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 2h8l4 4v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6l4-4Z"/><path d="M12 8v5"/><path d="M12 17h.01"/></svg>
        <span>Reportar error</span>
      </a>
      <a href={siteContactUrl} target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6"/><path d="M22 11h-6"/></svg>
        <span>Sumar proveedor</span>
      </a>
      <a href={siteRepoUrl} target="_blank" rel="noopener">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3c3 0 6-2 6-5.5 0-1.2-.4-2.3-1.2-3.2.1-.4.5-1.9-.1-3.3 0 0-1-.3-3.3 1.2a11.4 11.4 0 0 0-6 0C7.1 2.7 6.1 3 6.1 3c-.6 1.4-.2 2.9-.1 3.3A4.6 4.6 0 0 0 4.8 9.5C4.8 13 7.8 15 10.8 15a4.8 4.8 0 0 0-1 3v4"/><path d="M9 18c-4.5 2-5-2-7-2"/></svg>
        <span>Repositorio</span>
      </a>
    </div>
  </section>
</footer>
