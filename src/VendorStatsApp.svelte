<script>
  import { onMount } from "svelte";
  import { fetchJson, formatDate, formatDay, formatInteger, formatTime } from "./lib/shared.js";

  let providers = [];
  let days = [];
  let generatedAt = "";
  let health = null;
  let disabled = false;

  onMount(async () => {
    const flags = await fetchJson("data/feature_flags.json", {});
    if (!flags.vendorStatsEnabled) {
      disabled = true;
      return;
    }
    const history = await fetchJson("data/provider_stock_history.json", { providers: [], days: [] });
    health = await fetchJson("data/build_business_log.json", null);
    providers = history.providers || [];
    days = (history.days || []).slice(-30);
    generatedAt = history.generated_at || "";
  });

  $: reversedDays = [...days].reverse();

  function latestQuantity(providerId) {
    const latestDay = days[days.length - 1];
    return latestDay ? quantityForProvider(latestDay, providerId) : 0;
  }

  function latestDeltaForProvider(providerId) {
    const latestDay = days[days.length - 1];
    return latestDay ? deltaForProvider(latestDay.date, providerId) : null;
  }

  function movementForProvider(providerId, direction) {
    return days.reduce((total, day) => {
      const delta = deltaForProvider(day.date, providerId);
      if (!Number.isFinite(delta)) return total;
      if (direction === "positive" && delta > 0) return total + delta;
      if (direction === "negative" && delta < 0) return total + Math.abs(delta);
      return total;
    }, 0);
  }

  function deltaForProvider(date, providerId) {
    const index = days.findIndex((day) => day.date === date);
    if (index <= 0) return null;
    return quantityForProvider(days[index], providerId) - quantityForProvider(days[index - 1], providerId);
  }

  function quantityForProvider(day, providerId) {
    const value = Number(day.providers?.[providerId] || 0);
    return Number.isFinite(value) ? value : 0;
  }

  function checksForDay(day) {
    const checks = Array.isArray(day.checks) ? day.checks : [];
    if (checks.length) return checks;
    if (!day.captured_at) return [];
    return [{ captured_at: day.captured_at, providers: day.providers || {} }];
  }

  function deltaTone(delta) {
    if (!Number.isFinite(delta)) return "muted";
    if (delta > 0) return "positive";
    if (delta < 0) return "negative";
    return "flat";
  }

  function deltaLabel(delta) {
    if (!Number.isFinite(delta)) return "Sin base";
    return delta > 0 ? `+${formatInteger(delta)}` : formatInteger(delta);
  }

  function statusLabel(status) {
    if (status === "ok") return "OK";
    if (status === "blocked") return "Bloqueado";
    return status || "";
  }
</script>

<main class="internal-shell">
  <header class="topbar">
    <div>
      <p class="eyebrow">Consumo interno</p>
      <h1>Estadisticas de vendedores</h1>
    </div>
  </header>

  <section class="status-strip">
    <span id="vendor-updated">{disabled ? "Feature flag apagado" : `Actualizado: ${formatDate(generatedAt)}`}</span>
    <strong id="vendor-window">{days.length} dias registrados</strong>
  </section>

  {#if health && health.status && health.status !== "not_run"}
    {@const status = health.status === "ok" ? "ok" : "blocked"}
    <section id="build-health" class="build-health" aria-label="Salud del ultimo build">
      <article class={`build-health-card build-health-${status}`}>
        <header>
          <div>
            <p class="eyebrow">Salud del build</p>
            <h2>{health.summary || "Sin novedades"}</h2>
          </div>
          <strong>{statusLabel(health.status)}</strong>
        </header>
        {#if Array.isArray(health.events) && health.events.length}
          <ul class="build-health-events">
            {#each health.events.slice(0, 4) as event}
              <li class={`health-event-${event.level || "info"}`}>{event.message || ""}</li>
            {/each}
          </ul>
        {/if}
        {#if health.last_good_sources && Object.keys(health.last_good_sources).length}
          <dl class="build-health-last-good">
            {#each Object.entries(health.last_good_sources) as [sourceId, source]}
              <div>
                <dt>{source.name || sourceId}</dt>
                <dd>{formatInteger(source.total_stock_units)} carretes · {formatDate(source.generated_at)}</dd>
              </div>
            {/each}
          </dl>
        {/if}
      </article>
    </section>
  {:else}
    <section id="build-health" class="build-health" aria-label="Salud del ultimo build"></section>
  {/if}

  {#if disabled}
    <section id="vendor-disabled" class="internal-empty">
      <h2>Pagina apagada</h2>
      <p>El feature flag interno esta desactivado.</p>
    </section>
  {:else}
    <section id="vendor-dashboard" aria-label="Estadisticas internas de vendedores">
      {#if !days.length || !providers.length}
        <section class="internal-empty">
          <h2>Sin historial todavia</h2>
          <p>El historial se completa con la captura diaria de las 09:00.</p>
        </section>
      {:else}
        <section class="vendor-stat-grid">
          {#each providers as provider}
            <article class="vendor-stat-card">
              <header>
                <div>
                  <h2>{provider.name}</h2>
                  <p>{provider.zone || ""}</p>
                </div>
                <strong>{formatInteger(latestQuantity(provider.id))} carretes</strong>
              </header>
              <dl class="vendor-kpis">
                <div>
                  <dt>Variacion reciente</dt>
                  <dd><span class={`delta-badge delta-${deltaTone(latestDeltaForProvider(provider.id))}`}>{deltaLabel(latestDeltaForProvider(provider.id))}</span></dd>
                </div>
                <div>
                  <dt>Entradas 30d</dt>
                  <dd class="delta-positive">+{formatInteger(movementForProvider(provider.id, "positive"))}</dd>
                </div>
                <div>
                  <dt>Salidas 30d</dt>
                  <dd class="delta-negative">-{formatInteger(movementForProvider(provider.id, "negative"))}</dd>
                </div>
              </dl>
              <div class="vendor-table-wrap">
                <table class="vendor-history-table">
                  <thead>
                    <tr>
                      <th>Fecha</th>
                      <th>Cantidad por dia</th>
                      <th>Variacion vs dia anterior</th>
                    </tr>
                  </thead>
                  <tbody>
                    {#each reversedDays as day}
                      {@const quantity = quantityForProvider(day, provider.id)}
                      {@const delta = deltaForProvider(day.date, provider.id)}
                      {@const checks = checksForDay(day)}
                      <tr class="daily-row">
                        <td>{formatDay(day.date)}</td>
                        <td>{formatInteger(quantity)}</td>
                        <td><span class={`delta-badge delta-${deltaTone(delta)}`}>{deltaLabel(delta)}</span></td>
                      </tr>
                      <tr class="intraday-checks">
                        <td colspan="3">
                          <details class="intraday-panel">
                            <summary><span>Chequeos del dia</span><strong>{formatInteger(checks.length)}</strong></summary>
                            {#if checks.length}
                              <div class="intraday-list">
                                {#each checks as check, index}
                                  {@const checkQuantity = quantityForProvider(check, provider.id)}
                                  {@const previous = index > 0 ? quantityForProvider(checks[index - 1], provider.id) : null}
                                  {@const previousDelta = Number.isFinite(previous) ? checkQuantity - previous : null}
                                  <div class="intraday-row">
                                    <span class="intraday-time">{formatTime(check.captured_at)}</span>
                                    <strong class="intraday-quantity">{formatInteger(checkQuantity)}</strong>
                                    <span class="intraday-metric"><small>vs anterior</small><span class={`delta-badge delta-${deltaTone(previousDelta)}`}>{deltaLabel(previousDelta)}</span></span>
                                    <span class="intraday-metric"><small>vs 09:00</small><span class={`delta-badge delta-${deltaTone(checkQuantity - quantity)}`}>{deltaLabel(checkQuantity - quantity)}</span></span>
                                  </div>
                                {/each}
                              </div>
                            {:else}
                              <p class="intraday-empty">Sin chequeos intradia.</p>
                            {/if}
                          </details>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </article>
          {/each}
        </section>
      {/if}
    </section>
  {/if}
</main>
