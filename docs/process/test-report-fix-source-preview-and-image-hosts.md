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

## Review-only checks

- Docker build and `scripts/docker-smoke.sh`: not performed, explicitly excluded
  by the implementation request; Claude Code runs them at review.
- Live Sources slow-preview browser check and saved-digest image network check:
  not performed; Claude Code runs them at review.
