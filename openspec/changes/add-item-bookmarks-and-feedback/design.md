# Design

See `proposal.md` for why. The requirements are in the spec deltas: `digest-history` (marks and the bookmarks list), `user-interface` (controls, the Bookmarks screen, and the modified "Digest reading layout"), and `x-accounts` (the modified "Delete all X data").

## Context

- **A digest is a snapshot** (`backend/src/catchup/models.py:218-235`). Each `DigestItem` row copies the item's title, link, source name and kind, publish time, summary, "Also read" links, and images. Its `item_id` points at the stored `Item`, with `ON DELETE SET NULL`. Reading a digest uses only the snapshot (`backend/src/catchup/api/digests.py:57-111`). The topic items in the answer have no identifier today.
- **An item is delivered once.**
  - A run snapshots each summarized item, or each item listed in Creator updates, into exactly one `DigestItem`, and then sets the item's state to `delivered` (`backend/src/catchup/digest/runner.py:500-546`).
  - Runs and the extension read only `pending` items (`backend/src/catchup/collection.py:114-121`, `backend/src/catchup/api/extension.py:73-214`).
  - So the same stored item never shows up in a later digest. A post that is published again gets a new identity, and becomes a new item.
- **Creator updates are digest items too.** They sit in a topic of kind `creator_updates`, with no summary and an `update_reason` (`runner.py:520-546`).
- **What deletes digest items.**
  - Deleting a source cascades to its stored `Item` rows. The `DigestItem` rows stay, with `item_id` set to NULL (`backend/src/catchup/api/sources.py:354-360`).
  - "Delete all X data" deletes every `DigestItem` from X. Then it deletes topics, and digests, that are left empty (`backend/src/catchup/api/settings.py:127-181`).
  - Removing a page saved from the browser deletes only pending items (`backend/src/catchup/api/extension.py:208-221`).
  - Nothing else deletes digests or digest items.
- **SQLite settings** (`backend/src/catchup/db.py:22-27`): every connection runs `PRAGMA foreign_keys=ON` and `PRAGMA secure_delete=ON`.
- **Cross-site writes** (`backend/src/catchup/main.py:122-146`). Every `POST`, `PUT`, `PATCH`, and `DELETE` with a foreign `Origin`, or with `Sec-Fetch-Site` set to `cross-site` or `same-site`, is refused with `cross_site_request`. A browser connection token is accepted only for the operations in `_extension_operation` (`main.py:55-61`). New write endpoints are covered without any change.
- **The digest layout** (`frontend/src/components/DigestArticle.tsx:79-104`, `frontend/src/styles/layout.css:23-31`).
  - Each `article.item` has the children `p.item-meta`, `h3.item-title`, and then `div.item-body` or `p.summary-unavailable`.
  - Above 1100 px the item is a subgrid with rows `auto auto 1fr`: the source line in row 1 and the title in row 2, both in columns 1–3; the summary spans rows `1 / -1` in columns 4 to the end.
  - `frontend/src/styles/tokens.test.ts:262-300` guards these rules. Item children must not be placed outside `@container (width > 1100px)`, and only `.items > .item` and `.items > .item + .item` may be styled there.
  - `frontend/src/pages/DigestView.test.tsx:76-78` and `:341-345` pin the children's order.
- **Navigation** (`frontend/src/components/AppShell.tsx:7-12`, `layout.css:59-71`). Four text links, kept on one row with no wrapping, in small capitals at 0.82 rem below 900 px. At 320 px the row has 288 px. A rough estimate from character widths puts the four links at about 270 px, so a fifth link would not fit without smaller text or icons. That is not measured.
- **The main screen** (`frontend/src/pages/Home.tsx:135-212`). A new digest replaces the shown one in place. The items keep their keys by position, so DOM nodes are reused across digests. Focus is moved only when the first digest replaces the Generate screen (`:150-154`, `:206`).
- **Type checks.** `npm run build` runs `tsc --noEmit` over `src/`, including the tests. `frontend/src/components/DigestArticle.test.tsx:8-15` passes a typed `digest` fixture; the other digest fixtures are untyped fetch answers.

### Probes (offline, `uv run --offline` in `backend/`, 2026-11-25; scripts in the session scratchpad)

- **Cascade without an ORM relationship.**
  - A child table with `ForeignKey("digest_items.id", ondelete="CASCADE")` as its primary key, and no `relationship`, was created with `catchup.db.make_engine`, where `PRAGMA foreign_keys` reads 1.
  - `session.delete(DigestItem)` removed its child row and kept the other one.
  - `session.delete(Digest)` removed the digest's items and their child rows, through the database's own cascades (`digest_items.digest_id` is `ON DELETE CASCADE`).
- **Concurrent first writes.** SQLAlchemy 2.1.3's `sqlite.insert(...).on_conflict_do_nothing(index_elements=["digest_item_id"])`, followed by `session.get` and an attribute change, was run from two threads at once on the same new row, each setting a different column. Both columns were saved, one row exists, and the ORM sent two `UPDATE`s. A second insert-or-ignore on the existing row did not fail.
- **Pydantic 2.13.5.**
  - A `str` field refuses `1` (`string_type`).
  - `note: str | None = None` refuses `5`, and accepts `None`.
  - A missing required `rating` is refused as `missing`.
  - The app answers all of these as 422 `invalid_request` (`backend/src/catchup/errors.py:30-35`).
- **Note length.** HTML `maxlength` counts UTF-16 code units, and Python's `len` counts code points. A note within the browser's 500 units is therefore always within the server's 500 code points. Only a client other than the browser can send more, and the server refuses it.

## Goals / Non-Goals

**Goals:** the marks and the Bookmarks screen as the specs describe them; marks that last as long as their digest item and go with it; nothing that changes digests or runs.

**Non-goals:**
- using marks in collection, ranking, summaries, or grouping (#9, later);
- exporting ratings and notes (#10 decides that);
- marks on Creator updates;
- a fifth navigation item;
- sorting or filtering the Bookmarks screen;
- changes to the extension.

## Decisions

### D1. One marks row per digest item (decisions U1, U6)

`DigestItemMark` in `backend/src/catchup/models.py`, table `digest_item_marks`:

| Column | Type | Meaning |
| --- | --- | --- |
| `digest_item_id` | integer, primary key, `ForeignKey("digest_items.id", ondelete="CASCADE")` | the marked item |
| `bookmarked_at` | `UTCDateTime`, NULL | the first bookmark time, or NULL |
| `liked_at` | `UTCDateTime`, NULL | the like time, or NULL |
| `rating` | `String(8)`, NULL | `good`, `poor`, or NULL |
| `note` | `Text`, NULL | the note, or NULL; never set without a rating |
| `rated_at` | `UTCDateTime`, NULL | the time of the last saved feedback |
| `updated_at` | `UTCDateTime`, not NULL, default `utc_now` | the last change |

- **No ORM relationship on `DigestItem`.** The database deletes the row with its digest item (probe 1), including in "Delete all X data", which deletes `DigestItem` rows one by one through the ORM. `secure_delete` overwrites the deleted note.
- **Rows are never deleted when the marks are cleared.** A row with all marks cleared means "no marks". If rows were deleted, a request clearing the last mark and another request setting a different one could meet: the second request's `UPDATE` would find no row, and fail with a stale-data error.
- **Writes** create the row with `INSERT … ON CONFLICT (digest_item_id) DO NOTHING`, then load it and change only their own columns. Two concurrent first writes both succeed (probe 2).
- A separate table, rather than columns on `digest_items`, keeps the snapshot table holding only what the run saved, so "the content shown MUST be the content that was saved" stays true by construction.

### D2. Migration `0012_digest_item_marks`

- `revision = "0012_digest_item_marks"`, `down_revision = "0011_model_reasoning"`.
- `upgrade()` creates the table of D1, with its foreign key and `ondelete="CASCADE"`. No existing row changes.
- `downgrade()` drops the table. The module docstring says that a downgrade loses every bookmark, like, rating, and note.

### D3. Mark endpoints (`backend/src/catchup/api/marks.py`, included in `main.py` after `digests_router`)

| Request | Body | Effect |
| --- | --- | --- |
| `PUT /api/digest-items/{id}/bookmark` | none | set `bookmarked_at` if NULL |
| `DELETE /api/digest-items/{id}/bookmark` | none | `bookmarked_at = NULL` |
| `PUT /api/digest-items/{id}/like` | none | set `liked_at` if NULL |
| `DELETE /api/digest-items/{id}/like` | none | `liked_at = NULL` |
| `PUT /api/digest-items/{id}/feedback` | `{"rating": "good" \| "poor", "note": string \| null}` | replace the rating and the note; `rated_at = now` |
| `DELETE /api/digest-items/{id}/feedback` | none | `rating = note = rated_at = NULL` |

- **Answers.** Every request answers 200 with `{"id": <digest item id>, "bookmarked": bool, "liked": bool, "rating": "good" | "poor" | null, "note": string | null}`. Each change also sets `updated_at`. Each request reads `utc_now()` (imported into `marks.py`) once, and uses that value for every time it writes. Every successful request writes `updated_at`, also one that changes no mark; a repeated bookmark keeps its first `bookmarked_at`, and a repeated like its first `liked_at`.
- **Errors.** None of them writes anything.
  - FastAPI validates the body before the handler runs. So for `PUT …/feedback`, wrong JSON types or a missing `rating` (`FeedbackInput(rating: str, note: str | None = None)`) come first: 422 `invalid_request`, from the existing handler.
  - Then the handler checks, in this order:
    1. no `DigestItem` with that id: 404 `not_found`, "Digest item not found.";
    2. its topic's `kind` is `creator_updates`: 422 `not_markable`, "Items in Creator updates cannot be bookmarked or rated.";
    3. for `PUT …/feedback`:
       - an item with `summary_unavailable` or no summary: 422 `no_summary`, "This item has no summary to rate.";
       - a `rating` that is not `good` or `poor`: 422 `invalid_feedback`, "Choose Good or Poor for the summary.";
       - a note longer than 500 characters after `strip()`: 422 `invalid_feedback`, "Keep the note to 500 characters or fewer.".
- **The note** is stored stripped, and an empty note as NULL.
- **Cross-site requests, and requests with a browser connection token**, are refused by the existing middleware with 403 `cross_site_request`. `_extension_operation` is not changed.

### D4. Digest answers carry marks

- Split the item dict of `_serialize_digest` (`backend/src/catchup/api/digests.py:70-82`) into a module function, `item_answer(item: DigestItem, mark: DigestItemMark | None) -> dict`.
  - It returns today's keys, with the same image filter (`is_public_url`, `is_formula_image`).
  - It adds `"id": item.id`, `"bookmarked"`, `"liked"`, `"rating"`, and `"note"`, all false or `None` without a mark.
- `_serialize_digest` loads the marks of the digest's items in one query: `select(DigestItemMark).where(DigestItemMark.digest_item_id.in_(ids))`.
- The Creator updates answer is unchanged. The list endpoint `GET /api/digests` is unchanged, and so is its constant query count (`backend/tests/test_digest_history.py:250`).

### D5. Bookmarks list (`GET /api/bookmarks`, in `marks.py`)

- **Query.** `DigestItem` joined to `DigestItemMark`, `Digest`, and `DigestTopic`, with `bookmarked_at IS NOT NULL` and topic kind `topic`. Ordered by `bookmarked_at DESC`, then `DigestItem.id DESC`.
- **Each entry** is `item_answer(item, mark)`, plus:
  - `"bookmarked_at"`;
  - `"digest": {"id", "created_at", "language"}`.
- **No paging.** A personal list stays small; Risks covers this.

### D6. Item controls (`frontend/src/components/DigestArticle.tsx`)

**Types and component.**
- The `DigestItem` type gains `id: number`, `bookmarked: boolean`, `liked: boolean`, `rating: 'good' | 'poor' | null`, and `note: string | null`. A new `type Marks = { id: number; bookmarked: boolean; liked: boolean; rating: 'good' | 'poor' | null; note: string | null }` describes the endpoints' answer.
- **`ItemActions({ item, title, announce, onChange? })`** renders `<div className="item-actions">` as the last child of `article.item`, after `div.item-body` or `p.summary-unavailable`.
  - Its state starts from the item's marks.
  - `DigestArticle` keys it by `` `${digest.id}-${item.id}` ``, so that a new digest never inherits another item's state.

**Contents, in order:**
1. **Bookmark.** `<Button variant="ghost" size="sm" aria-pressed={bookmarked}>{bookmarked && <Icon name="check" className="icon icon-xs"/>}Bookmark<span className="sr-only"> {title}</span></Button>`. Its accessible name is "Bookmark <title>". `Icon` renders `aria-hidden="true"` (`frontend/src/components/Icon.tsx:23`), so the name does not change.
2. **Like.** The same pattern: "Like <title>".

   A pressed toggle shows the check icon and a strong border, not only a color change, because status must never be conveyed by color alone (`user-interface` "Themes follow the system with accessible contrast").
3. **Feedback**, only when the item has a summary and its summary is available. `<Button variant="ghost" size="sm" aria-expanded={open} aria-controls={panelId}>Feedback<span className="sr-only"> on {title}</span></Button>`. When a rating is saved, it is followed by `<span className="feedback-state">Rated good</span>` or `Rated poor`.
4. **The error.** `<p role="alert" className="item-error">` with the error's message, only when the last change failed.
5. **The panel**, when open: `<div id={panelId} className="feedback-panel" role="group" aria-label={`Feedback on ${title}`}>`, holding:
   - `<fieldset>` with `<legend>How was this summary?</legend>`, and two radio inputs, labelled Good (`good`) and Poor (`poor`), named `rating-<id>`;
   - `<label htmlFor="note-<id>">Note (optional)</label>`, and a `<textarea id="note-<id>" maxLength={500} aria-describedby="note-hint-<id>">` with `<p id="note-hint-<id>" className="field-hint">Only kept in CatchUp. Up to 500 characters.</p>`;
   - the rating error `<p id="rating-error-<id>" className="field-error" role="alert">Choose Good or Poor.</p>`, shown after Save feedback with no rating. It is an alert because errors are announced as alerts (`user-interface` "Keep focus and announcements when content changes in place"), as `Sources.tsx:283` does. While it is shown, both radios have `aria-invalid="true"` and `aria-describedby="rating-error-<id>"`;
   - **Save feedback** (`variant="primary" size="sm"`); **Remove feedback**, only when a rating is saved; and **Cancel**.

**Behavior:**
- **Busy.** One request at a time per control. While a control's request runs, it has `aria-disabled="true"` and its click does nothing (the pattern of `Home.tsx:267`). Save feedback and Remove feedback share one busy flag.
- **State.** The new state comes from the server's answer. Nothing changes optimistically.
- **Messages.** When a change starts, `announce('')` empties the status region. On success, `announce(message)` sends one of "Bookmarked.", "Bookmark removed.", "Liked.", "Like removed.", "Feedback saved.", or "Feedback removed.". Emptying first makes a message that repeats the previous one, such as "Liked." twice, a new announcement. Settings does the same: it empties its message when a save starts (`Settings.tsx:355`), and then sets "Settings saved." (`:387`). On failure, the error paragraph shows `ApiError.message`, and the state stays as it was. The next activation clears the error.
- **Focus.** Save feedback (on success), Remove feedback (on success), and Cancel close the panel, and move focus to the Feedback button with `useLayoutEffect` after the close. Opening the panel keeps focus on Feedback.
- **The status region.** `DigestArticle` holds one `<p className="sr-only" role="status">` for these messages, empty until the first message. It is inside the article's section, so it is on the page before any message. `announce` replaces its text.

**CSS:**
- `components.css`:
  - `.item-actions { display: flex; flex-wrap: wrap; align-items: center; gap: .35rem .5rem; min-width: 0; }`;
  - `.item-actions .btn[aria-pressed="true"] { color: var(--fg) !important; border-color: var(--border-strong); }`. `.btn` already has a 1 px transparent border (`components.css:15`), and both tokens exist in `tokens.css`;
  - a `.feedback-panel` with a full-width textarea;
  - `.feedback-state` and `.item-error`, in the muted and error colors.
- `layout.css`, inside the existing `@container (width > 1100px)` block only: `.items > .item > .item-actions { grid-column: 1 / span 3; grid-row: 3; align-self: start; }`. Outside it, the actions follow the summary in DOM order (spec "Digest reading layout").

### D7. Bookmarks screen (`frontend/src/pages/Bookmarks.tsx`, route `/bookmarks`)

**Loading:**
- `useDocumentTitle('Bookmarks')`.
- It loads `GET /api/bookmarks` and `GET /api/settings/preferences`, which falls back to `{ show_images: true }` on failure, as `DigestView.tsx:20-23` does.

**The screen:**
- `<PageHead title="Bookmarks" lede="Items you bookmarked, newest first. They stay when their source is deleted.">`, with `<p className="back-link"><Link to="/digests">← All digests</Link></p>`.
- While loading: "Loading bookmarks…". A load error: `role="alert"`.
- **Empty.** `<div className="empty-state">`, `<h2>No bookmarks yet</h2>`, `<p>Bookmark an item in a digest to keep it here.</p>`, and `<Link to="/" className={buttonClass('primary')}>Open the latest digest</Link>`.
- **The list.** `<ol className="bookmark-list">`; each `<li>` holds an `article.item` with the same source line, title, body (or "Summary unavailable"), and `ItemActions` as in D6, in this order:
  - source line;
  - title;
  - body;
  - `<p className="bookmark-from"><Link to={`/digests/${digest.id}`}>From No. {digest.id} · {shortDate(digest.created_at)}</Link></p>` (the whole "From No. … · date" is the link, as the spec says);
  - controls.
- The summary uses `lang={digestLang(entry.digest.language)}`.
- **A shared renderer.** The source line, title, and body markup move out of `DigestArticle` into an exported `ItemContent({ item, lang, showImages, imageKey })`, so both screens render items the same way.
- **The status region.** The screen holds its own `<p className="sr-only" role="status">` inside its section, empty until the first message. Its setter goes to each entry's `ItemActions` as `announce`.
- **Removing a bookmark** updates only that entry's `bookmarked` flag (decision U7). The entry stays.
- **CSS.** `.bookmark-list` is a list without markers, with the border rules of `.items > .item + .item`. It sets no `grid-template` on `.item`, which `tokens.test.ts` forbids outside the wide block.

### D8. History link, route, and navigation

- **History.** `History.tsx`'s `PageHead` gains `<p className="history-links"><Link to="/bookmarks">Bookmarks</Link></p>` after its lede. It is shown also when no digest is saved.
- **Route.** `App.tsx` adds `<Route path="/bookmarks" element={<Bookmarks />} />`.
- **Navigation.** In `AppShell.tsx`, `/bookmarks` maps to `data-screen="bookmarks"`. The History link gets `aria-current="page"` on it, as on a digest. The full masthead stays.

### D9. Main screen focus

- In `Home.tsx`, where a fetched new digest replaces the shown one (`:205-207`), also set `focusNext.current = 'generate'` when `digest` is set and `document.activeElement?.closest('.item-actions')` is not null. The existing layout effect then focuses the run bar's Generate.
- This covers the spec scenario "New digest while a control has focus". Because `ItemActions` is keyed by digest and item (D6), the old digest's controls unmount when the new digest arrives. Without D9, focus would then fall to the page body.

### D10. README

- The intro paragraph gains: "Bookmark or like the items in a digest's topics, or rate their summaries; bookmarked items are listed under Bookmarks, linked from History."
- **Privacy** gains: "Bookmarks, likes, ratings, and notes stay in CatchUp's local database. They are never sent to the model provider, and they do not change later digests."

## Decisions for the user

- **U1. What is marked.**
  - Recommended (A): an item as it appears in one digest (`DigestItem`): items in topics, including ones whose summary is unavailable. The rating is about the summary text that digest showed. Marks survive source deletion, because the digest keeps the item. An item is delivered once (Context), so marks never split across digests.
  - Alternative (B): the stored `Item`. Marks would be lost when the source is deleted, because items cascade, and the summary that was rated could differ from the one saved in the digest. The bookmarks list would also need the snapshot anyway.
  - Alternative (C): A, plus Bookmark on Creator updates entries, to keep a video or episode without a transcript for later. If chosen: D3 drops `not_markable` for bookmarks only, the Creator updates list gains a Bookmark toggle, and the Bookmarks screen shows such entries with their reason instead of a summary.
- **U2. Which marks.**
  - Recommended (A): Bookmark and Like as two independent toggles, with no negative content signal. The summary's quality gets its own rating in U3. Like records interest, which #9 could use later.
  - Alternative (B): Bookmark only, with "like" read as a Good summary rating. This uses fewer controls, but mixes "I liked this news" with "the summary was good".
  - Alternative (C): Like and Dislike, plus Bookmark. A negative content signal has no use until ranking exists, and it adds a third toggle.
- **U3. Summary feedback.**
  - Recommended (A): a Feedback panel with a required Good or Poor rating, and an optional note of up to 500 characters, saved together by Save feedback. The reading view keeps three controls per item.
  - Alternative (B): inline Good summary and Poor summary toggles that save at once, plus a separate note editor. One click to rate, but five controls per item.
  - Alternative (C): A, plus fixed reasons for Poor: "Wrong or made-up facts", "Misses the main point", "Hard to read". Easier to count for #10. If chosen: a `reasons` JSON column, checkboxes in the panel, and `invalid_feedback` for unknown reasons.
- **U4. Where bookmarks are found.**
  - Recommended (A): a Bookmarks screen at `/bookmarks`, linked from History, with History marked current. The navigation keeps four items, which fit one row at 320 px today.
  - Alternative (B): a fifth navigation item, "Bookmarks". By the estimate in Context it would not fit one row at 320 px without smaller text or icon-only links. Measure it before choosing B.
  - Alternative (C): a "Bookmarked only" filter on History, with no new screen. History lists digests, not items, so the filter would need a second list layout anyway.
- **U5. Later digests and #10.**
  - Recommended (A): record only. Nothing is sent to the model, and generation is unchanged. #10's plan decides how to export ratings and notes.
  - Alternative (B): A, plus `GET /api/feedback`, a JSON download of every rated item (title, link, summary, rating, note, digest) linked from Settings. This gives #10 its samples now, with one more endpoint and one more Settings line.
  - Alternative (C): use likes or ratings to order items in later digests. This overlaps #9, and changes generation.
- **U6. Deletion.**
  - Recommended (A): marks go with their digest item. "Delete all X data" removes those on X items, and a digest left empty takes its marks along. The confirmation text stays: "This removes your X token, followed X accounts, and their items in saved digests." The marks are part of those items. The spec names them.
  - Alternative (B): A, and the confirmation also says "with your bookmarks and feedback on them". `Settings.tsx:564` changes, and `Settings.test.tsx:1337` pins that text.
- **U7. Removing a bookmark on the Bookmarks screen.**
  - Recommended (A): the entry stays, unpressed, until the screen is opened again. Focus stays put, and a mistaken click is undone with one more click.
  - Alternative (B): the entry disappears at once. Focus then moves to the next entry's Bookmark, or to the previous entry's when it was the last one, or to the heading when none is left. A focus rule for each case, and no undo.

## Risks / Trade-offs

- **[Parallel changes]** → #54's Deep level edits `context/`, the preferences, and Settings, and its plan adds no migration. If it does add one, the second change to merge renumbers its migration and updates the head assertions in `backend/tests/test_db.py`, as #4 and #54 did. The log files conflict as usual.
- **[A long Bookmarks list]** → One request with no paging. Hundreds of entries render in one page, which stays usable for a personal tool. Paging can come later without a spec change to the order.
- **[Notes are personal text]** → They stay in the local SQLite database on the data volume, and the README says so. Backups of the volume include them (`local-deployment` "Back up and restore the data volume"). They are never logged: the mark endpoints log nothing.
- **[Marks on X items]** → They hold no X content themselves. They are still deleted with the item, so "Delete all X data" leaves nothing tied to an X post.
- **[Reused item nodes on the main screen]** → D6 keys `ItemActions` by digest and item, and D9 moves focus. Without both, a new digest could show an old item's busy state or panel, or leave focus on the wrong item.
- **[Two status regions on the main screen]** → The run's region (`id="run-status"`) and the digest's. Each announces its own messages, and the run's region is not shared. `Home.test.tsx` then finds the run's region by its id instead of by role.
- **[Three controls on every item]** → More visual weight in the reading view. They are small ghost buttons, under the title on wide screens. U3 (B) would add more.
- **[No measurement of the fifth navigation item]** → It matters only if the user chooses U4 (B).

## Migration Plan

1. The upgrade creates the empty `digest_item_marks` table. Digests and items are not touched.
2. Rollback: downgrade to `0011_model_reasoning`, which drops the table and every mark, then install the previous image.

## Testing

- **Backend.**
  - The API through `TestClient(create_app(test_settings))`, with seeded digests (`seed_history` in `backend/tests/test_digest_history.py:10-54`, `seed_mixed_digest` in `backend/tests/test_x_settings_api.py:167`).
  - The migration through the Alembic `Config` and `command` pattern of `backend/tests/test_db.py:118-144`.
  - Cross-site requests through an `Origin` header, and the extension through a created connection token, as in `backend/tests/test_extension_api.py`.
- **Frontend.**
  - `DigestArticle` rendered directly, with a `fetchMock`.
  - The Bookmarks screen through `MemoryRouter`.
  - The main screen through `mockPage` and `watchPollTimer` in `frontend/src/pages/Home.test.tsx`.
  - `expectAccessible` (axe) on each new view.
- **Named mutations, as in `tasks.md`:** M1–M3 (data and migration), A1–A11 (API), U1–U13 (controls), B1–B6 (bookmarks list, Bookmarks screen, and navigation), H1 (main screen focus), and Doc (README).
- **Review (Claude Code).** `/code-review`, the spec sub-agent, `scripts/docker-smoke.sh`, and a live check on a scratch container on a port other than 8800. Seed a digest through the extension API and a local stub model. Then, in the browser:
  - bookmark, like, and rate an item, and reload;
  - open Bookmarks from History;
  - remove a bookmark;
  - check 1440 px (controls under the title) and 320 px (no horizontal scroll, with the panel open);
  - restart the container, and check that the marks are still there.

  The X deletion is covered by the backend tests; the live check follows no X account.
