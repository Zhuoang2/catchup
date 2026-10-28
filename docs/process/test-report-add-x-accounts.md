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
