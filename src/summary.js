import "./styles/global.css";
import SummaryApp from "./SummaryApp.svelte";
import { mount } from "svelte";

mount(SummaryApp, {
  target: document.getElementById("app"),
});
