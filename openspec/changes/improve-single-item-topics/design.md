# Design

Chosen by the user on 2026-10-16: Proposal 1 of the two proposals, the item title beside its summary, one row per item. Option G (fewer, broader topics through the grouping prompt) is split out into its own later change. The research behind this design is in `research.md`.

## Context

See `proposal.md` for the motivation. The current state that shapes the approach (details and measurements in `research.md`):

- **The topic row.**
  - Each topic is a 12-column subgrid, with the title and overview in columns 1–3 (`frontend/src/styles/layout.css:21-22`).
  - Its items sit in a 9-column grid over columns 4–12 (`layout.css:23`).
- **Item spans.**
  - A long item spans 6 item columns and a short item spans 3 (`layout.css:25-26`).
  - A single item, and every long item after a long item, restart at item column 1 (`layout.css:27`, `:29`).
  - Short items next to each other are separated by a vertical rule (`layout.css:28`).
- **Item markup.** `DigestArticle` marks an item long when its summary is over 140 characters or has a "- " line (`frontend/src/components/DigestArticle.tsx:67-68`). Each item is an `article.item` with the children `p.item-meta`, then `h3.item-title`, then `div.summary` or `p.summary-unavailable` (`DigestArticle.tsx:68-78`).
  - `.item` is a grid with a 0.45rem gap (`frontend/src/styles/components.css:112`).
- **Measured at 1440 px.**
  - The item grid spans 882 px. A long item spans 580 px, which holds 39–47 mixed characters per line, about 35 CJK characters, and about 75 Latin characters.
  - The heading column (item columns 1–3) would be 290 px wide.
- **Narrow layout.** At 900 px and below, everything is one column (`layout.css:59-68`).
- **Style audit.** `frontend/scripts/check-style-coverage.py` compares the archived C7 prototype's selectors with the app's CSS. The prototype still uses `.item-long` and `.item-short` (`openspec/changes/archive/2026-10-14-redesign-ui-ux/prototypes/directions/c7.css:26`).

## Goals / Non-Goals

**Goals:**
- Every item row on wide windows ends at the content's right edge, for single-item topics and for any number of items.
- The summary keeps today's long-item measure.
- The item's DOM, headings, links, and `lang` attributes are unchanged.

**Non-Goals:**
- Grouping granularity and the grouping prompt (Option G, a later change).
- The topic column's width, the Creator updates layout, and the narrow layout's appearance.
- Any backend or API change.

## Decisions

### D1. The item is a subgrid row of the item grid
- **Placement:**
  - `.items > .item` spans `1 / -1` of the 9-column item grid, as a subgrid, so its columns line up with the page grid.
  - `.item-meta` and `.item-title` take item columns `1 / span 3` (page columns 4–6), in rows 1 and 2.
  - `.summary` and `.summary-unavailable` take `4 / -1` (page columns 7–12) and span all of the item's rows.
- **The heading stays together.** The item's rows are `auto auto 1fr`, so a summary taller than the heading gives its extra height to the last row. The source line and title therefore stay together at the top of the row instead of spreading apart.
- **No markup change.** The placement is done in CSS only; the DOM order stays source line → title → summary.
- **Alternative:** wrapping the source line and title in a new `div.item-head`. Rejected: it changes the shared markup and adds an element, while the subgrid placement needs none.

### D2. One item layout; no length classes
- `DigestArticle` stops computing `wide` and renders `article.item` without `item-long` or `item-short` (`DigestArticle.tsx:67-68`).
- **CSS removed:**
  - the `.item-long`, `.item-short`, and `.item:only-child` span rules (`layout.css:25-27`)
  - the long-after-long restart (`layout.css:29`)
  - the vertical rule between items (`layout.css:28`)
- **Alternative:** keeping the classes for possible later use. Rejected: they would be dead CSS, and the 140-character rule classified nearly every real summary as long anyway.

### D3. Rules and spacing
- **Between items:** a top rule spans the whole item (page columns 4–12). Use the existing narrow-layout pattern: `border-top: 1px solid var(--border)` with `padding-top: 1rem`, as at `layout.css:68`.
- **No vertical rule** between the heading and the summary (the user's decision on 2026-10-16).
- **The topic column** stays at 3 columns (the same decision).
- **Row gap.** The row gap between items in a topic stays as today (`layout.css:23`).

### D4. Narrow layout (900 px and below)
- **Item grid:** the item grid is already one column (`layout.css:66`).
- **The item itself:**
  - It becomes one column (`grid-template-columns: minmax(0, 1fr)`).
  - Its children reset to `grid-column: 1 / -1; grid-row: auto`, so the source line, title, and summary stack in DOM order, as today.
- **Rules:** the existing top rule between items (`layout.css:67-68`) stays.

### D5. Style audit
- `.item-long` and `.item-short` go into `PROTOTYPE_ONLY` in `frontend/scripts/check-style-coverage.py`, each with a reason, the same way `.hero-last` was handled.
- `frontend/scripts/test_check_style_coverage.py` asserts the new entries.

### D6. Alternative considered: long items across the full width, with two text columns (Proposal 2)
Rejected because:
- Two-column body text splits 2–4 sentence summaries into short columns, and it breaks key-point lists across columns.
- A short item after a long one still leaves two thirds of its row empty.
- The 140-character rule would stay.

The issue's own suggestion, a 4 : 8 split for single-item topics, was also rejected:
- The 8-column item would be about 781 px wide, or about 47 CJK characters per line.
- It does not fix long-after-long rows.

## Risks / Trade-offs

- **[Narrow heading column]** Just above 900 px, the heading column is about 190 px wide (216 px at 1000 px), so titles wrap more. → The live checks at 901 and 1000 px confirm that titles stay readable, and the 900 px breakpoint is unchanged.
- **[Short items take a full row]** A one-line summary now has its own row, where before it shared one with a long item. → Short items are rare in real digests: 1 of 14 and 1 of 7 summaries. Their row is shorter, since the title sits beside the summary.
- **[The heading spreads apart]** Without explicit rows, a tall summary would stretch the meta and title rows. → D1's `auto auto 1fr` rows, a CSS assertion, and a live check that the title starts right below the source line.
- **[It looks like a table]** Three narrow-to-wide bands (topic, heading, summary) read more like a table than a page. → The rules stay horizontal only, and the topic's 3 px rule still opens each section.

## Migration Plan

- Frontend only, with no data or API change. Home and saved digests change together, because both render `DigestArticle`.
- Rollback is a revert.

## Testing

- **Unit (DOM):** in `frontend/src/pages/DigestView.test.tsx`, every item of any length, including key points and "Summary unavailable":
  - is an `article` with class `item` only
  - has no `item-long` or `item-short` class
  - keeps the DOM order source line → title → summary
- **CSS (`frontend/src/styles/tokens.test.ts`):**
  - the item subgrid and its row template
  - the heading and summary placements
  - the absence of the removed rules
  - the narrow-layout reset
- **The Home/History comparison test** (`frontend/src/pages/Home.test.tsx`) passes unchanged.
- **Audits:** the style audit and `npm run build`.
- **Review step (D-016):** `/code-review`, the spec subagent, and live checks.
  - The live checks run on a review build that shows the real Chinese digests No. 3 and No. 4 (read-only from the e2e container's data) and an English stub digest.
  - Widths: 1440, 1000, 901, 900, and 420 px.
  - What to check:
    - At 1440 px, every summary ends at x = 1312.
    - At 1440 px, no summary line holds more than 40 Chinese or 80 Latin characters.
    - The title starts right below the source line.
    - At 900 px and below, items stack.
    - There is no overflow at 420 px.
