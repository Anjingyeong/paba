/**
 * Design-system entry point.
 *
 * Registers the locally-bundled Carbon Web Components used across the kiosk and
 * manager surfaces (no CDN at runtime) and wires the light/dark theme toggle used
 * on the showcase. Progressive enhancement only — the server-rendered markup is
 * fully usable without this script.
 */

import "@carbon/web-components/es/components/button/index.js";
import "@carbon/web-components/es/components/text-input/index.js";
import "@carbon/web-components/es/components/tag/index.js";

const root = document.documentElement;

const toggle = document.querySelector<HTMLButtonElement>("[data-theme-toggle]");
if (toggle) {
  toggle.addEventListener("click", () => {
    const isDark = root.getAttribute("data-theme") === "dark";
    root.setAttribute("data-theme", isDark ? "light" : "dark");
    toggle.setAttribute("aria-pressed", String(!isDark));
  });
}

root.dataset.pbDesignSystem = "ready";
