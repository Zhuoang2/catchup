# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (all of "Context", D1–D4, and "Testing"), and the three spec deltas under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail. Then change the code. The seams are named in each task, and they count as agreed:
  - `catchup.net.public_hosts.is_public_url` and `is_public_address`;
  - `parse_feed`, `FetchResponse`, and `image_feed` in `backend/tests/test_discovery.py`;
  - `client`, `connected`, and `save_page` in `backend/tests/test_extension_api.py`;
  - `test_settings`, `TestClient(create_app(...))`, and rows written through `client.app.state.session_factory()` in `backend/tests/test_digest_history.py`;
  - `fetchMock`, `respond`, `preview`, and `page()` in `frontend/src/pages/Sources.test.tsx`;
  - `fetchMock`, `response`, `connect`, `preview`, `captured`, `genericResult`, and `saves` in `extension/src/test/popup.test.ts`.
- **Test rules.**
  - No real network and no real sleeps beyond the short `setTimeout` waits the existing popup tests already use.
  - Hold a request open with a deferred promise: create the promise, keep its `resolve`, and return it from `fetchMock` for that request, as `keeps busy Add focusable…` in `popup.test.ts` does.
  - Change no existing test, except where a task says so.
  - For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring.
  - Small traps: `test_digest_history.py` imports only `event` from `sqlalchemy`, so 2.1 needs `select`. A `media:content` image in `image_feed` needs `medium='image'`. In 4.1, the mock must answer `/api/captures` with 201, as in `keeps one status line attached…`.
- **Environment.**
  - Backend: run commands in `backend/` with `uv run`, without installing new packages.
  - Frontend and extension: use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/`, and again in `extension/`. Both install the locked packages from the local npm cache. If either fails, stop and report. Do not download packages, and do not change `package.json` or `package-lock.json`.
- **Out of scope:**
  - backend files other than `net/public_hosts.py` (new), `net/safe_fetch.py`, `sources/feeds.py`, and `api/digests.py`;
  - frontend files other than `src/pages/Sources.tsx` and its test;
  - extension files other than `src/popup.ts` and its test;
  - migrations, models, stored rows, and dependency versions;
  - Confirm on the Sources page and in the popup.
- **Do not edit** `proposal.md`, `design.md`, the spec deltas, `docs/process/decision-log.md`, or `docs/process/requirements-changes.md`. Claude Code wrote D-033 and the requirements row with the plan.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. One public-address rule, and image candidates with public addresses only (D3)

- [x] 1.1 Write `backend/tests/test_public_hosts.py` with two parametrized tests of `is_public_url` from `catchup.net.public_hosts`. Run them and watch them fail on the missing module.
  - Kept (`True`): `https://cdn.example.com/a.png`, `HTTPS://CDN.Example.COM/a.png`, `http://example.com./a.png`, `http://example.com:8080/a.png`, `https://my_bucket.cdn.example.com/a.png`, `https://xn--fsqu00a.example/a.png`, `http://8.8.8.8/a.png`, `http://[2606:4700:4700::1111]/a.png`, `http://[64:ff9b::808:808]/a.png`.
  - Dropped (`False`):
    - private and special IPv4: `http://192.168.1.1/cam.jpg`, `http://10.0.0.5/a.png`, `http://172.16.0.1/a.png`, `http://127.0.0.1/a.png`, `http://169.254.169.254/a.png`, `http://100.64.0.1/a.png`, `http://0.0.0.0/a.png`, `http://224.0.0.1/a.png`, `http://user@192.168.0.1/a.png`;
    - IPv6: `http://[::1]:9000/i.png`, `http://[::]/a.png`, `http://[fe80::1]/a.png`, `http://[fe80::1%25en0]/a.png`, `http://[fd00::1]/a.png`, `http://[::ffff:192.168.1.1]/a.png`, `http://[64:ff9b::c0a8:101]/a.png`;
    - numeric forms: `http://2130706433/x.png`, `http://0x7f.1/a.png`, `http://127.1/a.png`, `http://0177.0.0.1/a.png`, `http://8.8.8.010/a.png`, `http://example.0x/a.png`;
    - local names: `http://localhost:631/p.png`, `http://LOCALHOST./a.png`, `http://app.localhost/a.png`, `http://printer/p.png`, `http://printer./p.png`, `http://nas.local/p.jpg`, `http://nas.local./p.jpg`, `http://svc.internal/a.png`, `http://router.home.arpa/a.png`, `http://box.lan/a.png`;
    - hosts that are not plain ASCII names: `http://%31%32%37.0.0.1/a.png`, `http://１２７.０.０.１/a.png`, `http://ｌｏｃａｌｈｏｓｔ/a.png`, `http://例子.测试/a.png`, `http://a..b.example/a.png`;
    - backslashes, which browsers read as `/` (design Context, "Backslashes"): `http://192.168.1.1\@cdn.example.com/a.png`, `http://127.0.0.1:631\@cdn.example.com/p.png`;
    - other: `ftp://example.com/a.png`, `http://`, `http://[::1/a.png`, `http://[v1.abc]/a.png`, `https://[object Object]`.

  Verify: both tests fail with an import error.
- [x] 1.2 Create `backend/src/catchup/net/public_hosts.py` as in design D3.
  - Move the address rule from `_public_answers` in `net/safe_fetch.py` into `is_public_address(address)`, with the NAT64 step. `_public_answers` calls it and raises the same `FetchError("blocked_address", …)` when it is false. Keep `NAT64_PREFIX` importable from `safe_fetch` if anything imports it (check with `grep -rn NAT64_PREFIX backend`).
  - Add `is_public_url(url)` with the five steps in D3. Use `split_url` from `catchup.net.urls`. It makes no network call.

  Verify: the tests from 1.1 pass, and `uv run pytest tests/test_safe_fetch.py` passes unchanged.
- [x] 1.3 Write two failing tests that go through `filter_image_urls`:
  - in `backend/tests/test_discovery.py`, `test_entry_images_on_local_addresses_are_dropped`. Use `image_feed` with HTML images `http://192.168.1.1/cam.jpg`, `https://cdn.example.com/chart.png`, `http://2130706433/x.png`, `http://localhost:631/p.png`, `http://printer/p.png`, `http://nas.local/p.jpg`, and `http://192.168.1.1\@cdn.example.com/b.png`, and a `media:content` image `http://[::1]:9000/m.png`. Parse it with `parse_feed(FetchResponse(...))`, and assert that the entry's image URLs are exactly `["https://cdn.example.com/chart.png"]`;
  - in `backend/tests/test_extension_api.py`, `test_capture_drops_images_on_local_addresses`. Call `save_page(client, connected, images=[{"url": "http://[::1]:9000/i.png", "alt": "Local"}, {"url": "https://example.com/photo.png", "alt": "Photo"}])`, and assert that the stored `image_candidates` URLs are exactly `["https://example.com/photo.png"]`.

  Verify: both tests fail on the current `filter_image_urls`.
- [x] 1.4 In `filter_image_urls` (`backend/src/catchup/sources/feeds.py:116-140`), replace the scheme-and-host condition with `not is_public_url(url)`. Keep the other rules.

  Verify:
  - the tests from 1.3 pass, and `uv run pytest` passes in `backend/`;
  - mutations H1–H8 and H10 from design "Testing" each fail the tests named there. Restore the code after each.

## 2. Stored images are filtered when a digest is read (D4)

- [x] 2.1 Write a failing test in `backend/tests/test_digest_history.py`, `test_saved_digest_never_returns_local_images`.
  - In a session, add a `Source`, a `DigestRun`, a `Digest`, a `DigestTopic`, and one `DigestItem` whose `images` is `[{"url": "http://192.168.1.1/cam.jpg", "alt": "Camera"}, {"url": "https://cdn.example/chart.png", "alt": "Chart"}, {"url": "http://printer/p.png", "alt": "Printer"}]`, as `seed_history` does.
  - Assert that `GET /api/digests/{id}` and `GET /api/digests/latest` both return that item's `images` as exactly `[{"url": "https://cdn.example/chart.png", "alt": "Chart"}]`.
  - Assert that the stored `DigestItem.images` still has all three entries.

  Verify: the test fails on the current code.
- [x] 2.2 In `_serialize_digest` (`backend/src/catchup/api/digests.py:75`), return only the entries of `item.images` that are dicts whose `url` is a string passing `is_public_url`, in order.

  Verify: the test from 2.1 passes, and `uv run pytest` passes. Mutation H9 fails it. Restore the code.
- [x] 2.3 In `README.md`, section "Privacy", add after the paragraph about images from source sites: CatchUp never shows an image whose address points at this computer or a local network, such as `192.168.…`, `localhost`, or `printer.local`, and this includes digests saved earlier. It does not look up names, so a public-looking name that points at a local address is not caught; turn images off if that matters.

  Verify: `git diff README.md` shows only this paragraph. If a test checks the README text (`grep -rln "Privacy" backend/tests frontend/src extension/src`), it still passes.

## 3. Sources page: progress, and only the current address's preview (D1)

- [x] 3.1 Write failing tests in `frontend/src/pages/Sources.test.tsx`. Hold each preview with its own deferred promise.
  - `shows loading progress and ignores Preview while a preview loads`. Focus Preview and click it.
    - While the answer is held: Preview has `aria-disabled="true"`, is not `disabled`, and has focus. The status region has the text "Loading the preview…".
    - Click Preview again, and submit the form: `expect(fireEvent.submit(form)).toBe(false)`, which shows that the default submission was prevented. Exactly one `/api/sources/preview` request was made.
    - Resolve it with `preview`. The preview heading is shown, Preview has no `aria-disabled="true"`, and the status region is empty.
  - `shows only the preview of the address in the field`.
    - Preview `https://a.example/` and hold it. Change the field to `https://b.example/`. Preview has no `aria-disabled="true"`, and the status region is empty.
    - Preview it and hold that too. Resolve B with a preview titled "B News" and `feed_url` `https://b.example/feed`. Then resolve A with a preview titled "A News" and `feed_url` `https://a.example/feed`.
    - "B News" is shown and "A News" is not. Click Confirm source, and assert that the `POST /api/sources` body has `feed_url` `https://b.example/feed`.
  - `ignores an error for an earlier address`. Preview A and hold it. Change the field. Resolve A with a 422 `no_feed` error. No alert is shown, the status region is empty, and Preview has no `aria-disabled="true"`.
  - `announces the saved token but does not preview an address that changed during the save`. Reach the X token form as in `asks for a token in place, saves it, and repeats the same preview`. Hold `PUT /api/settings/x`. Click "Save and preview". While it is held, "Save and preview" has `aria-disabled="true"`, and clicking it again sends no second `PUT`. Change the address field. Resolve the `PUT`. The status region has the text "X token saved.", and no further `/api/sources/preview` request was made.
  - `ignores a repeated preview for an address that changed while it loaded`. Reach the X token form the same way. Let the `PUT` succeed, and hold the repeated `/api/sources/preview`. Change the address field. Resolve the held preview with an X preview titled "Writer". No "Source preview" region is shown, the status region is empty, and Preview has no `aria-disabled="true"`.

  Verify: the new tests fail on the current code. The existing tests still pass.
- [x] 3.2 Implement D1 in `frontend/src/pages/Sources.tsx`: `previewing` state, the `previewRequest` counter, `LOADING`, the guards in `previewSource` and `saveXAndPreview`, the address `onChange` change, and `aria-disabled` on Preview and "Save and preview".

  Verify:
  - `npx vitest run src/pages/Sources.test.tsx` passes, including the existing focus and status tests;
  - mutations F1–F8 from design "Testing" each fail the tests named there. Restore the code after each;
  - `npm test -- --run` and `npm run build` pass in `frontend/`.

## 4. Popup: busy Follow, progress, and late previews (D2)

- [x] 4.1 Write failing tests in `extension/src/test/popup.test.ts`. Hold the preview with a deferred promise.
  - `keeps busy Follow focusable, shows progress, and sends one preview`. Focus "Follow this site" and click it.
    - While the preview is held: the button has `aria-disabled="true"`, is not `disabled`, and has focus. The status line has the text "Loading the preview…".
    - Click it again and wait 20 ms. Exactly one `/api/sources/preview` request was made.
    - Resolve it with `preview`. The heading "Example Site" has focus, and the status line is empty.
  - `it.each` over a successful preview and a 422 `no_feed` error: `ignores a preview that answers after the page was saved`.
    - Use `genericResult(captured)`. Click "Follow this site", and hold the preview. Click "Add this page to my next digest". Wait for "Saved. It will be in your next digest.", and check that "Add this page to my next digest" has focus.
    - Resolve the preview. No heading "Example Site" is shown, the status line still says "Saved. It will be in your next digest.", and "Add this page to my next digest" still has focus.
  - `makes Follow available again after a preview error`. Click "Follow this site" and hold the preview; check that the button has `aria-disabled="true"`. Resolve the preview with a 422 `no_feed` error. The status line shows the error, and the same button has no `aria-disabled="true"`.

  Verify: the new tests fail on the current code. The existing tests still pass, including `keeps one status line attached while saving, removing, previewing, and following`.
- [x] 4.2 Implement D2 in `extension/src/popup.ts`: the `views` counter and `show(...)` helper used by `connected()`, `showXTokenPrompt()`, and the preview; `previewSite(trigger?)` with the busy guard, "Loading the preview…", and the view check; Follow passes itself as `trigger`.

  Verify:
  - `npx vitest run src/test/popup.test.ts` passes in `extension/`;
  - mutations P1–P6 from design "Testing" each fail the tests named there. Restore the code after each;
  - `npm test -- --run` and `npm run build` pass in `extension/`.

## 5. Checks and report

- [ ] 5.1 Run the full checks:
  - `uv run pytest` in `backend/` (record the count);
  - `npm test -- --run` and `npm run build` in `frontend/` and in `extension/`, with Node 22.17.1 (record the counts);
  - `DO_NOT_TRACK=1 openspec validate fix-source-preview-and-image-hosts --strict`.

  Do not run `docker build` or `scripts/docker-smoke.sh`: at `--auto medium` the smoke script is refused, and Claude Code runs both at review.

  Write the commands and their real results to `docs/process/test-report-fix-source-preview-and-image-hosts.md`:
  - each new test, and the mutations that it kills;
  - mutations H1–H10, F1–F8, and P1–P6, with their results;
  - the Docker smoke and the live check from design "Testing", listed as not performed (Claude Code runs them at review).

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.
