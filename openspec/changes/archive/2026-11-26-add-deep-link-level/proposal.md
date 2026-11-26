# Proposal

## Why

PR #103 (D-042) added the Settings choice "Linked pages" with Off, Shallow, and Normal, and left #54 open for the level the user asked for on 2026-10-19 (translated: "later we can give users the option to choose deep or shallow crawling"). Today no setting reads more than Normal: a user who wants fuller context for link-heavy posts, or for long linked articles, can only raise `CATCHUP_LINKS_PER_ITEM` and `CATCHUP_CONTEXT_FETCHES_PER_RUN` on the server and restart it, and even then each page is still cut to 3,000 characters and each item to 16,000. This change adds the Deep level and closes #54.

## What Changes

This describes the recommended option of each decision point U1–U4 in `design.md`.

- **A fourth level, Deep**, in the "Linked pages" choice (Settings → Digest), after Normal. It is deterministic and gathered before the summaries, like the other levels; no model call is added. At Deep a run:
  - reads up to twice `CATCHUP_LINKS_PER_ITEM` related links per item (16 by default);
  - keeps up to 6,000 characters of each linked page (3,000 at the other levels) and up to 32,000 characters of linked context per item (16,000 at the other levels);
  - makes up to twice `CATCHUP_CONTEXT_FETCHES_PER_RUN` context requests (120 by default), robots.txt included;
  - reads author replies as at Normal (at most 10 replies and 4,000 characters, and `CATCHUP_AUTHOR_REPLIES` still turns them off).
- **Off, Shallow, and Normal do not change.** Normal stays the default. The environment settings keep their meaning: they set Normal, and Deep is twice Normal.
- **No migration.** `app_settings.link_depth` is a 16-character string with no constraint (`0010_link_depth`); only the API's list of levels changes.
- **The preferences API** accepts `link_depth: "deep"`. The `GET` answer's read-only `link_depth_pages` gains `"deep"`, and a new read-only `deep_context_fetches_per_run` gives Deep's per-run limit. The refusal for an unknown level names the four levels.
- **Settings text.** The option reads "Deep — up to 16 pages per item", with the server's number. The note names Deep's numbers: "Each page read adds time to a run, and up to 3,000 characters to that item's summary request (6,000 at Deep, and up to 4,000 for author replies), which uses more tokens. A run makes at most 60 page requests (120 at Deep), robots.txt files included."
- **`scripts/docker-smoke.sh`** expects the two new answer fields.
- README: what Deep reads, and that its larger context leaves less of each summary call for the item's own text.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `content-collection`: "Choose how many linked pages a run reads" gains Deep and its numbers; "Gather related context for website items" says that the per-page cut, the per-item cap, and the per-run limit are larger at Deep.
- `user-interface`: "Choose linked pages in Settings" offers Deep, and its note names Deep's numbers.

## Impact

- Code:
  - `backend/src/catchup/context/depth.py` (Deep in `LINK_DEPTHS`, `context_limits`, and `link_depth_pages`; `ContextLimits` gains the per-page and per-item caps);
  - `backend/src/catchup/context/gather.py` (the two caps come from the level's limits instead of constants);
  - `backend/src/catchup/api/settings.py` (preferences answer and refusal message);
  - `frontend/src/pages/Settings.tsx`.
- Tests: `backend/tests/test_context_depth.py`, `test_context_gather.py`, `test_settings_api.py`, `test_readme_context.py`; `frontend/src/pages/Settings.test.tsx`; `scripts/docker-smoke.sh`.
- Docs: `README.md`, decision log (D-044), requirements-changes table, a test report, the AI usage log.
- No migration, no new dependency, no new environment setting.
- Shared with the change planned at the same time: #8 (`add-item-bookmarks-and-feedback`) adds migration `0012` and may edit `README.md` and `api/`; this change edits only the preferences section of `api/settings.py` and the Linked pages paragraph of the README. Log files conflict as usual.
- Out of scope: model-picked links (#48's Proposal 2), following links found on linked pages, more author replies, per-level environment settings, and any change to how context is used in summaries or to the progress formula (D-036).
