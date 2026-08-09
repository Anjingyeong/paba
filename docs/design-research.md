# Design research — kiosk & manager console

> Method note: the plan references an `imagegen` step for synthetic concept
> imagery. That tool is not available in this environment, so concept exploration
> was done with **inline-SVG mockups** (see `templates/design-system/showcase.html`
> and the concept block below) instead of raster renders. Everything else follows
> the plan: study real operational patterns, record adopt/reject rationale, choose
> one direction, and encode it as tokens in `DESIGN.md`.

## References studied

| Source | What we looked at | Adopt | Reject |
| --- | --- | --- | --- |
| IBM Carbon Design System — Color (https://carbondesignsystem.com/elements/color/overview/) | Gray 10 / Gray 100 theme token roles, interactive Blue 60, support colors | Token role model (background/layer/field/border/text/interactive), WCAG-AA contrast pairs | Full multi-theme (White/Gray90) matrix — we ship one light + one dark only |
| Carbon — Data table usage (https://carbondesignsystem.com/components/data-table/usage/) | Row density, sticky header, zebra vs. bordered, responsive strategy | Manager tables use a bordered, comfortable-density table with sticky header; collapse to labeled cards under 672px | Inline row-expansion for our simple lists |
| Carbon — Notification usage (https://carbondesignsystem.com/components/notification/usage/) | Inline vs. toast, status color + icon (never color alone) | Toast for transient punch confirmations; inline notification for blockers, always icon+text | Auto-dismiss on blocking errors |
| Carbon — UI shell / side-nav | Fixed side-nav + scrollable content region | Manager shell: fixed left sidenav (rail on mobile), independent scroll body | Header-only nav (too shallow for the console's many sections) |
| Kiosk/POS timeclock patterns (shared-tablet clock-in screens) | Large single primary action, immediate confirmation, fast auto-lock | Kiosk: full-screen cover, one big current action, 3s success then auto-lock | Employee roster / numeric name lists (enumeration + privacy leak) |
| WCAG 2.2 quick-ref (https://www.w3.org/WAI/WCAG22/quickref/) | Target size (2.5.8 ≥24px; we use ≥44px), focus not obscured, contrast | 44×44 min targets, always-visible 2px focus ring, non-color status | — |

## Personas the design must serve

1. **바쁜 공유-태블릿 직원** — one-handed, gloved, 3-second interaction, Korean UI, no reading small text.
2. **월마감 점장** — long sessions, dense tables, keyboard-driven, needs clear blockers.
3. **저시력/키보드 사용자** — 200% zoom, visible focus, screen-reader labels, no color-only signals.
4. **한 손 사용 제약 사용자** — large targets, reachable primary actions, no precise gestures.

## Concept exploration (SVG mockups) → decision

Three directions were sketched as SVG in the showcase's "concepts" section:

- **A. Split-card kiosk** — clock actions as four equal cards. Rejected: divides attention, smaller targets.
- **B. Single-action cover** *(chosen)* — full-screen cover showing only the *next* valid action as one large button, with break state and a confirmation view. Chosen: matches persona 1 & 4, minimizes error, supports fast auto-lock.
- **C. Dashboard-first manager home** — KPI tiles above the fold. Deferred: analytics dashboards are explicitly out of scope; the manager home instead surfaces today's status + the exception queue.

**Decision:** Kiosk = Concept B full-screen cover. Manager = fixed sidenav + scroll-body shell with bordered tables and inline blockers. Encoded in `DESIGN.md`.
