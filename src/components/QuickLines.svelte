<script>
  import { lineMeta, quickLineHint, quickLineLabel, quickLineValues } from "../lib/shared.js";

  export let available = [];
  export let targetSelector = ".group-section";
  export let help = "";
  export let id = "";

  $: availableSet = new Set(available);
  $: visibleLines = quickLineValues.filter((line) => availableSet.has(line));

  function scrollToLine(line) {
    help = "";
    const target = [...document.querySelectorAll(targetSelector)].find((node) => node.dataset.line === line);
    if (!target) {
      help = `No hay resultados visibles para ${quickLineLabel(line)}.`;
      return;
    }
    document.querySelectorAll(`${targetSelector}.quick-target`).forEach((node) => node.classList.remove("quick-target"));
    target.classList.add("quick-target");
    target.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => target.classList.remove("quick-target"), 1400);
  }
</script>

<div id={id || undefined} class="quick-lines">
  {#each visibleLines as line}
    {@const tone = lineMeta[line]?.quickTone || "default"}
    <button class={`quick-line quick-line-${tone}`} type="button" data-line={line} title={quickLineHint(line)} aria-label={`${quickLineLabel(line)}. ${quickLineHint(line)}`} on:click={() => scrollToLine(line)}>
      <span>{quickLineLabel(line)}</span>
    </button>
  {/each}
</div>
<span class="quick-lines-cue" aria-hidden="true"></span>
