# Test report: add-x-accounts (#41)

2026-10-27. Tasks 1–5 were implemented in order, with tests run red before
each implementation and green before checking off the task. Task 0.1 was
completed before this implementation. Tests use invented X payloads, `respx`
and fake model/Chrome clients. No real X token, API call, or authenticated
page was used.

## Red-first evidence

| Task | Observed failing check before implementation |
| --- | --- |
| 1.1 | Migration tests failed on the absent `0007` tables and run columns. |
| 1.2 | X settings route tests failed before token CRUD and usage-only test existed. |
| 1.3 | The extension could not save an initial X token; the replacement guard was mutation-tested. |
| 1.4 | Settings tests failed for the absent X group and updated ledes. |
| 2.1 | X API client tests failed before the client module existed. |
| 2.2 | X address recognition tests failed before the recognizer existed. |
| 2.3 | X preview and confirm tests failed before the routes handled X accounts. |
| 2.4 | Sources tests failed for the absent preview, token prompt and X status. |
| 3.1 | X account-check tests failed before the checker existed. |
| 3.2 | Budget and gap tests failed before the continuation logic existed. |
| 3.3 | Configuration/run tests failed before X source integration, deferral and counters existed. |
| 3.4 | Delivered X items retained text, replies and linked context before clearing was added. |
| 3.5 | Home and digest article tests failed before X counters, labels and icon were shown. |
| 3.6 | Delete-all backend and Settings tests failed before the endpoint and confirmation existed. |
| 4.1 | Four popup tests failed: no Follow button on profile/post and obsolete cannot-follow line. After implementation, 50 popup/manifest tests passed. |
| 4.2 | Eight popup tests failed: absent token prompt, settings direction and X error wording. After implementation, 58 popup/manifest tests passed. |
| 5.1 | README contract failed on the missing `## X accounts` heading. After documentation, 4 docs tests passed. |

The named temporary mutations were observed failing their corresponding
tests, then reverted: 1.3 allowing extension token replacement (409 guard);
3.2 updating `newest_id` without a gap; 3.3 rewriting a deferred check as
successful; 3.4 clearing every delivered item's text, including feed items;
and 3.6 deleting an entire topic that still held a non-X item. No mutation
remains in the branch.

The initial extension test command could not find Vitest; `npm ci` installed
the locked dependencies. A first token-prompt test query found the password
field's label ambiguous with its enclosing section's ARIA name; the section
name was made distinct. An existing backend test uses Python 3.12-only
f-string syntax and fails collection under the default Python 3.11, so final
backend checks explicitly selected 3.12.

## Final automated checks, in task order

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, 41 modules transformed. |
| `cd backend && uv run --python 3.12 pytest --cov=catchup --cov-report=term` | **706 passed**; **96%** statement coverage, 2,984/3,101 statements covered (117 missed). `sources/x_check.py` 98%, `sources/x_api.py` 94%, `sources/x_accounts.py` 94%, `digest/runner.py` 98%. |
| `cd frontend && npm test -- --run` | **254 passed** in 14 files. |
| `cd extension && npm test -- --run` | **104 passed** in 8 files, including popup axe checks with jsdom contrast disabled. |
| `cd extension && npm run build` | Passed, including TypeScript and packaged-file checks. |
| `docker build -t catchup:x-accounts-local .` | Passed locally. |
| `scripts/docker-smoke.sh catchup:x-accounts-local` | Passed: container health, API/UI/PWA, stored preference, non-root process, database volume, image exclusions, restart persistence. |
| `DO_NOT_TRACK=1 openspec validate add-x-accounts --strict` | Passed. |

The Docker frontend dependency install reported three audit findings (two
moderate, one high); the locked installation and build succeeded. Dependencies
were not changed as part of this feature.

## Not performed

A live X API test, browser extension interaction on a real X page, and
model-provider summarization with a real token were not performed. They
require the owner's credentials and policy decision. The Docker smoke is
local and does not publish the image.

## Fix round 1 (2026-10-28)

Tasks 6.1–6.8 followed the amended plan in `218af0d`. Each task was
checked off and committed after verification. All tests used invented X
payloads, offline routes and fake clients, not a real token or X request.

| Task | Red-first result or already-green guard |
| --- | --- |
| 6.1 | A complete two-page read retained `(newest_id, gap_since_id, gap_until_id) = ("300", "100", "201")` instead of `("300", None, None)`; a digest reported one account waiting instead of zero. The first combined run timed out after an empty continuation page; dedicated complete-read tests then failed. The budget-exhaustion guard passed. Re-derived `read_phase` from D5: change gaps on phase termination and treat an empty page as terminal. **69 passed**. |
| 6.2 | **5 failed, 15 passed**: valid data with partial errors was discarded, 200/403 suspensions were called not found, and an absent short URL inserted expanded text between characters. The not-found and reply-signal guards passed. After the fix, **20 passed**. |
| 6.3 | Three X subdomains returned no account error, preview/confirm reached `pytest.fail` discovery/fetch stubs, related context kept two X-owned links, and the popup offered Follow this site on `help.x.com`. Generic-extractor and look-alike guards passed. After sharing host detection without broadening the post extractor: focused backend **32 passed**, popup **59 passed**, extension build passed. |
| 6.4 | Six tests failed: cached confirm succeeded after token removal or secret change, delete-all/new-token reused the preview, late cache insertion after removal succeeded, and token/delete-all left cache entries. After clear and pre-cache token/decryption checks: **32 passed**. |
| 6.5 | Changed secret made token Test raise `InvalidToken` through TestClient (a production 500), without reaching the mocked usage endpoint. Shared the token decryption/error helper: **33 passed** across Sources and Settings. |
| 6.6 | **3 failed, 57 passed**: missing console hint and two rejected-token wording checks. `x_token_exists` already passed. Added accessible hint and distinct rejected wording: popup **60 passed**, extension build passed. |
| 6.7 | All six guards passed before mutation: scheduling, oldest ten replies, two source-count cases, lookup cursor, and Settings removal. An initial orphan fixture needed the second item orphaned explicitly; a check-order assertion and an optional mock route were corrected. Final focused backend **5 passed**, Settings **23 passed**. |
| 6.8 | Report and checks, not new runtime behavior; no red-first test applies. |

Every temporary named mutation failed and was reverted; focused tests
passed after reversion. Results:

| Task | Mutation and observed failure |
| --- | --- |
| 6.1 | Restore run-1 `read_phase`: complete-read test retained stale gap `("100", "201")`. |
| 6.2 | Check resource-not-found before suspension: two suspension tests failed. |
| 6.2 | Map `errors` even when `data` exists: two partial-data tests failed. |
| 6.2 | Drop `in_reply_to_user_id` signal: its single-signal guard failed. |
| 6.2 | Drop `replied_to` signal: its single-signal guard failed. |
| 6.3 | Apply X extractor to every X subdomain: generic-extractor test saw `extractX`. |
| 6.3 | Disable X extractor on account post pages: existing post-extractor test failed. |
| 6.3 | Remove dot boundary from host suffix: `notx.com` look-alike test failed. |
| 6.4 | Omit delete-all cache clear: cache-entry test failed. |
| 6.4 | Omit confirm token requirement: late-preview test returned 201 instead of 422. |
| 6.6 | Give `x_token_exists` the rejected-token prefix: exact-wording guard failed. |
| 6.6 | Change the prompt's `x_token_required` status to "Token needed.": its Sources-wording guard expected "X token needed." and failed. |
| 6.7 | Sort last-check descending, nulls first: B was not read and A was read. |
| 6.7 | Raise reply cap to 100: eleven replies were saved instead of ten. |
| 6.7 | Subtract X item count from source count: remaining feed digest had `source_count=0` instead of 1. |
| 6.7 | Ignore orphaned X items in source count: remaining feed digest had `source_count=2` instead of 1. |
| 6.7 | Ignore lookup ID at confirm: stored `"900"` instead of `"999"`. |
| 6.7 | Remove Settings DELETE call: no `DELETE /api/settings/x` was sent. |

### Fix-round final automated checks, in task 5.2 order

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, 41 modules transformed. |
| `cd backend && uv run --python 3.12 pytest --cov=catchup --cov-report=term` | **737 passed**, **96%** statement coverage: **3,007/3,119** covered (112 missed). `sources/x_check.py` 100%, `sources/x_api.py` 94%, `sources/x_accounts.py` 95%, `digest/runner.py` 98%. |
| `cd frontend && npm test -- --run` | **254 passed** in 14 files. |
| `cd extension && npm test -- --run` | **107 passed** in 8 files, including axe checks with jsdom color contrast disabled. |
| `cd extension && npm run build` | Passed, including TypeScript and packaged-file checks. |
| `docker build -t catchup:x-accounts-local .` | Passed locally. |
| `scripts/docker-smoke.sh catchup:x-accounts-local` | Passed: health, API/UI/PWA, stored preference, non-root process, volume, image exclusions, restart persistence. |
| `DO_NOT_TRACK=1 openspec validate add-x-accounts --strict` | Passed. |

Live X API, authenticated extension-on-X and real model-provider checks
remain unperformed; the Docker image was not published.

## Fix round 2 (2026-10-28, final Droid round)

Task group 7 followed the amended plan in `555053c`. New behavior was
observed failing before the fix; existing behavior was proved by the
specified mutations. Every temporary mutation was reverted.

| Task | Observed red or guard result |
| --- | --- |
| 7.1 | Phase B stopped at the first empty page with a continuation token (1 request instead of 2); Phase A likewise made 2 requests instead of 3 and missed posts behind its gap. After removing the empty-page stop, three bounded-route tests each failed immediately on request 41 without a page cap: empty Phase B, empty Phase A, and Phase B after 5 posts. A 40-page cap preserved the old cursor with no posts, preserved Phase A's gap, and saved an unread Phase B gap after 5 posts. All **15** focused X-check tests passed. |
| 7.2 | Backend host and context tests: **8 failed, 26 passed** before normalization. Hosts `x.com.`, `help.x.com.`, `twitter.com.`, and `X.COM` were unrecognized; the profile and two non-account addresses on trailing-dot hosts were misclassified; a trailing-dot X link was retained as context. Popup: **2 failed**, with the two look-alike guards passing. After normalizing one trailing dot and case, backend **34 passed**, popup **64 passed**, and extension build passed. |
| 7.3 | Confirming `http://[abc/feed` raised `ValueError: Invalid IPv6 URL` in TestClient instead of answering 422; `safe_fetch` was replaced by `pytest.fail` and was not reached. Mapping the pre-fetch parse error to `invalid_url` made both the new check and the existing X-host feed refusal pass (**2 passed**). |
| 7.4 | Both new guards passed unmodified. With the named missing-secret mutation, Test answered `secret_not_configured` rather than `secret_invalid`; with the title-only suspension mutation, lookup answered `x_account_not_found` rather than `x_account_suspended`. Both mutations were reverted; the focused X settings and API suites passed (**45 passed**). |
| 7.5 | Report and full checks, not a runtime behavior, so no red-first test applies. |

Named mutations and their bounded failures:

- **7.1, restore `or not page.posts`:** Phase B returned after one request rather than two; Phase A returned after two rather than three. Both tests failed assertions, not by hanging.
- **7.1, remove the page cap:** each of the three capped-page tests failed at the route's `pytest.fail("X requested page 41")`; no test hung.
- **7.2, drop the `.` boundary from popup `isXHost`:** `https://notx.com/simonw` lost "Follow this site", so its look-alike guard failed.
- **7.4, catch only `InvalidToken`:** the missing-secret test received `secret_not_configured` instead of `secret_invalid`, with zero usage requests.
- **7.4, ignore suspension in `title`:** the title-only suspension test received `x_account_not_found` instead of `x_account_suspended`.

### Fix-round-2 final automated checks, in task 5.2 order

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, 41 modules transformed. |
| `cd backend && uv run --python 3.12 pytest --cov=catchup --cov-report=term` | **754 passed**, **96%** statement coverage: **3,015/3,127** covered (112 missed). `sources/x_check.py` 100%, `sources/x_api.py` 94%, `sources/x_accounts.py` 95%, `api/sources.py` 91%. |
| `cd frontend && npm test -- --run` | **254 passed** in 14 files. |
| `cd extension && npm test -- --run` | **111 passed** in 8 files. |
| `cd extension && npm run build` | Passed, including TypeScript and packaged-file checks. |
| `docker build -t catchup:x-accounts-local .` | Passed locally. |
| `scripts/docker-smoke.sh catchup:x-accounts-local` | Passed: container health, API/UI/PWA, saved preference, non-root process, persistent volume, image exclusions, restart persistence. |
| `DO_NOT_TRACK=1 openspec validate add-x-accounts --strict` | Passed. |

No live X API, authenticated extension-on-X, or real model-provider check
was performed. The local Docker image was not published.

## Claude's review of fix round 2 (2026-10-28)

- **Delta review.** `/code-review` on `555053c..b73b31d` found no real defect. A spec sub-agent ran 20 mutations on the changed lines: 17 killed, 2 equivalent (normalizing a host that is already normalized; stripping every trailing dot instead of one), and 1 survivor, R17.
- **R17, the leftover test.** Dropping `normalizedHost` from the popup's `host` constant made Add on `https://x.com./writer/status/1` use the generic extractor, and no test noticed. Claude added that address to the post-page test in `extension/src/test/popup.test.ts`. Under R17 it fails ("1 failed | 111 passed"); without it, 112 pass.
- **Recorded, not changed:**
  - a phase that reaches the 40-page cap without reading any post sets no gap, so the next run asks for the same pages again (D5 accepts this; the timeline holds at most 3,200 posts, 32 full pages);
  - a host with two trailing dots is not normalized;
  - the host is normalized twice in `x_username` and in the popup's `isXHost`;
  - the popup's host line shows the normalized host.
- **Docker smoke** on `catchup:review-41` at `b73b31d`: 11 passed.

## Fix round 3 (2026-10-28)

Tasks 8.1–8.7 were worked in order and committed separately. All X test data
was invented and routed offline; no live X API or owner credential was used.

| Task | Red-first result or already-green guard |
| --- | --- |
| 8.1 | **4 failed, 1 passed**: both non-ASCII PUTs returned 200 rather than 422; both Test calls raised `UnicodeEncodeError` before usage. The printable-character save guard passed. After validation, X settings **29 passed**. |
| 8.2 | **4 safe-fetch failures**: initial X URLs failed at DNS instead of returning `blocked_address`, the redirect requested X, and the malformed URL raised `ValueError`. The article-text test first passed vacuously because DNS was blocked by the test fixture; after giving X a public mocked DNS answer, it failed by attempting the X route. After the central refusal, focused backend **185 passed**. The preview and related-link guards passed unchanged. An initial test command referenced nonexistent `test_links.py`; corrected it to `test_context_links.py`. |
| 8.3 | **6 failed**: malformed 200 timeline answers returned an empty/success page; a gapped check tried a second page instead of failing. After validating JSON, errors and metadata, X API/check **42 passed**; the empty final page guard passed. |
| 8.4 | Concurrent confirm finished while the test held `_start_lock`, so `alive` was false. The fresh-session, locked confirm passed, including the uncontended 201 guard; Sources **14 passed**. |
| 8.5 | Failed-run usage test: **1 failed, 1 passed**; 12 reads were absent while zero counters stayed hidden. After adding the notes, Home **93 passed** and frontend build passed. |
| 8.6 | The never-posted gap guard passed on unchanged code. Its named Phase A mutation failed with `KeyError: 'start_time'`; the restored guard passed. |
| 8.7 | README contract: **1 failed, 3 passed** without “thread” in the X section; after the disclosure, **4 passed**. |

Named mutations were run individually and reverted:

- **8.2, remove `_check_address` X-host refusal:** redirect test requested the mocked X page and failed `AssertionError: X page must never be fetched`; restored test passed.
- **8.4, write without `_start_lock`:** confirm finished during the held-lock interval (`alive` was false); restored tests passed.
- **8.6, send `start_time=None` in Phase A:** the next request lacked `start_time`, and the guard failed with `KeyError`; restored test passed. No mutation remains.

### Fix-round-3 final automated checks, in task 5.2 order

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed, 41 modules transformed. |
| `cd backend && uv run --python 3.12 pytest --cov=catchup --cov-report=term` | **772 passed**, **96%** statement coverage: **3,024/3,137** covered (113 missed). `sources/x_check.py` 100%, `sources/x_api.py` 95%, `sources/x_accounts.py` 95%, `net/safe_fetch.py` 94%, `net/x_hosts.py` 100%. |
| `cd frontend && npm test -- --run` | **256 passed** in 14 files. |
| `cd extension && npm test -- --run` | **112 passed** in 8 files. |
| `cd extension && npm run build` | Passed, including TypeScript and packaged-file checks. |
| `docker build -t catchup:x-accounts-local .` | Passed locally. |
| `scripts/docker-smoke.sh catchup:x-accounts-local` | Passed: 11 checks for health, API/UI/PWA, saved preference, non-root process, volume, image exclusions and restart persistence. |
| `DO_NOT_TRACK=1 openspec validate add-x-accounts --strict` | Passed. |

No live X API, authenticated extension-on-X, or real model-provider check was
performed. The local Docker image was not published.

## Claude's review of fix round 3 (2026-10-28)

- **Delta review.** `/code-review` on `38f033f..fa77990` reported 3 low findings. A spec sub-agent ran 24 mutations on the changed lines: 18 killed, 2 equivalent (the duplicate re-check under the lock, and confirm's early token check), and 4 survivors, S06, S07, S09, and S11. Docker smoke on `catchup:review-41` at `fa77990`: 11 passed.
- **Leftovers in Claude's review commit.** With the user's approval (an exception to D-023, recorded in D-025), Claude fixed two small behavior gaps test-first, and added tests for three survivors:
  - **A redirect to an unparsable address.** `test_redirect_to_unparseable_location_is_invalid_url` failed first (`urljoin` raised `ValueError`). `safe_fetch` now maps it to `invalid_url`. Mutation "unguarded `urljoin`": 1 failed.
  - **A failed run's notes.** `shows only billed X reads on failed run` failed first for both cases (the transcript and deferred-video lines appeared). The failed branch now shows only "N X posts read" (D9). Restoring `HeldNotes` there fails both cases.
  - **S06, S07** (`body = {}` after a JSON error; no `fetch_failed` for errors-only answers): `test_invalid_lookup_and_usage_answers_are_fetch_failed_with_status`, 1 failed under each.
  - **S09** (`result_count` checked for presence only): `test_text_result_count_is_fetch_failed`, 1 failed.
- **Recorded, not changed:**
  - S11: the request's session would see a deleted token too; D4 now calls the new session a defensive choice;
  - the X-host refusal uses code `blocked_address`, which the Sources page and the popup show as "This address is not allowed.";
  - an errors-only timeline answer with `meta` now fails the account, by design (D2).
- **Checks after the commit:** backend 776 passed; frontend 256 passed, build passed; extension unchanged.

## The user's live check, and one layout fix (2026-11-01)

- **Live check, part 1.** On a test instance (a copy of the user's data, migrated to `0007`), the user saved and tested their own token, followed one account, refused `https://help.x.com/en`, and ran a digest. The two recent posts held at follow were delivered under "X · <name>", linking to the posts; their stored text, replies, and contexts were cleared afterwards. The run read 0 posts, because none were newer than the follow.
- **The billing note's layout.** The user saw the note in the "X accounts" group split into three columns: `.note` is a flex row, and the note's text, link, and period were three flex items. The note now wraps its sentence in one `<span>`, after the info icon, like the other notes. A new check in `loads a saved token without putting it in the field` failed first (the note had bare text nodes) and passes now.
- **The "Delete all X data" button in dark mode.** Checking the fix above in a browser, Claude found the button drawn in the browser's default light grey with the dark theme's light orange error text, about 1.6:1. It uses `variant="danger"`, and `.btn-danger` set only a color. `.btn-danger` now has a transparent background and the ghost buttons' hover. A new CSS check in `styles/tokens.test.ts` failed first and passes now. (axe in jsdom cannot see this, because it does not compute colors.)
