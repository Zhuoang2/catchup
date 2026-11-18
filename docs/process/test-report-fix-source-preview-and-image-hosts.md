# Test report: fix-source-preview-and-image-hosts

Implementation evidence, recorded as each task group runs. Python 3.12.13;
frontend and extension use Node 22.17.1.

## Setup

In each of `frontend/` and `extension/`:
`export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"` then
`npm ci --offline --no-audit --no-fund`, exit 0 (124 and 120 packages respectively).
Backend commands use `uv run`, with no new dependencies added.
All OpenSpec CLI commands are prefixed with `DO_NOT_TRACK=1`.

## Group 1: shared public-address rule and candidates

- Red: `uv run pytest tests/test_public_hosts.py`, exit 2, collection fails with
  `ModuleNotFoundError: No module named 'catchup.net.public_hosts'`, as required.
- Green: `uv run pytest tests/test_public_hosts.py tests/test_safe_fetch.py`,
  122 passed (53 new table cases, 69 existing fetch tests unchanged).
- Red: `uv run pytest tests/test_discovery.py::test_entry_images_on_local_addresses_are_dropped tests/test_extension_api.py::test_capture_drops_images_on_local_addresses`,
  2 failed, both returning local image candidates.
- Green: `uv run pytest`, 1024 passed, including both new candidate tests.
- `NAT64_PREFIX` search found no importers, only its definition and use in
  `safe_fetch.py`; the constant now belongs to `public_hosts.py`.

### Isolated mutations

Each mutation below ran alone with `uv run pytest -q`, exited 1 with the stated
assertion failures, and was restored byte-for-byte. After each restoration,
`git diff` for the affected production files matched the pre-mutation diff.
`table` means `tests/test_public_hosts.py`.

| Mutation | Tests run | Actual result and killing test |
| --- | --- | --- |
| H1 | table | 16 failed, 37 passed; `test_nonpublic_image_address_is_dropped`, private/special IPv4 and IPv6 rows |
| H2 | table | 14 failed, 39 passed; dropped rows including `0x7f.1` and `127.1` |
| H3 | table | 1 failed, 52 passed; `test_public_image_address_is_kept`, `example.com.` |
| H4 | table | 3 failed, 50 passed; dropped full-width IPv4, Unicode domain, and empty-label rows |
| H5 | table | 2 failed, 51 passed; dropped `nas.local` and `nas.local.` rows |
| H6 | table | 2 failed, 51 passed; dropped `printer` and `printer.` rows |
| H7 | table plus `tests/test_safe_fetch.py::test_nat64_embedded_public_address_allowed` | 2 failed, 52 passed; kept public NAT64 row and existing NAT64 fetch test |
| H8 | both new candidate tests named above | 2 failed; feed and capture both retained local images |
| H10 | table | 2 failed, 51 passed; both dropped backslash rows |

H1 retained literal parsing but bypassed `is_public_address` for IPv4 and IPv6.
H2 removed the numeric-last-label branch; H3 omitted trailing-dot removal;
H4 omitted the ASCII-name check; H5 omitted the `local` suffix; H6 allowed
single-label names; H7 omitted NAT64 conversion; H8 restored the old HTTP(S)
scheme-and-host candidate condition; H10 omitted backslash rejection.

## Group 2: saved digest images

- Red: `uv run pytest tests/test_digest_history.py::test_saved_digest_never_returns_local_images`,
  1 failed because the response included all three stored images.
- Green: `uv run pytest`, 1025 passed. The new test exercises detail and latest
  routes and verifies all three original image entries remain stored.
- H9 alone: return `item.images or []` unfiltered, then run
  `uv run pytest -q tests/test_digest_history.py::test_saved_digest_never_returns_local_images`:
  exit 1, 1 failed. Restored byte-for-byte and compared the restored `git diff`
  with its pre-mutation value.
- `git diff -- README.md`: only the requested Privacy paragraph was added.
  Searches for `Privacy` in `backend/tests`, `frontend/src`, and `extension/src`
  found no tests referring to that heading.

## Group 3: Sources page

- Red: `npx vitest run src/pages/Sources.test.tsx`, 5 new tests failed and
  all 46 existing tests passed.
- Green: the same command, 51 passed.
- Full frontend: `npm test -- --run`, 312 passed in 14 files;
  `npm run build`, exit 0 (`tsc --noEmit` and Vite).

New tests (all request timing uses deferred promises):

1. `shows loading progress and ignores Preview while a preview loads`:
   focus, focusable busy button, progress, repeated click/submission suppression,
   prevented native form submission, and clearing busy/progress on success.
2. `shows only the preview of the address in the field`: A/B answers out of
   order, editing clears busy/progress, and Confirm posts B's feed.
3. `ignores an error for an earlier address`: no obsolete error or busy state.
4. `announces the saved token but does not preview an address that changed during the save`:
   one token PUT while busy and no obsolete preview after saving.
5. `ignores a repeated preview for an address that changed while it loaded`:
   no obsolete X preview or loading state.

Each mutation ran alone with
`npx vitest run src/pages/Sources.test.tsx -t '<test name>'`
(F1 used names 2 and 3 joined by `|`), exited 1, then was restored byte-for-byte
with the restored `git diff` compared to the pre-mutation diff.

| Mutation | Change | Actual result / killing test above |
| --- | --- | --- |
| F1 | omit previewSource answer/error counter checks | 2 failed, 49 skipped; tests 2 and 3 |
| F2 | omit previewing guards | 1 failed, 50 skipped; test 1 saw 3 preview requests, expected 1 |
| F3 | omit Preview aria-disabled | 1 failed, 50 skipped; test 1 |
| F4 | omit LOADING messages | 1 failed, 50 skipped; test 1 |
| F5 | omit onChange counter increment and end-busy update | 1 failed, 50 skipped; test 2 |
| F6 | omit stale-PUT branch, proceed to preview | 1 failed, 50 skipped; test 4, missing saved-token announcement |
| F7 | put busy guard before preventDefault | 1 failed, 50 skipped; test 1, submit returned true; jsdom also reported native requestSubmit unimplemented |
| F8 | omit repeated-preview answer/error counter checks | 1 failed, 50 skipped; test 5 |

## Group 4: popup

- Red: `npx vitest run src/test/popup.test.ts`, all 4 new cases failed,
  all 84 existing tests passed, including the persistent status-line test.
- Green: same command, 88 passed.
- Full extension: `npm test -- --run`, 135 passed in 8 files;
  `npm run build`, exit 0 (TypeScript, Vite, and existing build checker).

New tests:

1. `keeps busy Follow focusable, shows progress, and sends one preview`:
   busy semantics, focus, progress, one request, focused heading, cleared status.
2. `ignores a preview that answers after the page was saved (200)` and `(422)`:
   deferred success and error preserve the saved view, status, and Add focus.
3. `makes Follow available again after a preview error`: the same Follow button
   is released and the error is announced.

Each mutation ran alone with
`npx vitest run src/test/popup.test.ts -t '<test name>'`
(the base name for test 2 selects both cases), exited 1, then was restored
byte-for-byte with restored `git diff` compared to the pre-mutation diff.

| Mutation | Change | Actual result / killing test above |
| --- | --- | --- |
| P1 | omit busy guard | 1 failed, 87 skipped; test 1 saw 2 previews, expected 1 |
| P2 | omit setting Follow aria-disabled true | 1 failed, 87 skipped; test 1 |
| P3 | omit view checks on success and error | 2 failed, 86 skipped; both test 2 cases |
| P4 | omit loading progress message | 1 failed, 87 skipped; test 1 |
| P5 | connected replaces content without incrementing views | 2 failed, 86 skipped; both test 2 cases |
| P6 | omit finally releasing trigger aria-disabled | 1 failed, 87 skipped; test 3 |

## Diagnosis

Ranked hypotheses were recorded after reproducing each symptom and before
implementing its fix:

| Symptom | Ranked hypotheses | Confirmed cause |
| --- | --- | --- |
| Local feed/capture candidates survive | 1. permissive shared filter; 2. feed URL rewriting; 3. capture bypasses filtering | Both paths preserve the local URL and use a filter accepting any HTTP(S) host |
| Saved digest exposes local images | 1. unfiltered serializer; 2. route caching; 3. storage mutation | Detail and latest share a serializer returning the stored images unchanged |
| Sources stale preview/error and no busy progress | 1. missing request invalidation; 2. response normalization; 3. wrong Confirm feed selection | Late answers change the UI before Confirm; no request counter or busy guard |
| Popup late preview replaces saved view/status | 1. missing busy/view guards; 2. capture-save ordering; 3. focus handling alone | Success replaces content and error overwrites status after a save, without checking which view requested the preview |

The fixes address these causes at the approved seams; no stored state meanings,
rows, dependency versions, or API shapes changed.

## Group 5: final checks

All six final commands were rerun after groups 1–4, with no active mutations:

| Directory | Command | Actual result |
| --- | --- | --- |
| `backend/` | `uv run pytest` | exit 0, 1025 passed (33.49 s) |
| `frontend/` | `npm test -- --run` | exit 0, 312 passed in 14 files |
| `frontend/` | `npm run build` | exit 0, TypeScript and Vite passed |
| `extension/` | `npm test -- --run` | exit 0, 135 passed in 8 files |
| `extension/` | `npm run build` | exit 0, TypeScript, Vite, and build checker passed |
| repository root | `DO_NOT_TRACK=1 openspec validate fix-source-preview-and-image-hosts --strict` | exit 0, change is valid |

Both JavaScript projects used
`export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"` for every test/build.
The OpenSpec status, list, and apply-instructions reads also exited 0.

### Coverage summary

These are behavioral test counts, not a measured line-coverage percentage:

| Suite | Existing tests unchanged | New test cases | Final total |
| --- | --- | --- | --- |
| Backend | 969 | 56 (53 public-host table rows, feed, capture, saved digest) | 1025 |
| Frontend | 307 | 5 Sources tests | 312 |
| Extension | 131 | 4 popup cases | 135 |

New backend test/mutation mapping:
`test_public_image_address_is_kept` kills H3/H7;
`test_nonpublic_image_address_is_dropped` kills H1/H2/H4/H5/H6/H10;
`test_entry_images_on_local_addresses_are_dropped` and
`test_capture_drops_images_on_local_addresses` each kill H8;
`test_saved_digest_never_returns_local_images` kills H9.
Frontend and popup mappings are recorded in their mutation tables above.

All 24 named mutations H1–H10, F1–F8, P1–P6 were killed individually and restored.
All specified red expectations held; all green checks passed. The only
nonzero test commands were the deliberate pre-fix red runs and mutation runs.
No real-network test or new sleep was added, apart from the existing popup
pattern's short 20 ms waits. No temporary mutation scripts or helper files
were created.

## Review-only checks

- Docker build and `scripts/docker-smoke.sh`: not performed, explicitly excluded
  by the implementation request; Claude Code runs them at review.
- Live Sources slow-preview browser check and saved-digest image network check:
  not performed; Claude Code runs them at review.
