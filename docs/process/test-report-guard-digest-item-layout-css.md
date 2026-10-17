# Guard digest item layout CSS: implementation checks

2026-10-16, branch `guard-digest-item-layout-css`. The guards read `base.css`, `layout.css`, and `components.css`; no stylesheet change is retained.

| Check | Actual result |
| --- | --- |
| `cd frontend && npm test -- --run` | **165 passed** in **13 files**. |
| `cd frontend && npm run build` | Passed TypeScript and Vite build; **41 modules** transformed. |
| `python3 frontend/scripts/check-style-coverage.py` | Passed: **9** static UI classes with C7 rules but no app rules (all documented), **11** prototype-only allow-list entries, **0** uncovered prototype selectors. |

Each temporary mutation was applied alone, followed by `cd frontend && npm test -- --run src/styles/tokens.test.ts`. The affected guard failed with the stylesheet and selector in its diagnostic; after reverting the mutation, all focused tests passed. None of the mutations is in the final diff.

| Temporary CSS mutation | Red result | Green after revert |
| --- | --- | --- |
| `components.css` `.summary`: `grid-column: 2` | Placement guard failed, naming `src/styles/components.css: .summary` (1 failed, 10 passed). | 11 passed. |
| `components.css` `.item`: `grid-template-columns: 1fr 1fr` | Placement guard failed, naming `src/styles/components.css: .item` (1 failed, 10 passed). | 11 passed. |
| `base.css` new `.item-title { grid-row: 3; }` | Placement guard failed, naming `src/styles/base.css: .item-title` (1 failed, 10 passed). | 11 passed. |
| `layout.css` wide `.items > .item > .summary, …`: `border-left: 1px solid var(--border)` | Vertical-rule guard failed, naming `src/styles/layout.css` and both selectors (1 failed, 11 passed). | 12 passed. |
| `layout.css` wide `.items > .item`: `border-right: 1px solid` | Vertical-rule guard failed, naming `src/styles/layout.css: .items > .item` (1 failed, 11 passed). | 12 passed. |
| `components.css` `.item-title`: `border: 1px solid` | Vertical-rule guard failed, naming `src/styles/components.css: .item-title` (1 failed, 11 passed). | 12 passed. |

No painted layout or responsive-width browser check was performed. This test-only change guards the CSS declarations, not the rendered geometry.

## Review fixes, round 1

The guards now inspect the rightmost compound of each comma-separated selector and the full placement and border property families. The changes are test-only; none of the temporary stylesheet edits below remains.

| Check | Re-run result |
| --- | --- |
| `cd frontend && npm test -- --run` | **165 passed** in **13 files**. |
| `cd frontend && npm run build` | TypeScript and Vite build passed; **41 modules** transformed. |
| `python3 frontend/scripts/check-style-coverage.py` | Passed: **9** static UI classes with C7 rules but no app rules, **11** prototype-only allow-list entries, **0** uncovered prototype selectors. |

Each edit was tested alone with `cd frontend && npm test -- --run src/styles/tokens.test.ts`, then reverted and tested again. Red means exactly one guard failed with the file and selector named (11 other tests passed); green means all **12** focused tests passed.

| Temporary CSS mutation | With edit | After revert |
| --- | --- | --- |
| `components.css` `.summary`: `grid-column: 2` | Placement red: `components.css: .summary`. | Green. |
| `components.css` `.item`: `grid-template-columns: 1fr 1fr` | Placement red: `components.css: .item`. | Green. |
| `base.css` new `.item-title { grid-row: 3; }` | Placement red: `base.css: .item-title`. | Green. |
| `layout.css` wide `.items > .item > .summary, …`: `border-left: 1px solid var(--border)` | Vertical-rule red: `layout.css` and both selectors. | Green. |
| `layout.css` wide `.items > .item`: `border-right: 1px solid` | Vertical-rule red: `layout.css: .items > .item`. | Green. |
| `components.css` `.item-title`: `border: 1px solid` | Vertical-rule red: `components.css: .item-title`. | Green. |
| `layout.css` new wide `.items > .item > p.summary { border-left: 1px solid; }` | Vertical-rule red: `layout.css: .items > .item > p.summary`. | Green. |
| `components.css` `.summary`: `border-left-style: solid; border-left-width: 1px` | Vertical-rule red: `components.css: .summary`. | Green. |
| `components.css` `.item-title`: `grid-area: 2 / 1` | Placement red: `components.css: .item-title`. | Green. |
| `layout.css` new `.items>.item { grid-template: auto / 1fr 1fr; }` outside the query | Placement red: `layout.css: .items>.item`. | Green. |
| `components.css` new `.topic .item { grid-template-columns: 1fr 1fr; }` | Placement red: `components.css: .topic .item`. | Green. |
| `components.css` new `:is(.summary) { grid-column: 2; }` | Placement red: `components.css: :is(.summary)`. | Green. |
| `components.css` new `.item:hover .badge { border: 1px solid; }` | Green, descendant badge not targeted. | Green. |
| `components.css` new `.summary li { border-left: 1px solid; }` | Green, documented descendant limit. | Green. |
| `components.css` `.item`: `border-radius: 2px` | Green, allowed radius. | Green. |

No browser geometry check was performed in this round.
