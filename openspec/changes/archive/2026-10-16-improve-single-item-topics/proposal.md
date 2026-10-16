# Proposal

## Why

On wide windows, digest topic rows leave the right third of the content empty. Issue #25 reports this for single-item topics. Research shows it is the normal case:
- Long items take 6 of the 9 item columns.
- Nearly every real summary counts as long (over 140 characters).
- A long item after another long item starts a new row.

As a result, 14 of 16 rows in a real Chinese digest end 302 px short of the content edge at 1440 px. Since #27, the latest digest is the main screen, so this is the first thing users see.

## What Changes

- **One row per item.** On wide windows, each item in a topic is one row:
  - its source line and linked title on the left (item columns 1–3)
  - its summary on the right (item columns 4–9), ending at the content's right edge
- **The summary measure stays at today's long-item width:** about 580 px at 1440 px, or 39–47 mixed Chinese/Latin characters per line.
- **One width for every item.** The long/short distinction and its 140-character threshold are removed, so all items share one layout. Width still does not depend on position.
- **Unchanged:**
  - the topic column (title and overview in page columns 1–3)
  - the top rule between items, which now spans the item's full width
  - the single-column layout at 900 px and below
  - the Creator updates layout
  - the DOM order of an item: source line, then title, then summary
- **Stacked items at 1100 px and below.** From 901 to 1100 px, the topic column stays, and each item stacks its source line, title, and summary across the item area. This keeps titles from wrapping to 4–5 lines in a narrow heading column.
- **Out of scope:** grouping granularity (fewer, broader topics), the second cause named in #25. It is split out into its own later change.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `user-interface`, "Digest reading layout": the requirement that a long item gets a wider column than a short one is replaced. In its place, each item is a row with its heading beside its summary, and every summary has one width that ends at the content edge on wide windows. The "Long transcript summary" scenario is updated, and a "Single-item topic" scenario is added.

## Impact

- **Frontend only.**
  - `frontend/src/styles/layout.css`: item placement in the topic row, and the 900 px block.
  - `frontend/src/components/DigestArticle.tsx`: no length-based item class.
  - `frontend/scripts/check-style-coverage.py`: the removed classes are still used by the archived prototype.
  - Tests in `frontend/src/pages/DigestView.test.tsx` and `frontend/src/styles/tokens.test.ts`.
- **Both screens.** Home (`/`) and saved digests (`/digests/:id`) change together, because they share `DigestArticle`.
- **No change** to the backend, the API, the stored data, the grouping prompt, the service worker, or Docker packaging.
