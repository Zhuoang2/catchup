# Design

Lean OpenSpec change for issue #54. On 2026-11-25 the user approved the plan with the recommendation for U1–U3: no Deep level in this change (#54 stays open for it), the environment settings set Normal, and Off makes no context request. `tasks.md` is written for these. Each decision point below also says what the other options would have changed.

## Context

See `proposal.md` (Why). Facts on main `145811f` that shape the approach:

- **The numbers today.** `Settings` holds `links_per_item` (8), `context_fetches_per_run` (60), and `author_replies` (on) (`backend/src/catchup/config.py:78-80`), read from `CATCHUP_LINKS_PER_ITEM`, `CATCHUP_CONTEXT_FETCHES_PER_RUN`, and `CATCHUP_AUTHOR_REPLIES` (`config.py:99-101`). `positive_env` refuses 0 and negative values (`config.py:12-22`), so neither number can be 0 today.
- **The context pass** (`backend/src/catchup/context/gather.py:108-254`).
  - It plans every pending item of a `feed`, `podcast`, `capture`, or `x` source whose `context_status` is NULL (`gather.py:111-117`); podcast items only when their transcript is text (`:122-123`).
  - Links: `related_links(item.link, site_url, entry_links, settings.links_per_item)` (`:126-130`). Author replies: only for sources other than `capture` and `x`, when `settings.author_replies` is on and the feed reported comments (`:131-132`). Replies saved with a capture or kept from an X thread (`item.captured_replies`) need no request (`:133`, `:228-234`).
  - One budget list `[settings.context_fetches_per_run]` is shared by every fetch and by robots.txt (`:109-110`, `robots.py:45-46`).
  - An item that starts while the budget is 0 and has no saved replies is dropped from the progress and keeps `context_status` NULL (`:157-159`). An item that stored nothing becomes `none`, otherwise `gathered` (`:244`).
  - The caps are constants: 3,000 characters per page (`:189`) and 16,000 per item (`:170`, `:189`).
- **`related_links` with a limit of 0 returns one link.** It appends a kept link before it checks the limit (`backend/src/catchup/context/links.py:49-51`). Probe (`probes54/probe_limit0.py`, run with the locked environment): limits 0, 1, 3, 8 over four kept links return 1, 1, 3, and 4 links.
- **Who reads `context_status`.** Only `gather.py` (`:114` selects NULL, `:244` writes it) and `api/extension.py:157` (a re-saved capture resets it to NULL). Delivered items are never planned again, whatever their status.
- **The run** reads the model configuration and the Digest settings once, before any source is checked (`backend/src/catchup/digest/runner.py:255-262`), then calls `gather_context(factory, run_id, app.state.settings, spacer)` after the caption pass (`runner.py:353`). `test_stage_durations_are_saved_for_each_stage` wraps `gather_context` with `*args, **kwargs` (`backend/tests/test_digest_runner.py:154-163`), so a new keyword argument keeps it working.
- **Progress** (D-036). The total is `done + in progress + saved replies left + reachable_reads(remaining URLs, verdicts, units left)` (`gather.py:60-69`). With no URL and no budget, it is the number of saved replies. The main screen shows "Linked pages read" only while `context_total > 0` (`frontend/src/pages/Home.tsx:70-73`).
- **Digest settings.** `AppSettings` has `digest_language`, `youtube_captions`, `youtube_skip_shorts`, and `show_images` (`backend/src/catchup/models.py:59-67`); `show_images` came with migration `0005_item_images`. The migration head is `0009_model_provider`, and `backend/tests/test_db.py:127`, `:145`, `:314`, `:354`, and `:495` name it.
- **The preferences API** (`backend/src/catchup/api/settings.py`). `PreferenceInput` has four optional fields (`:41-45`). `read_preferences` returns the four values, with defaults when no row exists (`:291-299`). `save_preferences` validates the language with `AppError("invalid_language", …, 422)`, writes the given fields, and returns `read_preferences(session)` (`:302-321`). Three tests compare whole answers (`backend/tests/test_settings_api.py:295-337`).
- **Settings page** (`frontend/src/pages/Settings.tsx`). The Digest group (`:422-442`) has the language select with a hint linked by `aria-describedby`, and the "Show images from source sites" switch with its note. Save sends the model settings, then all Digest and YouTube preferences in one `PUT` (`:334-352`). The page loads preferences once (`:104-123`). The test file's default mock answers preferences without `show_images` (`frontend/src/pages/Settings.test.tsx:61-63`), and one test mocks its own answer (`:378-381`). The frontend and the API ship in one image (D-006).
- **Summaries.** Context is subtracted from a split item's text budget, with a floor of 2,000 characters (`backend/src/catchup/digest/summarize.py:82`), so less context leaves more room for the item's own text.
- **#48's research and decisions.** The default of 8 links covers nearly every related link in the research sample: Simon Willison's median entry has 8 links, about half of them tags (archive `2026-10-19-add-linked-pages-and-author-replies/design.md` D2). Model-picked links were rejected for an extra call per item, fetches inside the summarizing stage, a nondeterministic selection, and re-fetching after a failed run (D9; D-020). The linked pages' own links are not kept: the pass stores only the extracted text (`gather.py:183-196`).

## Goals / Non-Goals

**Goals:**
- One stored choice that the run reads once, with Normal exactly as today.
- Off sends no context request at all.
- The Settings text shows the real numbers and the cost.

**Non-Goals:**
- A Deep level (U1).
- Different per-run limits per level, or new caps.
- Removing or renaming the environment settings.
- Re-gathering items that already have context when the level changes.

## Decisions

### D1. The levels (`backend/src/catchup/context/depth.py`)

A new module holds the levels and one pure function:

```python
LINK_DEPTHS = ("off", "shallow", "normal")
SHALLOW_LINKS = 3

@dataclass(frozen=True)
class ContextLimits:
    links_per_item: int
    fetches_per_run: int
    author_replies: bool

def context_limits(level: str, settings: Settings) -> ContextLimits: ...
def link_depth_pages(settings: Settings) -> dict[str, int]: ...
```

| Level | `links_per_item` | `fetches_per_run` | `author_replies` |
|---|---|---|---|
| `off` | 0 | 0 | False |
| `shallow` | `min(3, settings.links_per_item)` | `settings.context_fetches_per_run` | `settings.author_replies` |
| `normal` | `settings.links_per_item` | `settings.context_fetches_per_run` | `settings.author_replies` |

Any other value is treated as `normal`: the API never stores one (D6), so this only guards a hand-edited database. `link_depth_pages(settings)` returns `{"off": 0, "shallow": min(3, links), "normal": links}` for the API and the labels.

### D2. Off is the existing "limit spent" path

`gather_context(factory, run_id, settings, spacer, level="normal")` computes `limits = context_limits(level, settings)` and uses `limits.fetches_per_run` for the budget, `limits.links_per_item` for `related_links`, and `limits.author_replies` in place of `settings.author_replies`. Nothing else in the pass changes. At Off:
- the budget is 0, so every item without saved replies is dropped at `gather.py:157-159` and keeps `context_status` NULL. No request is made, robots.txt included;
- an item with saved replies plans no link and no comment read, stores its replies as `A1`, and becomes `gathered`, as the X requirement already does when the limit is spent;
- the total is the number of saved replies, so with none the main screen shows no linked-page line.

`related_links` also returns `[]` for a limit of 0 or less, so that no caller can get the one-link result of the probe.

Leaving items NULL, not `none`, is what lets "Item left by Off is read later" hold: a run at Off that fails, or an item that stays pending for any reason, is gathered by the next run at the level that run uses. A delivered item is never planned again, so NULL on it changes nothing.

Alternatives: skipping the context pass at Off (rejected: saved replies would be lost, and the pass would need a second code path); marking Off items `none` (rejected: they would never get context, even when the user switches back before they are delivered).

### D3. The run reads the level once

`run_digest` reads `link_depth` from the same `AppSettings` row as the language (`runner.py:259-262`), defaulting to `"normal"` when no row exists, and passes `level=link_depth` to `gather_context` (`runner.py:353`). A level saved during the run applies to the next run. Alternative: read the row again when the context pass starts (rejected: the run already fixes its settings at the start, and the user cannot see when the pass starts).

### D4. Author replies follow the level (U3)

At Shallow and Normal, author replies are read as today, and `CATCHUP_AUTHOR_REPLIES` still turns them off for the instance. At Off, no post page or comment feed is requested. Replies saved with a capture or kept from an X thread are kept at every level, because they need no request.

### D5. The environment settings set Normal (U2)

`CATCHUP_LINKS_PER_ITEM` and `CATCHUP_CONTEXT_FETCHES_PER_RUN` keep their meaning and defaults: they are Normal's numbers, and Shallow never reads more than Normal. An instance that saved no choice runs exactly as before. The README says so.

### D6. Storage and API

- **Migration `0010_link_depth`** (`down_revision = "0009_model_provider"`): `app_settings.link_depth`, `String(16)`, not null, `server_default="normal"`. The downgrade drops the column with `recreate="never"`, as `0009` does. `AppSettings.link_depth` gets `default="normal", server_default="normal"`.
- **`GET /api/settings/preferences`** adds `link_depth` (`"normal"` when no row exists), and the read-only `link_depth_pages` (`link_depth_pages(request.app.state.settings)`) and `context_fetches_per_run`. `read_preferences` gains a `request: Request` parameter; `save_preferences` passes it on.
- **`PUT`** accepts an optional `link_depth`. A value outside `LINK_DEPTHS` is refused before anything is written, with `AppError("invalid_link_depth", "Choose Off, Shallow, or Normal for linked pages.", 422)`. The read-only fields are ignored if sent, as Pydantic ignores unknown fields today.

### D7. Settings text

In the Digest group, after the language field and before the images switch:

```
Linked pages                       <select id="link-depth" aria-describedby="link-depth-note">
  Off — no linked pages or author replies
  Shallow — up to 3 pages per item
  Normal — up to 8 pages per item
Each page read adds time to a run, and up to 3,000 characters to that item's summary request (up to 4,000 for author replies), which uses more tokens. A run makes at most 60 page requests, robots.txt files included.
```

The numbers come from `link_depth_pages` and `context_fetches_per_run`, through `plural` from `components/format.ts` ("up to 1 page per item"). The 3,000 is the per-page cut (`gather.py:189`), which no setting changes; the author replies read from a post page have their own cut of 4,000 (`comments.py:21`). The run's limit is the budget that robots.txt, post pages, and comment feeds share with linked pages, so the note counts page requests, not pages. The select's value is the stored level, and it is sent in the existing preferences `PUT`. The page reads the new fields directly, without fallbacks, because the frontend and the API ship together (D-006); the test mocks that answer preferences get the new fields.

Alternatives: a radio group (rejected: the Digest group already uses a select for a choice among fixed values, and three options fit in one); numbers written into the page (rejected: wrong when the server's settings differ).

### D8. Progress

No change to the formula (D-036). Shallow plans at most 3 links per item, so its total is smaller; Off's total is the number of saved replies (D2).

## Decision points for the user

### U1. A Deep level

- **Recommended: A. Off, Shallow, and Normal now; Deep later, on its own.** The PR says "Part of #54", and #54 stays open for Deep. When the user asked for the choice (2026-10-19), Claude's proposal was 3 links and the user asked for more: Shallow is that proposal, and Normal is what the user chose. The step beyond Normal that #54 sketches is following links that the linked pages point to, chosen by the model. That needs what this change cannot verify offline: keeping the linked pages' own links (not stored today), rules for links in whole pages rather than in a feed entry, a new prompt and model call per item, and its cost. All of D-020's reasons against Proposal 2 apply. It is a design of its own, with research.
- **B. A Deep level without a model, in this change.** Deep reads up to twice Normal's links (16 by default), the first 6,000 characters of each page, up to 32,000 characters per item, and twice the per-run limit (120 by default). It is deterministic and stored before the summary, like the other levels. It reads more of long linked articles and helps items with many links. Typical blog items gain little from more links: the #48 sample's median entry has 8 links, about half of them tags, so Normal already reads all of its other links. A run can take about twice as long, and an item's summary request can carry 16,000 more characters. Change in the plan: a fourth row in `context_limits` and `link_depth_pages`; the two caps move into `ContextLimits` (`gather.py:170`, `:189`); the `content-collection` delta's MODIFIED requirement says "3,000 characters (6,000 at Deep)" and "16,000 characters (32,000 at Deep)"; a Deep scenario and option label ("Deep — up to 16 pages per item, more of each page"); the PUT message names four levels; tests for each new number, with mutations; the PR says "Closes #54". About one more task group.
- **C. #48's model-picked links, in this change.** One extra model call for each item with links (all 30 of Simon Willison's sampled entries), then fetches of the chosen links. Rejected for this change: it is a full RePPIT change of its own (research, two proposals), its selection is nondeterministic, and its quality can only be judged with the user's own model key.

### U2. What the environment settings mean

- **Recommended: they set Normal** (D5). Nothing changes for an instance that saved no choice, and an administrator can still lower or raise Normal.
- **Upper limits for every level, with defaults raised to the largest level.** Only meaningful with a Deep level (U1 B): an instance that sets `CATCHUP_LINKS_PER_ITEM=8` would then cap Deep at 8. Change in the plan with U1 B: Deep's numbers become the env values, and the defaults change to 16 and 120 (**BREAKING** for instances that rely on the defaults).
- **Remove them.** Rejected: breaks instances that set them, and loses the knob for small machines.

### U3. Author replies at Off

- **Recommended: Off makes no context request at all** (D4). "Off" then means CatchUp reads nothing beyond the feed and the item's own article, which is the fastest and cheapest run, and matches the progress line, which already counts post pages and comment feeds as linked pages. The label says "no linked pages or author replies".
- **Off covers linked pages only.** Post pages and comment feeds are still read at Off, unless `CATCHUP_AUTHOR_REPLIES` is off. Change in the plan: `context_limits("off")` keeps `settings.author_replies` and a budget, and Off items without comments become `none`; the Off label becomes "Off — no linked pages"; the "Off makes no request" scenario becomes "no linked page is requested, and the post page is read for author replies"; mutation L2 is dropped.

## Risks / Trade-offs

- **[Migration number clash]** #4 (`add-reasoning-setting`), planned at the same time, may also add migration `0010`. → Whichever change merges second renumbers its migration to `0011`, sets `down_revision` to the first one's revision, and updates the head assertions in `backend/tests/test_db.py`, as D-037 noted for #12 and #40.
- **[Shared files]** #4 may edit `api/settings.py`, `models.py`, `Settings.tsx`, and `Settings.test.tsx`, in the model sections. → This change touches only `PreferenceInput`, `read_preferences`, `save_preferences`, `AppSettings`, the Digest group, and the preferences mocks. Conflicts are expected to be in adjacent lines only; any conflict outside log files stops the merge for the user, per AGENTS.md.
- **[Requirements this change modifies]** `content-collection` "Gather related context for website items" (MODIFIED: the level's link count, author replies except at Off). New: `content-collection` "Choose how many linked pages a run reads", `user-interface` "Choose linked pages in Settings". `user-interface` "Settings explain risk and keep secrets out of view" and "Show Settings save results at Save", which #4 may modify, are not modified here. → If #4 or #32 also modifies "Gather related context for website items", the second to archive rebases its delta on the merged text.
- **[Off and items left pending]** Off leaves items NULL. A capture with saved replies becomes `gathered` at Off, so its links are not read later even when the user switches to Normal before it is delivered. → The same as when the limit is spent today; recorded as a limit.
- **[Token cost is not measured]** The change cannot measure tokens without the user's model. → The run already shows token totals; the user can compare runs at Shallow and Normal after the merge (Rollout).
- **[Shallow in large runs]** With many items, the per-run limit, not the level, bounds the run: Shallow then spreads the same 60 requests over more items, so it is not faster, but each summary request is smaller. → The note names the per-run limit.
- **[Downgrade]** Downgrading below `0010` drops the stored level; older code reads Normal's numbers from the environment. → No data loss beyond the choice.

## Migration Plan

- Migration `0010_link_depth` adds one column with a default; existing rows read `normal`.
- Rollback: downgrade to `0009_model_provider` drops the column.

## Testing

Test-first (D-016). Seams:
- `context_limits` and `link_depth_pages` in `catchup.context.depth`, directly, with parametrized tables over `Settings` objects built with `dataclasses.replace` (`backend/tests/test_context_depth.py`, new);
- `related_links` directly (`backend/tests/test_context_links.py`);
- `environment`, `seed`, `stub_collection(on_check=...)`, `execute` (`backend/tests/test_digest_runner.py`), and `setup`, `html`, `public_dns`, `capture_with_context` with `respx.mock(assert_all_mocked=True)` (`backend/tests/test_context_gather.py`); the level is set on the `AppSettings` row through `environment.app.state.session_factory()`;
- `api` and `TestClient(create_app())` (`backend/tests/test_settings_api.py`), with `client.app.state.settings` replaced for the server-number test;
- Alembic `command.upgrade` / `command.downgrade` on a temporary engine (`backend/tests/test_db.py`, as `test_model_provider_migration_defaults_existing_config_and_downgrades` does);
- the README text (`backend/tests/test_readme_context.py`);
- `Settings` rendered with the `fetchMock` preferences answers, `fireEvent.change` on the select, the `PUT` body, `toHaveAccessibleDescription`, and `expectAccessible` (`frontend/src/pages/Settings.test.tsx`).

Named mutations, each applied alone and restored:

| Id | Mutation | Must fail |
|---|---|---|
| L1 | `context_limits("off")` uses `settings.context_fetches_per_run` | the Off depth row; "Off makes no request" (`context_status` becomes `none`, not NULL); "Item left by Off is read later"; "Level changed during a run" |
| L2 | `context_limits("off")` keeps `settings.author_replies` | the Off depth row only: with a budget of 0, the pass drops the item before its post page (`gather.py:157-159`), so no run test sees it (checked on a prototype) |
| L3 | Shallow uses `settings.links_per_item` | the Shallow depth row; "Shallow reads three links" |
| L4 | Shallow uses 3 without `min` | the Shallow-under-2 depth row; "Shallow under a lower server setting" |
| L5 | `related_links` without the `limit <= 0` guard | the limit-0 links test |
| L6 | `link_depth_pages` returns a fixed 8 for Normal | the server-number API test; the 5-, 2-, and 1-link rows of `test_link_depth_pages` |
| L7 | `context_limits("normal")` uses a fixed 8 links | the `normal_server` depth row; "Normal follows the server setting"; the existing `test_configured_two_link_limit_never_requests_third` |
| G1 | `gather_context` ignores `level` (uses `settings` as today) | "Off makes no request"; "Shallow reads three links" |
| R1 | `run_digest` reads `link_depth` again after the source checks | "Level changed during a run" |
| R2 | `run_digest` does not pass the level | "Off makes no request" (through the runner) |
| R3 | `run_digest` uses `"off"` when no `AppSettings` row exists | "No level saved" (`test_run_without_saved_digest_settings_reads_at_normal`) |
| A1 | `save_preferences` stores any `link_depth` | the invalid-level API test |
| A2 | `read_preferences` returns `"normal"` without reading the row | the save-and-read API test |
| M1 | the migration's `server_default` is `"shallow"` | the migration test |
| U1 | Save leaves `link_depth` out of the `PUT` body | the save test; the load-and-keep-Off test |
| U2 | the Normal label uses a fixed 8 | the server-numbers test |
| U3 | the note is not linked by `aria-describedby` | the default-choice test |
| U4 | the select ignores the loaded level | the load-and-keep-Off test |

"Shallow under a lower server setting" and "Normal follows the server setting" pass before the change too, because Normal reads the same links; L4 and L7 show that they can fail. "No level saved" is covered by the existing context tests, which seed `AppSettings` without `link_depth` and must keep passing unchanged, by the migration test, and, for an instance with no `AppSettings` row, by `test_run_without_saved_digest_settings_reads_at_normal` (R3).

## Rollout

- Review: Claude Code runs the Docker smoke test, and a live check on a scratch container (fresh volume, a port other than 8800, a stub model): Settings at 1280 px and 375 px with the accessibility tree read; one run at each level over a local stub site with linked pages and comments, comparing the requests the stub site receives and the stored context.
- After the merge: the user can run one digest at Shallow and one at Normal on their own instance with their own model, and compare the token totals the run shows.
