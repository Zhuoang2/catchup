# Design

Lean OpenSpec change for issue #54 (the Deep level). The plan below is written for the recommendation of each decision point U1–U4 (end of this document); each decision point also says what the other options would change.

## Context

See `proposal.md` (Why). Facts on main `d75b75b` that shape the approach:

- **The levels today** (`backend/src/catchup/context/depth.py:8-28`). `LINK_DEPTHS = ("off", "shallow", "normal")`. `context_limits(level, settings)` returns `ContextLimits(links_per_item, fetches_per_run, author_replies)`: Off is `(0, 0, False)`; Shallow is `min(3, settings.links_per_item)`; any other value, including a hand-edited unknown one, gets Normal's numbers (`:22-23`). `link_depth_pages(settings)` returns `{"off": 0, "shallow": …, "normal": …}`.
- **The server's numbers.** `links_per_item` (8), `context_fetches_per_run` (60), and `author_replies` (on) come from `CATCHUP_LINKS_PER_ITEM`, `CATCHUP_CONTEXT_FETCHES_PER_RUN`, and `CATCHUP_AUTHOR_REPLIES` (`backend/src/catchup/config.py:78-80`, `:99-101`); `positive_env` refuses 0 and negative values, so twice either number is at least 2.
- **The context pass** (`backend/src/catchup/context/gather.py:109-256`).
  - The budget is `[limits.fetches_per_run]`, shared with robots.txt (`:110-112`); links come from `related_links(…, limits.links_per_item)` (`:128-132`); author replies follow `limits.author_replies` (`:133-134`).
  - The two caps are literals in `gather_item`: the loop stops reading links once `linked_length >= 16_000` (`:172-174`), and each page is cut to `min(3000, 16_000 - linked_length)` characters (`:191`).
  - Because 8 × 3,000 is more than 16,000, Normal stores at most 6 full pages per item; `test_linked_context_stops_at_sixteen_thousand_chars` (`backend/tests/test_context_gather.py:823-839`) asserts at most 6 rows and 16,000 characters. A link after the cap is not requested (`drop_links`).
  - Author replies have their own limits, 10 replies and 4,000 characters (`backend/src/catchup/context/comments.py:20-21`), which no level changes.
- **Storage.** `AppSettings.link_depth` is `String(16)` with `default="normal"` (`backend/src/catchup/models.py:65`), and migration `0010_link_depth` adds it with no check constraint (`backend/src/catchup/migrations/versions/0010_link_depth.py:14-16`). The run reads the stored value once (`backend/src/catchup/digest/runner.py:261`) and passes it as `level=` (`:355`). So `"deep"` needs no migration and no runner change: only the API's list of levels refuses it today.
- **The preferences API** (`backend/src/catchup/api/settings.py:300-337`). The `GET` answer has `link_depth`, the read-only `link_depth_pages`, and `context_fetches_per_run` (`:309-311`). `PUT` refuses a level outside `LINK_DEPTHS` with `AppError("invalid_link_depth", "Choose Off, Shallow, or Normal for linked pages.", 422)` before writing (`:320-321`).
- **Summary size.** All stored context goes into the item's summary request (`backend/src/catchup/llm/prompts.py:63-89`). The item's own text budget is `max(2_000, max_chars - context length)` (`backend/src/catchup/digest/summarize.py:82`), where `max_chars` is `CATCHUP_SINGLE_CALL_CHARS`, or the model's context window minus 6,096, or 60,000 when the window is unknown (`runner.py:440-442`). More context therefore leaves less room for the item's own text: a longer item is summarized in more parts.
- **Settings page** (`frontend/src/pages/Settings.tsx`). The `Preferences` type lists the three levels (`:12-14`); state for the level, the pages, and the run limit (`:67-69`) is set from the `GET` answer (`:136-138`) and the level is sent in the preferences `PUT` (`:384`). The select and its note are at `:480-491`; the note's 3,000 and 4,000 are literals, and the run limit uses `plural(contextFetchesPerRun, 'page request')`.
- **Existing tests that name the three levels.**
  - `backend/tests/test_context_depth.py:9` (`LINK_DEPTHS`), `:21` (a row that uses `"deep"` as the unknown level and expects Normal's numbers), `:35-42` (`link_depth_pages` dicts).
  - `backend/tests/test_settings_api.py:382` (`"deep"` is one of the refused values), `:393-401`, `:403-411`, and the whole answers at `:414-470`.
  - `frontend/src/pages/Settings.test.tsx`: `mockLinkedPages` (`:55-64`), the default preferences mock (`:80-83`), the linked-pages tests (`:93-147`), and the preferences mocks at `:457`, `:535`, and `:625`.
  - `scripts/docker-smoke.sh:86-90` and `:122-126` compare the whole preferences answer.
  - `backend/tests/test_readme_context.py` checks README phrases.
- **#48's research sample** (archive `2026-10-19-add-linked-pages-and-author-replies/research.md:240`, `design.md` D2). Simon Willison's entries have 3 / 8 / 40 links (min / median / max), and every entry ends with a "Tags:" paragraph of same-site tag links, which are excluded. Normal's 8 links already cover the median entry's related links; more links matter for link-heavy posts such as weekly roundups.
- **Prototype** (a `git archive` export of `d75b75b`, session scratchpad `probes54d/proto`). Group 1's run tests, written as in `tasks.md` 1.1, fail as 1.1 says on today's code (4 failed, 4 passed), pass with D1 and D2 applied (8 passed), and mutations G1, G2, and G3 each fail at least the cap test. With D1 and D2 applied, the only other failing backend test is `test_context_limits[unknown]`, whose level `"deep"` becomes a real level (1.1 changes that row).
- **Probe** (`probes54d/probe_extract.py` in the session scratchpad, run with the locked environment). `trafilatura.extract` on the test helper's `html(title, "x" * 10000)` returns 10,000 characters, `"x" * 7000` returns 7,000, and `"word " * 2000` returns 9,999. So test pages longer than 6,000 characters reach the cut intact.

## Goals / Non-Goals

**Goals:**
- One more level that reads more, chosen the same way and read once per run.
- Off, Shallow, and Normal behave exactly as today.
- The Settings text shows Deep's real numbers.

**Non-Goals:**
- Any model call to choose links (U1).
- Following links found on linked pages.
- More author replies at Deep.
- New environment settings, or a migration.
- Changing how context is used in summaries, or the progress formula (D-036).

## Decisions

### D1. Deep's limits (`context/depth.py`)

```python
LINK_DEPTHS = ("off", "shallow", "normal", "deep")
SHALLOW_LINKS = 3
DEEP_FACTOR = 2
PAGE_CHARS, ITEM_CHARS = 3_000, 16_000
DEEP_PAGE_CHARS, DEEP_ITEM_CHARS = 6_000, 32_000

@dataclass(frozen=True)
class ContextLimits:
    links_per_item: int
    fetches_per_run: int
    author_replies: bool
    page_chars: int = PAGE_CHARS
    item_chars: int = ITEM_CHARS
```

| Level | `links_per_item` | `fetches_per_run` | `author_replies` | `page_chars` | `item_chars` |
|---|---|---|---|---|---|
| `off` | 0 | 0 | False | 3,000 | 16,000 |
| `shallow` | `min(3, links)` | `fetches` | `settings.author_replies` | 3,000 | 16,000 |
| `normal` | `links` | `fetches` | `settings.author_replies` | 3,000 | 16,000 |
| `deep` | `2 × links` | `2 × fetches` | `settings.author_replies` | 6,000 | 32,000 |

`links` and `fetches` are `settings.links_per_item` and `settings.context_fetches_per_run`. Any other value still gets Normal's numbers. The new fields have defaults so that other callers need no change, but every expected row of `test_context_limits` names all five fields: a row that relied on the defaults would compare equal under a mutated default (E6). `link_depth_pages(settings)` adds `"deep": 2 × links`.

Alternatives: new environment settings for Deep (rejected: more knobs, and an administrator who lowers Normal would also have to lower Deep); Deep's numbers as fixed constants (rejected: Deep could then read fewer links than Normal on a server that raised `CATCHUP_LINKS_PER_ITEM`).

### D2. The pass reads the caps from the limits (`context/gather.py`)

`gather_item` uses `limits.item_chars` in place of both `16_000` literals (`:172`, `:191`) and `limits.page_chars` in place of `3000` (`:191`):

```python
if linked_length >= limits.item_chars: ...
content = text.strip()[:min(limits.page_chars, limits.item_chars - linked_length)]
```

Nothing else in the pass changes: robots.txt, host spacing, redirects, the four workers, saved replies, and the progress total (which already follows `budget[0]`).

### D3. API (`api/settings.py`)

- `GET` adds the read-only `deep_context_fetches_per_run`: `context_limits("deep", settings).fetches_per_run`. `link_depth_pages` gains `"deep"` through D1. `context_fetches_per_run` keeps its meaning: the limit at Shallow and Normal.
- `PUT` accepts `"deep"` through `LINK_DEPTHS`. The refusal message becomes "Choose Off, Shallow, Normal, or Deep for linked pages." The new field is ignored if sent, like the other read-only fields.

Alternative: replace `context_fetches_per_run` with a per-level dict (rejected: churn in a field added one PR ago, for no behavior gain).

### D4. Settings text (`frontend/src/pages/Settings.tsx`)

```
Linked pages                       <select id="link-depth" aria-describedby="link-depth-note">
  Off — no linked pages or author replies
  Shallow — up to 3 pages per item
  Normal — up to 8 pages per item
  Deep — up to 16 pages per item
Each page read adds time to a run, and up to 3,000 characters to that item's summary request (6,000 at Deep, and up to 4,000 for author replies), which uses more tokens. A run makes at most 60 page requests (120 at Deep), robots.txt files included.
```

The Deep option uses `plural(linkDepthPages.deep, 'page')`; the note's 60 is `plural(contextFetchesPerRun, 'page request')` as today, and 120 is `deepContextFetchesPerRun` as a plain number. 6,000, 3,000, and 4,000 are literals, like 3,000 and 4,000 today, because no setting changes them. The `Preferences` type and the initial state gain `deep` and `deep_context_fetches_per_run` (initial 0, as for the other numbers). The note stays one static text for every level (U4).

### D5. README

The Linked pages paragraph gets one sentence on Deep after the Shallow sentence: "**Deep** reads up to twice `CATCHUP_LINKS_PER_ITEM` links per item, keeps up to 6,000 characters of each page and 32,000 per item, and allows twice `CATCHUP_CONTEXT_FETCHES_PER_RUN` requests per run; author replies are read as at Normal." And after "A run uses the level saved when it starts.": "Deep's larger context leaves less of each summary request for the item's own text, so long items are summarized in more parts; with a small model, prefer Normal or Shallow." In the same paragraph, "Every level keeps the per-run limit." becomes "Shallow and Normal keep the per-run limit.", because Deep doubles it. `test_readme_context.py` checks "**Deep** reads up to twice" and "with a small model, prefer Normal or Shallow".

### D6. Smoke script

Both expected preferences answers in `scripts/docker-smoke.sh` gain `"deep": 16` in `link_depth_pages` and `"deep_context_fetches_per_run": 120`. Droid edits the script but does not run it (Claude runs it at review).

## Decision points for the user

### U1. What Deep is

- **Recommended: A. Deterministic bigger limits** (D1, the option offered as U1 B in #54's first change). Deep reads twice Normal's links, more of each page, and more per item, within twice the per-run limit, before the summaries, with no model call. It is testable offline and closes #54. It helps link-heavy posts (roundups with up to 40 links in the #48 sample) and long linked articles; a typical entry, whose related links Normal already covers, gains mostly the longer page excerpts.
- **B. Model-picked links** (#48's Proposal 2, the sketch in #54's issue text). One extra model call for every item with links, a nondeterministic choice, and fetches inside or before the summarizing stage. D-020 rejected it for #48 for these reasons. It would need a full RePPIT change (research and two proposals), so this plan would stop; #54 would stay open.
- **C. Second-hop links.** Deep also follows related links found on the linked pages. The pass stores only extracted text today (`gather.py:183-198`), so it would need to keep each page's links and new rules for links in whole pages (navigation, footers, ads), which feed entries do not have. Rejected: much more fetching for links whose relevance nothing checks.

### U2. Deep's numbers

- **Recommended: A. Twice Normal's links and caps** (D1): 16 links, 6,000 characters per page, 32,000 per item by default, derived from `CATCHUP_LINKS_PER_ITEM`. Author replies unchanged. The item's summary request can carry up to 16,000 more characters than at Normal.
- **B. More pages, same cut.** 16 links, 3,000 characters per page, 48,000 per item. Reads more pages of link-heavy posts in full excerpt, but not more of any one page, and makes summary requests up to 32,000 characters larger than at Normal. Change in the plan: D1's Deep row and the spec's numbers; the note's "(6,000 at Deep)" goes away; the 6,000 test becomes a 3,000 one at Deep, and the cap test uses 48,000.
- **C. Twice the links only.** 16 links with Normal's 3,000 and 16,000. Rejected: Normal already stops at 6 full pages because of the 16,000 cap, so Deep would read more pages only when earlier ones are short or fail.

### U3. The per-run limit at Deep

- **Recommended: A. Twice `CATCHUP_CONTEXT_FETCHES_PER_RUN`** (120 by default). Deep can read up to twice as many pages per item, so with the same limit a run of many items would spend it on the first items and leave the rest without context. A run can take up to about twice as long in its context pass.
- **B. The same limit as Normal** (60). Deep then reads deeper only for the first items of a large run; small runs are unchanged. Change in the plan: D1's Deep row keeps `fetches`; no `deep_context_fetches_per_run` field; the note keeps today's second sentence; the "Deep doubles the per-run limit" scenario and its test go away.

### U4. The Settings text

- **Recommended: A. One note for every level, naming Deep's numbers in parentheses** (D4). The user can compare the levels before choosing, and the text does not move while the select changes.
- **B. A note that follows the selected level.** At Deep the note reads "… up to 6,000 characters … A run makes at most 120 page requests …", at the other levels as today. Shorter, but the user sees Deep's cost only after choosing it, and the description changes under a screen reader's focus. Change in the plan: D4's note becomes two texts; the default-choice test checks today's note, and a new test checks the Deep note after `fireEvent.change`.
- **C. Put Deep's per-page number in its label**: "Deep — up to 16 pages per item, 6,000 characters each". Rejected: the other labels name only pages, and the note already carries the character limits.

## Risks / Trade-offs

- **[Larger summary requests]** At Deep an item's summary request can carry up to 32,000 characters of linked context and 4,000 of author replies. With the 60,000 default budget (model window unknown), an item with more than 28,000 characters of its own text is split into parts, which adds model calls. On a small local model with `CATCHUP_SINGLE_CALL_CHARS`, Normal's 16,000 already compete with the item's text; Deep doubles that. → The README says to prefer Normal or Shallow with a small model (D5). Token cost is not measured offline; the run shows token totals, so the user can compare a run at Normal and one at Deep after the merge.
- **[Longer runs]** Up to twice the context requests, each subject to the 1-second host spacing and the fetcher's timeouts. → The note says each page adds time, and names Deep's request limit.
- **[Downgrade with Deep saved]** An older image reads a stored `"deep"` as Normal in runs (`depth.py:22`), but its Settings page cannot show Deep and its API refuses `"deep"` on Save, so Save fails with `invalid_link_depth` until the user chooses another level. → Recorded; there is no migration to undo.
- **[Shared files with #8]** #8 (`add-item-bookmarks-and-feedback`) adds migration `0012` and may edit `api/`, `models.py`, and `README.md`. → This change edits only `context/`, the preferences part of `api/settings.py`, the Linked pages field of `Settings.tsx`, and one README paragraph; log files conflict as usual (keep both sides).
- **[Requirements this change modifies]** `content-collection` "Choose how many linked pages a run reads" and "Gather related context for website items", and `user-interface` "Choose linked pages in Settings", all three added or changed by #54's first change. → If another change also modifies one of them before this one archives, the second rebases its delta on the merged text.
- **[Mutation equivalence]** `DEEP_FACTOR` applied to `links` and `fetches` with the default numbers cannot be told apart from fixed 16 and 120 by the default rows. → The `deep_server` row (5 links, 40 requests) and the API's server-number test use other numbers.

## Migration Plan

- No schema change; `"deep"` fits the existing column.
- Rollback: an older image treats a stored `"deep"` as Normal in runs; see Risks for its Settings page.

## Testing

Test-first (D-016). Seams:
- `context_limits` and `link_depth_pages` in `catchup.context.depth`, directly, with parametrized rows over `Settings` objects built with `dataclasses.replace` (`backend/tests/test_context_depth.py`);
- `setup`, `html`, `set_level`, `public_dns`, `stub_collection`, and `execute` with `respx.mock(assert_all_mocked=True, …)` (`backend/tests/test_context_gather.py`); the level is set on the `AppSettings` row with `set_level`, and server numbers by replacing `environment.app.state.settings`;
- `api` and `client.app.state.settings` (`backend/tests/test_settings_api.py`);
- the README text (`backend/tests/test_readme_context.py`);
- `Settings` rendered with `mockLinkedPages`, `fireEvent.change` on the select, `preferencePuts()`, `toHaveAccessibleDescription`, and `expectAccessible` (`frontend/src/pages/Settings.test.tsx`).

Named mutations, each applied alone and restored:

| Id | Mutation | Must fail |
|---|---|---|
| E1 | Deep's `links_per_item` is `settings.links_per_item` | `test_context_limits[deep]`, `[deep_server]`; `test_deep_reads_twice_normals_links` |
| E2 | Deep's `fetches_per_run` is `settings.context_fetches_per_run` | `test_context_limits[deep]`, `[deep_server]`; `test_deep_doubles_the_run_limit[deep]` |
| E3 | Deep's `page_chars` is 3,000 | `test_context_limits[deep]`; `test_page_cut_follows_the_level[deep]` |
| E4 | Deep's `item_chars` is 16,000 | `test_context_limits[deep]`; `test_deep_caps_an_items_linked_context` |
| E5 | Deep's `author_replies` is `False` | `test_context_limits[deep]`; `test_deep_reads_author_replies` |
| E6 | `ContextLimits.page_chars` defaults to 6,000 | `test_context_limits[normal]` and the other non-Deep rows; `test_page_cut_follows_the_level[normal]`, `[shallow]` |
| E7 | `LINK_DEPTHS` without `"deep"` | `test_link_depths`; `test_link_depth_save_and_read` |
| E8 | `link_depth_pages` returns a fixed 16 for Deep | `test_link_depth_pages[5-expected1]`, `[2-expected2]`, `[1-expected3]`; `test_preferences_report_the_server_numbers` |
| G1 | `gather_item` keeps the literal `3000` in the cut | `test_page_cut_follows_the_level[deep]`; `test_deep_caps_an_items_linked_context` |
| G2 | `gather_item` keeps the literal `16_000` in the loop check (`:172`) | `test_deep_caps_an_items_linked_context` |
| G3 | `gather_item` keeps the literal `16_000` in the cut (`:191`) | `test_deep_caps_an_items_linked_context` |
| A1 | `deep_context_fetches_per_run` is `settings.context_fetches_per_run` | `test_preferences_report_the_server_numbers` |
| A2 | the refusal message names three levels | every case of `test_invalid_link_depth` (it now checks the message) |
| F1 | the Deep option is missing | `shows the linked-pages choice with its numbers and cost note` |
| F2 | the Deep label uses a fixed 16 | `names the server's own numbers` |
| F3 | the note uses a fixed 120 | `names the server's own numbers` |
| F4 | the note's Deep page cut reads 3,000 | `shows the linked-pages choice with its numbers and cost note` |
| R1 | the README's Deep sentence is removed | `test_readme_documents_public_context_limits_and_robots` |

## Rollout

- Review: Claude Code runs `scripts/docker-smoke.sh` and a live check on a scratch container (fresh volume, a port other than 8800, a stub model, and a local stub site): Settings at 1280 px and 375 px with the accessibility tree read and Deep saved; one run at Deep over a stub item with 17 linked pages and one long page, comparing the requests the stub site receives and the stored context lengths with Normal.
- After the merge: the user can run one digest at Normal and one at Deep on their own instance with their own model and compare the token totals the run shows.
