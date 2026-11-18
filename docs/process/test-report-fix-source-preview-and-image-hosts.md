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

## Review by Claude Code

Date: 2026-11-18. Range reviewed: `da3811a..35aa29b`, in a separate review
worktree. Review method: D-016 (`/code-review` at high effort, an independent
spec sub-agent with mutations, Claude Code's own checks and live checks).

### Checks

| Check | Result |
| --- | --- |
| `uv run pytest` in `backend/`, at `35aa29b` | **1,025 passed**. |
| `uv run pytest` in `backend/`, with the review edits | **1,034 passed** (nine new table rows). |
| `npx vitest run` and `npm run build` in `frontend/`, Node 22.17.1 | **312 passed** at `35aa29b`, **314** with the review edits; build passed. |
| `npx vitest run` and `npm run build` in `extension/`, Node 22.17.1 | **135 passed**; build passed. |
| `DO_NOT_TRACK=1 openspec validate fix-source-preview-and-image-hosts --strict` | Valid, before and after the review edits. |
| `docker build -t catchup:fix73-local .` at `35aa29b` | Passed. |
| `scripts/docker-smoke.sh catchup:fix73-local` | Passed all **12 checks** at `35aa29b`, and again after rebuilding at the review commit `8b36068`; no container or volume left. |

### Live checks

- **Setup.** Two images, one built from a clean `main` worktree at `866be0d`
  and one from the branch at `35aa29b`. Each ran in its own container, on a
  local port (not 8800), with a fresh volume.
- **Saved images.** The same two digests were written into both databases:
  - digest 1 with `http://192.168.1.1/live73-cam.jpg`,
    `http://192.168.1.1\@cdn.example.com/live73-b.png`, and a public image;
  - digest 2 with `http://127.0.0.1:9/live73-loop.jpg`,
    `http://localhost:9/live73-name.png`, and the same public image.

  `GET /api/digests/latest` and `/api/digests/{id}` on `main` returned all
  three images; on the branch, only the public one. In the browser, `main`'s
  `/digests/2` requested `http://127.0.0.1:9/live73-loop.jpg` and
  `http://localhost:9/live73-name.png` (Chrome then refused them with
  `ERR_UNSAFE_PORT`). On the branch, `/digests/1`, `/digests/2`, and the main
  screen requested neither, and showed only the public image's `<img>`.
  `main`'s digest 1 was not opened in a browser, because that would have
  requested a device on the reviewer's own network.
- **Sources preview.** Address A was `https://httpbin.org/delay/5` (answers
  after at least 5 seconds, with no feed); address B was Simon Willison's
  Atom feed. A was previewed, the field was changed to B before A answered,
  and B was previewed.
  - On `main`, nothing showed that A was loading, and Preview stayed
    available. After both answered, A's error, "The URL did not return a
    parsable feed.", was shown under B's address together with B's preview.
  - On the branch, while A loaded, Preview had `aria-disabled="true"`, stayed
    focusable, and the status region said "Loading the preview…"; a second
    Enter sent no request. Editing the address made Preview available and
    removed the message. After both answered, only B's preview was shown,
    with no alert.
- **Popup.** Not checked live: the built-in browser cannot load extensions.
  The popup tests and the extension build cover it.
- Both containers and their volumes were removed.

### Findings

`/code-review` (high) reported 6 findings:

| Finding | Decision |
| --- | --- |
| No test fails when the stale check after a failed token save is removed | Confirmed (c): the mutation passed all 51 Sources tests. Fixed with a test (R1). |
| No test covers keeping a newer preview's loading message after an older token save succeeds | Confirmed (c), a spec clause without a test. Fixed with the same test (R2). |
| After a stale token save, the typed token stays in the page's state | Confirmed (a), minor: if the token form appears again, its field is prefilled. Fixed in the review commit with the user's approval (one line), and tested (T1). |
| The busy guard reads `previewing` from the render, not from a ref | Rejected: React 18 renders between discrete events, so a second click or Enter sees the new state. |
| `filter_image_urls` parses each address twice | Churn (D-023 d). Recorded. |
| The regexes and suffix list are built inside `is_public_url` | Churn (D-023 d). Recorded. |

The spec sub-agent found no missing requirement, no unrequested behavior, no
wrong implementation, and no false claim. It re-ran all 24 named mutations,
and each failed its named tests. It compared `is_public_url` with Node's
WHATWG `new URL()` on 531,873 generated addresses, with and without a base
URL: none was kept by CatchUp while a browser would request this computer or
a local network. It traced every place that stores or shows images (four
writers, all through `filter_image_urls`; one reader, `_serialize_digest`;
one `<img>`). Of its 30 extra mutations, 12 were caught. Survivors and
decisions:

| Mutation | Decision |
| --- | --- |
| X1: drop `is_reserved` | Test gap: `[::7f00:1]` was kept. Row added. |
| X4: allow `%` in names | Test gap: `http://nas.%6cocal/…` (a browser requests `nas.local`) was kept. Row added. |
| X5: refuse only `\@` | Test gap: `http://127.0.0.1\x@cdn.example.com/…` (a browser requests `127.0.0.1`) was kept. Row added. |
| X9: no exact-suffix match | Marginal; row `http://home.arpa/…` added anyway. |
| X14, X16: stale token save | The same as R2 and R1 above. |
| X15: "Save and preview" shows no loading message | Test gap on a spec clause. Assertion added. |
| X17, X18: a failed token save leaves the buttons busy or the message on | Test gap. Assertions added. |
| X19: a successful save and preview leaves Preview busy | Test gap. Assertion added. |
| X22: a failed repeated preview leaves the loading message | Test gap. Assertion added. |
| X25: the popup shows no loading message for the preview after a token save | Test gap on a spec clause. Assertion added. |
| X8, X10, X11, X20 | Marginal (more images dropped, a defensive check, or a wider message reset). Recorded. |
| X23, X24 | Equivalent: no preview can be pending in those views. Recorded. |

It also raised two points for the user, who chose on 2026-11-18:

- `localhost.localdomain`, `.home`, `.corp`, `.intranet`, and `.private`
  hosts were kept. The suffixes `localdomain`, `home`, `corp`, `intranet`,
  and `private` are now refused (spec delta, design D3, D-033, and the
  requirements row updated). `fritz.box` stays a known limit.
- Saving the page while a popup preview loads replaces the loading message
  with the save's own result. The spec wording now says that the loading
  message lasts until the preview answers or another action writes its
  result. No code change.

### Review mutations

Each was applied alone to the review head and restored.

| Id | Mutation | Result |
| --- | --- | --- |
| R1 | remove the stale check after a failed token save | `keeps a newer preview loading when an older token save fails` failed. |
| R2 | `setMessage('X token saved.')` after a stale save | `keeps a newer preview loading when an older token save succeeds` failed. |
| T1 | clear the typed token only on the current path (Droid's code) | `announces the saved token but does not preview an address that changed during the save` failed. |
| X1, X4, X5, X9 | as in the table above | The matching new row failed (1 each). |
| X15 | no loading message for "Save and preview" | `keeps Save and preview focused until the repeated preview answers, then focuses its heading` failed. |
| X17, X18 | a failed token save keeps `previewing`, or keeps the message | `marks the X token field, not the address, when saving the token fails` failed. |
| X19 | no `setPreviewing(false)` at the end of `saveXAndPreview` | Two X token tests failed. |
| X22 | keep the loading message after a failed repeated preview | `focuses the address and shows the error when the token saves but the repeated preview fails` failed. |
| X25 | the popup shows the loading message only with a trigger | `focuses the preview heading after saving the X token and keeps the status line attached` failed. |
| S1–S5 | drop `localdomain`, `intranet`, `private`, `corp`, or `home` | The matching new row failed (1 each). |
