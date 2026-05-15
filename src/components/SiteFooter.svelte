<script>
  import { formatDate, providerAnchorId, siteContactUrl, siteRepoUrl, sourceWhatsappUrl, stockDelta } from "../lib/shared.js";

  export let sources = [];
  export let contactContext = "";

  $: message = `Hola, vi su stock publicado en Central de Filamentos.${contactContext ? ` Estoy buscando ${contactContext}.` : " Quería consultar disponibilidad y precio."}`;
</script>

<footer id="site-footer" class="site-footer">
  <div class="footer-grid">
    {#each sources as source}
      {@const stats = source.stats || {}}
      {@const delta = stockDelta(stats)}
      <section class="footer-provider" id={providerAnchorId(source.id)}>
        <h3><a href={source.homepage_url} target="_blank" rel="noopener">{source.name}</a></h3>
        <p>{source.zone}{source.address ? ` · ${source.address}` : ""}</p>
        <p class="provider-stock-line">
          <span>{stats.total_stock_units || 0} carretes · {stats.product_count || 0} productos</span>
          {#if delta}
            <span class={`stock-delta stock-delta-${delta.tone}`}>{delta.label} vs ayer</span>
          {/if}
        </p>
        <p>Actualizado: {formatDate(source.last_success_at || source.last_attempt_at)}</p>
        <div class="contact-actions">
          {#if source.contact_whatsapp_url}
            <a href={sourceWhatsappUrl(source, message)} target="_blank" rel="noopener">WhatsApp</a>
          {/if}
          {#if source.contact_phone}
            <a href={`tel:${source.contact_phone.replaceAll(" ", "")}`}>Teléfono</a>
          {/if}
          {#if source.contact_email}
            <a href={`mailto:${source.contact_email}`}>Mail</a>
          {/if}
          {#if source.source_url}
            <a href={source.source_url} target="_blank" rel="noopener">Fuente</a>
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
    <div class="contact-actions">
      <a href={siteContactUrl} target="_blank" rel="noopener">Reportar error</a>
      <a href={siteContactUrl} target="_blank" rel="noopener">Sumar proveedor</a>
      <a href={siteRepoUrl} target="_blank" rel="noopener">Repositorio</a>
    </div>
  </section>
</footer>
