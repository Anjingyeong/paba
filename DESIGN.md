# DESIGN.md — Paris Baguette payroll UI

The system tokens below are the single source of truth for both surfaces. They are
implemented in `assets/styles/tokens.css` (values) and `assets/styles/app.css`
(component/layout rules), consumed by server-rendered templates and locally-bundled
`@carbon/web-components` (no CDN at runtime).

Grounded in IBM Carbon (see `docs/design-research.md`); we ship exactly **one light
and one dark theme**, both meeting WCAG 2.2 AA.

## Themes & color roles

Theme-aware: light on bare `:root`; dark under `@media (prefers-color-scheme: dark)`
and `:root[data-theme="dark"]`; an explicit `:root[data-theme="light"]` wins back.

| Role token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--pb-background` | `#f4f4f4` | `#161616` | app canvas |
| `--pb-layer` | `#ffffff` | `#262626` | cards, panels, table |
| `--pb-layer-accent` | `#e8e8e8` | `#393939` | hover/zebra |
| `--pb-field` | `#ffffff` | `#393939` | inputs |
| `--pb-border` | `#8d8d8d` | `#6f6f6f` | dividers, input border |
| `--pb-text` | `#161616` | `#f4f4f4` | primary text |
| `--pb-text-secondary` | `#525252` | `#c6c6c6` | secondary text |
| `--pb-interactive` | `#0f62fe` | `#4589ff` | primary action, focus |
| `--pb-on-interactive` | `#ffffff` | `#161616` | text on primary |
| `--pb-support-error` | `#da1e28` | `#ff8389` | errors/blockers |
| `--pb-support-success` | `#198038` | `#42be65` | success |
| `--pb-support-warning` | `#b28600` | `#f1c21b` | warnings (needs icon) |

Contrast: text/background pairs are ≥ 4.5:1; large text and UI borders ≥ 3:1. Status
is **never** color-only — always paired with an icon and/or text label.

## Typography

No CDN fonts (CSP). Stack prioritizes installed CJK faces:
`--pb-font: "IBM Plex Sans", "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR", system-ui, sans-serif;`
(IBM Plex Sans is self-hosted in production; the stack degrades cleanly to system CJK.)

Scale (rem): `--pb-type-caption:0.75`, `body:1`, `body-lg:1.125`, `h3:1.25`,
`h2:1.5`, `h1:2`, `display:2.625`. Line-height 1.4–1.5; Korean long-form never
truncates — it wraps.

## Spacing & radius (Carbon scale)

`--pb-space-1:0.125rem` … `2:0.25 · 3:0.5 · 4:0.75 · 5:1 · 6:1.5 · 7:2 · 8:3rem`.
Radius `--pb-radius:4px`. Container max width for reading columns: 40rem.

## Elevation / layers

Flat by default; `--pb-shadow-overlay` for modals/toasts only. Layering order
tokens `--pb-z-sticky:100`, `--pb-z-overlay:1000`, `--pb-z-toast:1100`.

## State, focus, motion

- **Focus**: always-visible `2px solid var(--pb-interactive)` outline with `2px`
  offset; never removed. Focus is never obscured by sticky headers/sidenav.
- **Hover/active/disabled**: distinct, and not conveyed by color alone.
- **Reduced motion**: under `prefers-reduced-motion: reduce` all transitions/animations
  collapse to none; the kiosk 3s auto-lock still functions (no motion required).

## Touch & targets

Minimum interactive target **44×44px** (exceeds WCAG 2.5.8). Kiosk primary action
is full-width and tall. Adequate spacing between targets to avoid mis-taps.

## Responsive breakpoints

`sm 375 · md 768 · lg 1280`. All layouts verified at 375/768/1280 and at 200% zoom
with **zero horizontal overflow**; wide content (tables) scrolls inside its own
container, never the page body.

## Screen topologies

### Kiosk — full-screen cover (`.pb-kiosk`)
A fixed, full-viewport cover. States: device-pairing, locked, employee-code+PIN,
**single current punch action**, break state, success confirmation, correction
request, network-failure. Shows minimal synthetic name only during an action;
auto-locks within 3s and clears state (no data survives back/refresh).

### Manager — fixed sidenav + scroll body (`.pb-shell`)
`--pb-sidenav-width:16rem`. Fixed left sidenav (collapses to a top rail < 768px),
independent scrollable `.pb-shell__body`. No double scrollbars. Tables become
labeled cards on small screens.
