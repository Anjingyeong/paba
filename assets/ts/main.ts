/**
 * Frontend entry point.
 *
 * Todo 1 only needs the Bun bundling pipeline to be real and reproducible; the
 * full design system (tokens, showcase, kiosk/manager shells) is built in Todo 2.
 * We import one Carbon Web Component so the bundle exercises the real toolchain
 * and locally vendors Carbon (no CDN at runtime).
 */

import "@carbon/web-components/es/components/button/index.js";

// Signal to templates that the bundle loaded (progressive enhancement only).
document.documentElement.dataset.pbFrontend = "ready";
