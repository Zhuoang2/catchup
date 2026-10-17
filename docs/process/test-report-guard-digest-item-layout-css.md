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
