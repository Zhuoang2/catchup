# Proposal

## Why

On 2026-10-02 the user asked for a way to see only the N most important items of a digest (requirements change of that date, #9). Today a digest shows every item it covers: after a long gap that can be 100 or more summaries, and nothing tells a reader which ones matter most. No ranking exists: a summary call returns only the summary, the "Also read" references, and image choices (`backend/src/catchup/digest/summarize.py:101-127`).

## What Changes

This describes the recommended option of each decision point U1–U7 in `design.md`.

- **An importance rating from each summary call.** The call that writes an item's summary also returns `importance`, a whole number from 1 to 5, on a fixed scale written in the prompt. No model call is added. A missing or invalid rating leaves the item unrated and keeps its summary.
  - The rating is stored with the item's summary and reused with it, so a run that retries a failed run's items keeps their ratings.
  - A saved digest records each topic item's rating. The digest answers give it as `importance` (1–5, or `null`).
  - Ratings change nothing in a run: which items it includes, how they are grouped, and their order stay as they are.
- **"Items to show" in Settings → Digest**: All items (the default, today's behavior), or the 5, 10, 20, or 30 most important. It is saved by Save with the other Digest settings. The preferences API gains `top_items` (0 for All).
- **Limited reading.** When the choice is a number, and a digest has more items in its topics than that and at least one rated item, the main screen and a saved digest opened from History show only that many topic items:
  - the highest-rated ones; an unrated item with a summary ranks as 3, and an item whose summary is unavailable ranks last; equal ranks keep the reading order;
  - in their topics and in the digest's order; topics left with no shown item are left out, also from the index;
  - Creator updates are always shown, and do not count;
  - a line under the headline, "Showing the 10 most important of the 37 items in topics.", with a button "Show all 37" that shows every item, and then "Show the 10 most important".
  - Each opening of a digest starts limited. Digests saved before ratings, the Bookmarks screen, and any digest when the preferences cannot be read are shown in full.
- **Focus.** When a run's new digest replaces the shown one while that button has focus, focus moves to Generate, as it does for an item's controls.
- **Data.** Migration `0013_item_importance` adds `items.importance`, `digest_items.importance`, and `app_settings.top_items`.
- **README.** The intro names the choice.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `digest-generation`: new requirement "Rate each item's importance".
- `digest-history`: new requirement "Saved digests keep each item's importance". "Reopen a saved digest" is modified: a digest that "Items to show" limits first shows only its most important topic items, and its scenario "Open an older digest" is read with All items.
- `user-interface`: new requirements "Choose how many items a digest shows" and "Show only the most important items"; "Keyboard and screen-reader support" is modified so that focus also moves to Generate when it is on the new button of a replaced digest.

## Impact

- **Backend.**
  - `backend/src/catchup/llm/prompts.py`: the rating rule and the example answers of `summary_messages` and `long_transcript_messages`.
  - `backend/src/catchup/digest/summarize.py`: `SummaryInput` and `SummaryResult` gain `importance`; the answer's rating is validated.
  - `backend/src/catchup/digest/runner.py`: the rating is stored on the item and in the digest snapshot.
  - `backend/src/catchup/models.py` and the new migration `backend/src/catchup/migrations/versions/0013_item_importance.py`.
  - `backend/src/catchup/api/digests.py` (`importance` in each topic item) and `backend/src/catchup/api/settings.py` (`top_items`).
- **Frontend.**
  - A new module `frontend/src/components/topItems.ts`, with its tests.
  - `frontend/src/components/DigestArticle.tsx`, `frontend/src/pages/Home.tsx`, `frontend/src/pages/DigestView.tsx`, `frontend/src/pages/Settings.tsx`, and `frontend/src/styles/components.css`.
- **Tests changed.**
  - `backend/tests/test_digest_stages.py`: the two tests that pin the summary prompts' exact text.
  - `backend/tests/test_db.py`: the head revision, the migration list, and the 0012 migration test's target revision.
  - `backend/tests/test_digest_history.py`: the pinned item answer.
  - `backend/tests/test_settings_api.py`: the three tests that pin the whole preferences answer.
  - `frontend/src/pages/Home.test.tsx`: `mockPage` can answer the preferences request.
  - `frontend/src/pages/Settings.test.tsx`: `mockLinkedPages`'s default answer gains `top_items: 0`.
- **Other.** `scripts/docker-smoke.sh`: both expected preferences answers gain `"top_items": 0`. `README.md`.
- **API.** New fields only: `importance` in digest and bookmark items, `top_items` in the preferences. Clients that ignore them keep working.
- **Cost.** A few output tokens per summary call for the rating. No added call, and no new run stage, so the progress formula (D-036) is unchanged.
- No new dependency. **Not changed:** grouping, topic order, collection, the extension, the Bookmarks screen, History's list, and the browser extension's API.
