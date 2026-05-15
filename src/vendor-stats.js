import "./styles/global.css";
import VendorStatsApp from "./VendorStatsApp.svelte";
import { mount } from "svelte";

mount(VendorStatsApp, {
  target: document.getElementById("app"),
});
