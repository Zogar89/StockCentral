import "./styles/global.css";
import CatalogApp from "./CatalogApp.svelte";
import { mount } from "svelte";

mount(CatalogApp, {
  target: document.getElementById("app"),
});
