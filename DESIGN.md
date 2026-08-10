# DESIGN.md — Paris Baguette payroll UI

This document is the visual contract for the server-rendered landing, kiosk, and
manager surfaces. Tokens live in `assets/styles/tokens.css`; reusable primitives
and page topology live in `assets/styles/app.css` and `assets/styles/kiosk.css`.
The UI remains dependency-light and works without a CDN.

## 1. Direction and design brief

The product is a calm operations workspace with an artisan-bakery warmth:
parchment and ivory surfaces, espresso ink, and a pâtisserie-berry accent with
caramel highlights. It should feel modern and tactile — evoking a French
boulangerie without imitating the real Paris Baguette brand blue or logo. The
memorable moment is the landing workspace: two clear paths, kiosk and manager,
presented as layered operational surfaces rather than a generic marketing hero.

Primary journeys:

- Store staff enter the kiosk flow quickly, often with one hand or gloves.
- Managers scan attendance, then move to payroll, insurance, close, and exports.
- A keyboard or screen-reader user can reach every destination and understand the
  current state without relying on color.

## 2. Themes and color roles

Light mode is the default. Dark mode follows the system and can be explicitly
selected with `data-theme`. Every visible color must come from a role token.

| Role token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--pb-background` | `#f6efe4` | `#1b1410` | app canvas (parchment / espresso) |
| `--pb-background-soft` | `#efe4d3` | `#241a13` | atmospheric tint |
| `--pb-layer` | `#fffaf3` | `#271d16` | cards and panels (ivory) |
| `--pb-layer-raised` | `#fffdf8` | `#33261d` | elevated controls |
| `--pb-layer-accent` | `#f3e7d5` | `#3b2c21` | hover and zebra rows |
| `--pb-field` | `#fffaf3` | `#2d2118` | inputs |
| `--pb-border` | `#e3d3ba` | `#4e3c2d` | quiet dividers |
| `--pb-border-strong` | `#94774d` | `#9c7a4f` | input and focus support (≥3:1) |
| `--pb-text` | `#2a1e14` | `#f7efe3` | primary text |
| `--pb-text-secondary` | `#6f5b45` | `#d3c1a9` | secondary text |
| `--pb-interactive` | `#9c2743` | `#f2a2b3` | primary action and focus (berry) |
| `--pb-interactive-hover` | `#7f1d36` | `#f7bcc8` | hover/pressed action |
| `--pb-interactive-soft` | `#f6e3e0` | `#4a2a2f` | active navigation and chips |
| `--pb-on-interactive` | `#fffaf3` | `#1b1410` | text on primary |
| `--pb-support-error` | `#b23225` | `#ff9d94` | errors and blockers |
| `--pb-support-success` | `#2f7d4f` | `#8fce87` | success |
| `--pb-support-warning` | `#8a6410` | `#f2c66b` | warnings |

Text/background pairs target WCAG 2.2 AA. Status is never color-only; pair its
dot with text and, where appropriate, an inline SVG icon.

## 3. Typography, spacing, and geometry

No CDN fonts. `--pb-font` prioritizes SUIT, Pretendard, and installed CJK system
faces. Numeric data uses tabular figures.

Type scale: caption `0.75rem`, body `1rem`, body-lg `1.125rem`, h3 `1.25rem`,
h2 `1.625rem`, h1 `2.125rem`, display `clamp(2.5rem, 6vw, 4.75rem)`. Display text
uses balanced wrapping; Korean body copy uses pretty wrapping and never clips.

Spacing follows the existing 2/4/8/12/16/24/32/48 scale. Geometry varies by
hierarchy: `10px` compact controls, `16px` cards, `24px` major surfaces, and a
pill radius only for compact labels and primary links.

## 4. Material and elevation

The canvas uses two radial light fields over a base color. Panels are opaque or
near-opaque surfaces with a quiet border, a soft ambient shadow, and an inset
highlight. The lighting direction is consistently top-left. Blur is optional
support, never the only material treatment.

Landing illustrations use one cohesive editorial 3D clay language: matte ivory
materials, navy structure, sky-blue controls, and a restrained berry accent.
Scenes must explain a real task (check-in or payroll), contain no logos or relied-on
in-image text, and keep enough quiet background for responsive cropping.

Use `--pb-shadow-card`, `--pb-shadow-raised`, and `--pb-shadow-overlay`; do not add
one-off shadows. Layering tokens remain `--pb-z-sticky`, `--pb-z-overlay`, and
`--pb-z-toast`.

## 5. Reusable primitives and states

- `.pb-brand`: compact brand mark plus product label; default and inverse states.
- `.pb-btn`: primary, secondary, and text-link variants; default, hover, focus,
  active, and disabled states.
- `.pb-panel`: shared raised surface for entry cards, sections, forms, and tables.
- `.pb-entry-card`: landing destination with icon, eyebrow, title, copy, and CTA;
  a task illustration may occupy the secondary pane; hover/focus lifts the surface
  and strengthens the rim.
- `.pb-landing__visual`: meaningful landing illustration with descriptive alt text,
  intrinsic dimensions, tokenized border/elevation, and content-safe cropping.
- `.pb-stat`: compact operational summary using tabular values and a label.
- `.pb-status`: text plus semantic dot; success, warning, and error variants.
- `.pb-table`: sticky-header data table; responsive labeled rows below the compact
  breakpoint.
- `.pb-empty`: composed empty state with heading and guidance, never a blank row.
- `.pb-shell`: manager fixed-navigation shell with one scroll owner.
- `.pb-kiosk`: kiosk cover with exactly one visible state and oversized actions.

The design-system showcase remains the primitive state harness. New repeated
patterns must be added here before being copied to additional screens.

## 6. Motion and interaction

Mechanisms are adapted from beui.dev `button` and `shared-layout-bg`:

- Color/opacity transitions use `--pb-motion-fast` (`160ms`) or
  `--pb-motion-base` (`260ms`) with `--pb-ease-out`.
- Hover-capable pointers lift interactive cards by `-4px`; touch devices do not
  receive sticky hover behavior.
- Pressed buttons use `scale(0.98)` and retarget immediately on release.
- Kiosk state changes use opacity and a short vertical transform; no layout
  properties animate.
- Navigation uses a soft active background instead of decorative motion.
- Under `prefers-reduced-motion: reduce`, transforms and entrance effects collapse
  to an immediate state change; the kiosk three-second auto-lock still functions.

## 7. Responsive topologies and scroll ownership

Breakpoints are 375, 768, and 1280 pixels. Intrinsic grids use
`minmax(min(18rem, 100%), 1fr)` so cards never force horizontal overflow.

- Landing: document scroll; fixed-width content limiter; the split hero stacks
  below tablet landscape, and two destination cards become one column when space
  is tight. Card illustrations become shallow top panes before the single-column
  transition.
- Kiosk: `100dvh` cover; the active state owns its internal layout; body does not
  scroll during normal use.
- Manager: `.pb-shell` is bounded by `100dvh`; navigation stays fixed and
  `.pb-shell__body` is the only vertical scroll owner. Below 768px, navigation
  becomes a wrapping top rail and document flow resumes.

## 8. Accessibility, cognitive constraints, and debt

Focus is always visible with a two-pixel interactive outline and offset. Targets
are at least 44 by 44 pixels. Headings and destinations use plain Korean labels;
no task depends on remembering an unlabeled icon. Reduced motion, dark mode,
200-percent zoom, keyboard navigation, and CJK line breaking are first-class.

Accepted debt: the landing status copy describes entry points, not live system
health. It must not be presented as telemetry until a real health/status contract
is wired. No unresolved accessibility debt is accepted for these three surfaces.
