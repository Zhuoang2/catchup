# Proposal

## Why

Two parts of the digest item layout from `improve-single-item-topics` (#25) have no test guarding them (issue #33). Neither causes a bug today, but either could regress silently:

- **The placement guard reads only `layout.css`.** "places digest headings beside summaries only above 1100px" in `frontend/src/styles/tokens.test.ts` checks that item placements appear only inside `@container (width > 1100px)`. A `grid-column` or `grid-row` on an item child in `components.css` or `base.css` would bring back the overlap that #25 fixed, where titles were painted over summaries at 900 px and below, and no test would fail.
- **No guard against a vertical rule between an item's heading and its summary.** The archived design `2026-10-16-improve-single-item-topics`, D3, says there is none. The spec subagent's mutations (a `border-left` on the wide summary rule, or on the wide `.items > .item` rule) passed every style test.

## What Changes

- **Extend the CSS structure guards in `frontend/src/styles/tokens.test.ts`** so they read every owned style file: `base.css`, `layout.css`, and `components.css`, the `OWNED` list in `frontend/scripts/check-style-coverage.py`.
- **Placement guard.** Outside `@container (width > 1100px)`, no rule in any owned file may:
  - set `grid-column` or `grid-row` on `.item-meta`, `.item-title`, `.summary`, `.summary-unavailable`, or `.items > .item > *`
  - set `grid-template-columns` or `grid-template-rows` on `.item` or `.items > .item`
- **Vertical-rule guard.** In any owned file, no rule for `.item`, `.items > .item`, or the item children may set a border other than `border-top` or `border-bottom`. This covers `border-left`, `border-right`, the `border-inline` family, and the `border` shorthand.
- **No change** to CSS, components, behavior, or specs.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None. This change only adds tests; `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- `frontend/src/styles/tokens.test.ts`: the existing `layoutRules` parser is reused, and the new or extended tests read the three owned files.
- No runtime code, dependency, or build change.
