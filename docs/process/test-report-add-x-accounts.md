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
