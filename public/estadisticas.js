const state = {
  providers: [],
  days: [],
  generatedAt: "",
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  const flags = await fetchJson("data/feature_flags.json", {});
  if (!flags.vendorStatsEnabled) {
    showDisabled();
    return;
  }

  const history = await fetchJson("data/provider_stock_history.json", { providers: [], days: [] });
  state.providers = history.providers || [];
  state.days = (history.days || []).slice(-30);
  state.generatedAt = history.generated_at || "";
  render();
}

async function fetchJson(url, fallback) {
  try {
    const response = await fetch(url);
    if (!response.ok) return fallback;
    return await response.json();
  } catch {
    return fallback;
  }
}

function showDisabled() {
  document.getElementById("vendor-updated").textContent = "Feature flag apagado";
  document.getElementById("vendor-dashboard").hidden = true;
  document.getElementById("vendor-disabled").hidden = false;
}

function render() {
  document.getElementById("vendor-updated").textContent = `Actualizado: ${formatDate(state.generatedAt)}`;
  document.getElementById("vendor-window").textContent = `${state.days.length} dias registrados`;

  const dashboard = document.getElementById("vendor-dashboard");
  if (!state.days.length || !state.providers.length) {
    dashboard.innerHTML = `
      <section class="internal-empty">
        <h2>Sin historial todavia</h2>
        <p>El historial se completa con la captura diaria de las 09:00.</p>
      </section>
    `;
    return;
  }

  dashboard.innerHTML = `
    <section class="vendor-stat-grid">
      ${state.providers.map(providerCardTemplate).join("")}
    </section>
  `;
}

function providerCardTemplate(provider) {
  const latest = latestQuantity(provider.id);
  const latestDelta = latestDeltaForProvider(provider.id);
  const positiveMovement = movementForProvider(provider.id, "positive");
  const negativeMovement = movementForProvider(provider.id, "negative");
  return `
    <article class="vendor-stat-card">
      <header>
        <div>
          <h2>${escapeHtml(provider.name)}</h2>
          <p>${escapeHtml(provider.zone || "")}</p>
        </div>
        <strong>${formatInteger(latest)} carretes</strong>
      </header>
      <dl class="vendor-kpis">
        <div>
          <dt>Variacion reciente</dt>
          <dd>${deltaBadgeTemplate(latestDelta)}</dd>
        </div>
        <div>
          <dt>Entradas 30d</dt>
          <dd class="delta-positive">+${formatInteger(positiveMovement)}</dd>
        </div>
        <div>
          <dt>Salidas 30d</dt>
          <dd class="delta-negative">-${formatInteger(negativeMovement)}</dd>
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
          <tbody>${[...state.days].reverse().map((day) => dayRowTemplate(day, provider.id)).join("")}</tbody>
        </table>
      </div>
    </article>
  `;
}

function dayRowTemplate(day, providerId) {
  const quantity = quantityForProvider(day, providerId);
  const delta = deltaForProvider(day.date, providerId);
  return `
    <tr>
      <td>${escapeHtml(formatDay(day.date))}</td>
      <td>${formatInteger(quantity)}</td>
      <td>${deltaBadgeTemplate(delta)}</td>
    </tr>
  `;
}

function latestQuantity(providerId) {
  const latestDay = state.days[state.days.length - 1];
  return latestDay ? quantityForProvider(latestDay, providerId) : 0;
}

function latestDeltaForProvider(providerId) {
  const latestDay = state.days[state.days.length - 1];
  return latestDay ? deltaForProvider(latestDay.date, providerId) : null;
}

function movementForProvider(providerId, direction) {
  return state.days.reduce((total, day) => {
    const delta = deltaForProvider(day.date, providerId);
    if (!Number.isFinite(delta)) return total;
    if (direction === "positive" && delta > 0) return total + delta;
    if (direction === "negative" && delta < 0) return total + Math.abs(delta);
    return total;
  }, 0);
}

function deltaForProvider(date, providerId) {
  const index = state.days.findIndex((day) => day.date === date);
  if (index <= 0) return null;
  const current = quantityForProvider(state.days[index], providerId);
  const previous = quantityForProvider(state.days[index - 1], providerId);
  return current - previous;
}

function quantityForProvider(day, providerId) {
  const value = Number(day.providers?.[providerId] || 0);
  return Number.isFinite(value) ? value : 0;
}

function deltaBadgeTemplate(delta) {
  if (!Number.isFinite(delta)) return `<span class="delta-muted">Sin base</span>`;
  const label = delta > 0 ? `+${formatInteger(delta)}` : formatInteger(delta);
  const tone = delta > 0 ? "positive" : delta < 0 ? "negative" : "flat";
  return `<span class="delta-badge delta-${tone}">${escapeHtml(label)}</span>`;
}

function formatInteger(value) {
  return Number(value || 0).toLocaleString("es-AR");
}

function formatDate(value) {
  if (!value) return "Sin datos";
  return new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function formatDay(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("es-AR", { dateStyle: "short" }).format(new Date(`${value}T09:00:00-03:00`));
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
}
