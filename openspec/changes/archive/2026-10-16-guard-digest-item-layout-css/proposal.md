# Proposal

## Why

Two parts of the digest item layout from `improve-single-item-topics` (#25) have no test guarding them (issue #33). Neither causes a bug today, but either could regress silently:

- **The placement guard reads only `layout.css`.** "places digest headings beside summaries only above 1100px" in `frontend/src/styles/tokens.test.ts` checks that item placements appear only inside `@container (width > 1100px)`. A `grid-column` or `grid-row` on an item child in `components.css` or `base.css` would bring back the overlap that #25 fixed, where titles were painted over summaries at 900 px and below, and no test would fail.
- **No guard against a vertical rule between an item's heading and its summary.** The archived design `2026-10-16-improve-single-item-topics`, D3, says there is none. The spec subagent's mutations (a `border-left` on the wide summary rule, or on the wide `.items > .item` rule) passed every style test.

## What Changes

- **Extend the CSS structure guards in `frontend/src/styles/tokens.test.ts`** so they read every owned style file: `base.css`, `layout.css`, and `components.css`, the `OWNED` list in `frontend/scripts/check-style-coverage.py`.
- **Which rules count.** A rule counts when the rightmost compound of one of its selectors is the item or an item child: it has the class `.item`, `.item-meta`, `.item-title`, `.summary`, or `.summary-unavailable`, including inside `:is()` or `:where()`, or it is the `*` in `.items > .item > *`. Whitespace is normalized first. A rule that only mentions these classes earlier in the selector, such as `.item:hover .badge` or `.summary li`, styles another element and does not count. Elements inside the summary are a known limit. (Amended after review, 2026-10-16.)
- **Placement guard.** Outside `@container (width > 1100px)`, a counted rule in any owned file must not:
  - set a placement property on an item child: `grid-area`, `grid-column`, `grid-row`, or their `-start` / `-end` longhands
  - set a grid template on the item: `grid`, `grid-template`, `grid-template-columns`, `grid-template-rows`, or `grid-template-areas`
- **Vertical-rule guard.** In any owned file, a counted rule must not set any `border*` property except the `border-top*` and `border-bottom*` families and `border-radius`. This covers `border-left`, `border-right`, the `border-inline` family, their width, style, and color longhands, and the shorthands `border`, `border-width`, `border-style`, and `border-color`.
- **No change** to CSS, components, behavior, or specs.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None. This change only adds tests; `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- `frontend/src/styles/tokens.test.ts`: the existing `layoutRules` parser is reused, and the new or extended tests read the three owned files.
- No runtime code, dependency, or build change.
