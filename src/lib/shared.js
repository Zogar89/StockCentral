export const siteContactUrl = "https://github.com/Zogar89/CentraldeFilamentos/issues/new";
export const siteRepoUrl = "https://github.com/Zogar89/CentraldeFilamentos";

export const lineMeta = {
  "PLA Standard": { label: "PLA Standard", quickLabel: "PLA", quickTone: "pla", help: "PLA comun: facil de imprimir y el mas buscado para piezas generales.", rank: 10 },
  "PLA+": { label: "PLA+", quickLabel: "PLA+", quickTone: "plus", help: "PLA modificado: suele buscarse por mejor resistencia o terminacion.", rank: 20 },
  "PLA Flexible": { label: "PLA Flexible", quickLabel: "Flex", quickTone: "flex", help: "PLA+ flexible de 3N3/3NFLEX: piezas con algo de elasticidad.", rank: 25 },
  PETG: { label: "PETG", quickLabel: "PETG", quickTone: "petg", help: "Mas tenaz y resistente a temperatura que PLA; util para piezas funcionales.", rank: 30 },
  ABS: { label: "ABS", quickLabel: "ABS", quickTone: "abs", help: "Material tecnico para piezas resistentes; suele requerir cama caliente y buena ventilacion.", rank: 40 },
  TPU: { label: "TPU", quickLabel: "TPU", quickTone: "flex", help: "Flexible/elastico, usado para piezas que necesitan doblarse o absorber impacto.", rank: 50 },
  Flex: { label: "Flex", quickTone: "flex", help: "Linea flexible de 3N3; pensada para piezas blandas o elasticas.", rank: 51 },
  Simpliflex: { label: "Simpliflex", quickTone: "flex", help: "Flexible de Grilon3: alternativa elastica con impresion mas amigable.", rank: 52 },
  "PLA Astra": { label: "PLA Astra", quickLabel: "Astra", quickTone: "astra", help: "PLA con brillo tipo glitter. Ideal cuando importa la estetica de la pieza.", rank: 60 },
  "PLA Silk": { label: "PLA Silk", quickLabel: "Silk", quickTone: "silk", help: "PLA de acabado brillante/sedoso, muy usado en piezas decorativas.", rank: 61 },
  "PLA Boutique": { label: "PLA Boutique", quickLabel: "Boutique", quickTone: "boutique", help: "Linea de colores especiales de Grilon3.", rank: 62 },
  "PLA Wood": { label: "PLA Wood", quickLabel: "Wood", quickTone: "wood", help: "PLA con terminacion tipo madera.", rank: 63 },
  "PLA 850": { label: "PLA 850 - tecnico", help: "PLA de linea especifica, distinto del PLA Standard.", rank: 70 },
  "PLA 870": { label: "PLA 870 - tecnico", help: "PLA de linea especifica, distinto del PLA Standard.", rank: 71 },
  "PLA Zeta": { label: "PLA Zeta - translucido/especial", help: "Linea especial de Grilon3; no es PLA Standard.", rank: 72 },
  "PETG Clear": { label: "PETG Clear - translucido", help: "PETG translucido/clear para piezas donde importa el pasaje de luz.", rank: 80 },
  "E-PET": { label: "E-PET - PET reciclado", help: "PET reciclado. Distinto de PETG.", rank: 81 },
  "PP-T": { label: "PP-T - polipropileno", help: "Polipropileno tecnico; util por su resistencia quimica y flexibilidad.", rank: 90 },
  "Nylon 6": { label: "Nylon 6", quickLabel: "Nylon", quickTone: "nylon", help: "Nylon tecnico para piezas exigentes.", rank: 100 },
  "Nylon 12": { label: "Nylon 12", quickTone: "nylon", help: "Nylon tecnico con otra formulacion; no mezclar con Nylon 6.", rank: 101 },
  "Acetal-POM": { label: "Acetal-POM", help: "Material tecnico de baja friccion, usado en piezas mecanicas.", rank: 110 },
  "PVA Soluble": { label: "PVA soluble", help: "Material soluble, usualmente para soportes.", rank: 120 },
  "Sampler / lápiz 3D": { label: "Sampler / lápiz 3D", help: "Muestras cortas en metros, pensadas para lápiz 3D o prueba de material; no son bobinas.", rank: 130 },
};

export const quickLineValues = ["PLA Standard", "PLA+", "PLA Flexible", "PETG", "ABS", "PLA Astra", "PLA Silk", "PLA Boutique", "PLA Wood", "TPU", "Nylon 6"];

export const zoneOrder = {
  "Zona Norte": 0,
  "Zona Oeste": 1,
  "Zona Sur": 2,
};

export function dataUrl(path) {
  return `${import.meta.env.BASE_URL}${path}`;
}

export async function fetchJson(path, fallback = {}) {
  try {
    const response = await fetch(dataUrl(path));
    if (!response.ok) return fallback;
    return await response.json();
  } catch {
    return fallback;
  }
}

export function formatDate(value) {
  if (!value) return "Sin datos";
  return new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Argentina/Buenos_Aires" }).format(new Date(value));
}

export function formatDay(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeZone: "America/Argentina/Buenos_Aires" }).format(new Date(`${value}T09:00:00-03:00`));
}

export function formatTime(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("es-AR", { timeStyle: "short", timeZone: "America/Argentina/Buenos_Aires" }).format(new Date(value));
}

export function formatInteger(value) {
  return Number(value || 0).toLocaleString("es-AR");
}

export function formatWeightLabel(weightG) {
  if (!weightG) return "";
  return `${Number(weightG) / 1000} kg`;
}

export function lineLabel(product) {
  if (isSamplerProduct(product)) return "Sampler / lápiz 3D";
  if (!product.variant && product.material === "PLA") return "PLA Standard";
  return product.variant || product.material || "Sin clasificar";
}

export function lineOptionLabel(line) {
  return lineMeta[line]?.label || line;
}

export function lineRank(line) {
  return lineMeta[line]?.rank ?? 999;
}

export function quickLineLabel(line) {
  return lineMeta[line]?.quickLabel || lineOptionLabel(line);
}

export function quickLineHint(line) {
  return lineMeta[line]?.help || `${line}: linea/material detectado desde las fuentes de stock.`;
}

export function brandRank(brand) {
  if (brand === "Grilon3") return "0";
  if (brand === "3N3") return "1";
  return "9";
}

export function diameterLabel(product) {
  return product.diameter_mm ? `${product.diameter_mm} mm` : "Sin diametro";
}

export function formatPresentation(product) {
  const weight = formatWeightLabel(product.weight_g);
  if (weight) return weight;
  const samplerLength = samplerLengthLabel(product);
  if (samplerLength) return `Sampler ${samplerLength}`;
  return "";
}

export function samplerLengthLabel(product) {
  const names = (product.offers || []).map((offer) => offer.original_name).join(" ");
  const match = names.match(/\bSAMPLER\b.*?\bX\s*(\d+(?:[,.]\d+)?)\s*M\b/i);
  if (!match) return "";
  return `${match[1].replace(",", ".")} m`;
}

export function isSamplerProduct(product) {
  return Boolean(samplerLengthLabel(product));
}

export function matchesSearchTerms(query, values) {
  const tokens = searchTokens(values.join(" "));
  return searchTokens(query).every((term) => tokens.some((token) => matchesSearchToken(term, token)));
}

export function matchesSearchToken(term, token) {
  if (term === "pla") return token === "pla" || token === "pla+";
  return token === term || token.startsWith(term);
}

export function searchTokens(value) {
  return foldText(value)
    .toLowerCase()
    .split(/[^a-z0-9+]+/)
    .filter(Boolean);
}

export function foldText(value) {
  return String(value || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
}

export function slugText(value) {
  return foldText(value).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export function providerAnchorId(sourceId) {
  return `proveedor-${sourceId}`;
}

export function stockDelta(stats) {
  const delta = Number(stats?.stock_delta_units);
  if (!Number.isFinite(delta)) return null;
  return {
    value: delta,
    label: delta > 0 ? `+${delta}` : `${delta}`,
    tone: delta > 0 ? "up" : delta < 0 ? "down" : "flat",
  };
}

export function sourceWhatsappUrl(source, message) {
  const separator = source.contact_whatsapp_url.includes("?") ? "&" : "?";
  return `${source.contact_whatsapp_url}${separator}text=${encodeURIComponent(message)}`;
}

export function productBaseName(product) {
  const presentation = formatWeightLabel(product.weight_g);
  if (!presentation) return product.display_name;
  return product.display_name.replace(` ${presentation}`, "").replace(/\s+/g, " ").trim();
}

export function comparePresentations(left, right) {
  return presentationRank(left) - presentationRank(right) || left.display_name.localeCompare(right.display_name, "es-AR");
}

export function presentationRank(product) {
  if (Number.isFinite(Number(product.weight_g)) && Number(product.weight_g) > 0) return Number(product.weight_g);
  if (isSamplerProduct(product)) return 10_000_000;
  return 20_000_000;
}

export function colorSwatchStyle(product) {
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

export function colorSwatchLabel(color) {
  if (!color) return "";
  return color.split(/\s+/).slice(0, 2).map((word) => word[0]).join("").toUpperCase();
}

export function pantoneSwatchLabel(pantone) {
  return String(pantone || "").replace(/^Pantone\s+/i, "P ");
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
    ["BLANCO PERLA", "#f6f1df"], ["BLANCO", "#f8f8f2"], ["NEGRO", "#111111"],
    ["GRIS PLATA", "#b8bec6"], ["GRIS ACERO", "#8e98a3"], ["GRIS ESPACIAL", "#6f747b"],
    ["GRIS PLOMO", "#565b63"], ["GRIS", "#9ea3aa"], ["AZUL DE PRUSIA", "#003153"],
    ["AZUL TRAFUL", "#1976a3"], ["ZAFIRO", "#0f52ba"], ["AZUL", "#1f6feb"],
    ["VERDE MANZANA", "#8bc34a"], ["VERDE LIMA", "#9bdc28"], ["VERDE AVIADOR", "#4f6f52"],
    ["ESMERALDA", "#1f9d73"], ["PINO", "#2f5d50"], ["VERDE", "#2e7d32"],
    ["ROJO CARMIN", "#960018"], ["ROJO", "#d32f2f"], ["RUBI", "#9b111e"],
    ["BORDO", "#6d1a25"], ["ROBY", "#8e1233"], ["AMARILLO", "#f5c400"],
    ["NARANJA PRAGA", "#e87522"], ["NARANJA", "#f57c00"], ["FUCSIA", "#c2185b"],
    ["MAGENTA", "#d81b60"], ["ROSA", "#f3a6bd"], ["VIOLETA", "#7b3fb3"],
    ["UVA", "#6f2da8"], ["LILA", "#b58ad6"], ["LAVANDA", "#b7a0d8"],
    ["TURQUESA", "#00a6a6"], ["CALIPSO", "#00a9c7"], ["CELESTE", "#8ecae6"],
    ["ACQUA", "#7ddfd4"], ["DORADO", "#c9a227"], ["ORO", "#d4af37"],
    ["BRONCE", "#a97142"], ["COBRE", "#b87333"], ["PLATINO", "#c7c7c7"],
    ["TITANIO", "#7f7f7f"], ["CHOCOLATE", "#5d342f"], ["CAOBA", "#704214"],
    ["CEREZO", "#8d3f2d"], ["NOGAL", "#6f4e37"], ["CARPINCHO", "#9b7653"],
    ["DULCE DE LECHE", "#c6925b"], ["HABANO", "#8f6b4a"], ["ARENA", "#d6c6a8"],
    ["HUESO", "#e5dcc3"], ["PIEL", "#e3b38e"], ["SALMON", "#fa8072"],
    ["CREMA", "#f4e3bd"], ["PERLA CALIDO", "#eadfca"], ["PERLA FRIO", "#dbe3ea"],
    ["PERLA", "#e8e3d3"], ["CARBON", "#2f3437"], ["AZABACHE", "#161819"],
    ["DARK", "#1d1b2f"], ["NOCHE", "#13172b"], ["NEBULA", "#3a255f"],
    ["JADE", "#00a86b"], ["NOVA", "#4b3f72"], ["OPTICO", "#f8f8ff"],
    ["RUSTICO", "#a9825a"],
  ];
  const match = rules.find(([token]) => folded.includes(token));
  return match ? match[1] : "#d7d7dc";
}
