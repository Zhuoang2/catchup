# Design

## Context

The motivation is in proposal.md ("Why"). The code on `main` at `866be0d`:

- **Sources page** (`frontend/src/pages/Sources.tsx`).
  - `previewSource` (`:169-181`) clears the preview, awaits `POST /api/sources/preview` with the current `url`, and then calls `setPreview` or `setFieldError` with whatever comes back. Nothing marks the wait, and Preview (`:241`) stays a plain submit button, so pressing it, or Enter in the field, starts another request.
  - The address field's `onChange` (`:238`) clears the preview, the field error, and the X token form, but it cannot stop a request that is already running.
  - `saveXAndPreview` (`:183-204`) saves the token with `PUT /api/settings/x`, then previews the `url` captured when it started, sets "X token saved.", and moves focus. It has the same race.
  - `confirmSource` (`:206-219`) posts `preview.feed_url`. So the preview card decides what is saved, not the field.
  - The status region `<p role="status">{message}</p>` (`:258`) is always on the page.
  - The busy pattern exists on the main screen: Generate uses `aria-disabled` (`frontend/src/pages/Home.tsx:267`, `:301`), and `.btn[aria-disabled="true"]` is styled like a disabled button (`frontend/src/styles/components.css:20-21`).
- **Popup** (`extension/src/popup.ts`).
  - `connected()` (`:185-200`) rebuilds the content with a new "Follow this site" or "Follow this account" button each time. `showXTokenPrompt()` (`:298-330`) and the preview (`:288`) also replace the content.
  - `previewSite()` (`:261-296`) has no busy guard. It writes the preview into `content` and focuses its heading whenever the answer arrives.
  - Add, Remove, and the token's Save already use `aria-disabled` and return early when busy (`:202-204`, `:247-249`, `:316-318`). The test `keeps busy Add focusable, ignores another click, and shows a run_active conflict` (`extension/src/test/popup.test.ts:437-460`) is the pattern to follow.
  - `keeps one status line attached while saving, removing, previewing, and following` (`popup.test.ts:80-115`) expects the status line to be empty once the preview is shown.
- **Image candidates.**
  - `filter_image_urls` (`backend/src/catchup/sources/feeds.py:116-140`) is the only filter. It is called for feed entries (`feeds.py:113`), X posts (`sources/x_accounts.py:74`), and pages saved from the browser (`api/extension.py:183`). Candidates are stored in `Item.image_candidates` (`collection.py:154`, `api/sources.py:259`, `x_accounts.py:83`, `api/extension.py:182`).
  - The run passes stored candidates to the summary call (`digest/runner.py:316`). The chosen images are stored in `Item.summary_images` (`runner.py:373`) and copied into `DigestItem.images` when a digest is saved (`runner.py:453`).
  - `_serialize_digest` (`api/digests.py:57`, images at `:75`) is the only reader of `DigestItem.images`. `/api/digests/latest` and `/api/digests/{id}` both use it. The frontend shows those images with `<img src>` (`frontend/src/components/DigestArticle.tsx:43-44`), and nothing else in the frontend loads an image from data.
  - `_public_answers` (`backend/src/catchup/net/safe_fetch.py:95-112`) holds CatchUp's public-address rule for its own fetches: a NAT64 address (`64:ff9b::/96`) is read as its IPv4 address, and anything not global, or private, loopback, link-local, reserved, multicast, or unspecified, is refused. `test_safe_fetch.py:264-275` pins the NAT64 cases.
- **Probes** on 2026-11-17, Python 3.12.13 (the version `uv` uses here; CI and the Docker image use 3.12):
  - `urlsplit(...).hostname` lowercases the host and removes IPv6 brackets. It keeps forms that browsers read as IPv4 numbers as text: `2130706433`, `0x7f.1`, `127.1`, `0177.0.0.1`. It also keeps percent-encoded (`%31%32%37.0.0.1`) and full-width (`１２７.０.０.１`) hosts unchanged, and keeps a trailing dot (`localhost.`). It removes tab characters (`host\t.example` → `host.example`).
  - `ipaddress`: `::ffff:127.0.0.1` is not global and is loopback; `::ffff:8.8.8.8` is global; `100.64.0.1`, `192.0.0.1`, `2001:db8::1`, and `::` are not global. Every NAT64 address (`64:ff9b::/96`) is global but also reserved, because it lies in `::/8`. Without the NAT64 step, every NAT64 address would be refused (fail closed); the step exists so that a NAT64 address of a public IPv4 address is allowed.
  - **Backslashes.** For `http` and `https`, browsers read `\` as `/`, so the host ends there. `urlsplit` does not: for `http://192.168.1.1\@cdn.example.com/a.png` it gives the host `cdn.example.com`, while Node's `new URL()` (the WHATWG parser that browsers use) gives `192.168.1.1` and the path `/@cdn.example.com/a.png`. A feed can carry such an address, also as `&#92;` in HTML.
  - Node 22.17.1 with `npm ci --offline --no-audit --no-fund` installed the extension's locked packages from the local npm cache (120 packages), as it did for `frontend/` on 2026-11-16.

## Goals / Non-Goals

**Goals:**
- A preview answer is shown only for the address the field shows, and the Sources page and the popup show that a preview is loading.
- No image whose address names this computer or a local network is kept, shown, or requested, including images stored before this change.
- One public-address rule for CatchUp's fetches and for image addresses.

**Non-Goals:**
- Visible captions, formula or tiny images, and prompt changes (#65, later).
- A busy state for Confirm. A second Confirm is refused by the server as a duplicate (`api/sources.py:215-217`, message "Already following …" at `:51-53`).
- Cancelling the server's work when an answer is dropped. The server finishes the preview and the result is discarded.
- Rewriting stored rows.
- DNS lookups for image hosts.

## Decisions

### D1. Sources page: one request counter and one busy state

- Add `previewing` state and a `previewRequest` ref (a counter). `LOADING = 'Loading the preview…'`.
- **`previewSource`.** After `event.preventDefault()`, if `previewing`, return. The order matters: returning before `preventDefault()` would let the browser submit the form natively and reload the page. Otherwise take `id = ++previewRequest.current`, set `previewing`, clear the preview and errors as today, and set the message to `LOADING`. When the request settles, do nothing if `id !== previewRequest.current`. Otherwise apply the preview or the error as today, clear the message, and set `previewing` to false.
- **`saveXAndPreview`.** The same guard, after `event.preventDefault()`, and the same `id`, taken before the `PUT`. After each `await`, the code first checks whether `id` is stale:
  - **`PUT` fails.** If `id` is stale, do nothing. Otherwise show the token error as today, clear `LOADING`, and end `previewing`.
  - **`PUT` succeeds, `id` stale.** The token is saved, but the old address is not previewed. Announce it with `setMessage(current => current === LOADING ? current : 'X token saved.')`, so that the loading message of a newer preview stays. Change nothing else: no `setNeedsXToken(false)`, no `setPreviewing(false)`.
  - **`PUT` succeeds, `id` current.** Preview the address.
  - **Preview answers, `id` stale.** Do nothing.
  - **Preview answers, `id` current.** As today: on success set "X token saved." and focus the heading; on failure show the error and focus the address. Then hide the token form and end `previewing`.
  - The current `finally { setNeedsXToken(false) }` must not run for a stale `id`: it would hide a token form that a newer preview has shown.
- **Address `onChange`.** Also increment `previewRequest.current`, set `previewing` to false, and clear the message if it is `LOADING`. The X token form already disappears here (`setNeedsXToken(false)`).
- **Buttons.** Preview and "Save and preview" get `aria-disabled={previewing || undefined}`. They stay enabled `<button>`s, so focus stays on them. Pressing either, or Enter in either form, reaches the guard and does nothing.
- Alternative considered: compare the answer's address with the field (`url === requestedUrl`). Rejected: an address edited and then typed back would accept an answer that the field change had already dropped, and the server may normalize the address. A counter is simpler to reason about.
- Alternative considered: `AbortController`. Rejected for now: `request()` does not take a signal (`frontend/src/api/client.ts:14`), and aborting does not stop the server's work.

### D2. Popup: busy Follow, a progress message, and a view counter

- Add `let views = 0` and a helper `show(...nodes)` that increments `views` and calls `content.replaceChildren(...nodes)`. `connected()`, `showXTokenPrompt()`, and the preview use it. Nothing else replaces `content`; `content.append(remove)` after a save (`popup.ts:237`) adds to the saved-page view and does not count as a new view.
- **`previewSite(trigger?)`.** If `trigger` is `aria-disabled="true"`, return. Set it to `aria-disabled="true"`, remember `view = views`, and set the status line to "Loading the preview…". When the answer settles:
  - if `views !== view`, return without touching the content, the status line, or focus. This includes errors, and a 401;
  - otherwise behave as today: show the preview and clear the status line, or show the error, the token prompt, or the disconnected view.
  - In `finally`, set `trigger` back to `aria-disabled="false"`. If the content was replaced, that button is detached and this does nothing visible.
- The Follow button passes itself as `trigger`. `saveXToken` calls `previewSite()` without one, because its own Save button is already busy.
- Alternative considered: also make Add busy while a preview loads. Rejected: the user may want to save the page while the feed search runs; dropping the late preview is enough.
- Saving the page while a preview loads clears the status line and writes the save's own result there; the loading message is not restored. The spec wording says so (changed at review on 2026-11-18, when the spec review found that "While a preview loads, the status line MUST say …" did not hold in this case).

### D3. One public-address rule, and an image-address check built on it

- **New module `backend/src/catchup/net/public_hosts.py`.**
  - `is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool`: the rule moved out of `_public_answers`. A NAT64 address is read as its IPv4 address. The result is false when the address is not global, or is private, loopback, link-local, reserved, multicast, or unspecified. `_public_answers` raises `blocked_address` when it is false, exactly as today.
  - `is_public_url(url: str) -> bool`, without any network access:
    1. False when the URL contains a backslash (`\`), because browsers read it as `/` in `http` and `https` addresses and may then request another host (Context, "Backslashes"). Then `split_url(url)`; false when it is `None`, the scheme is not `http` or `https`, or there is no `hostname`.
    2. If the host was bracketed (`"[" in parts.netloc`), it is an IPv6 literal: `ipaddress.IPv6Address(host)`, then `is_public_address`. False when it does not parse, which also covers `[v1.abc]`-style hosts, which browsers refuse.
    3. Otherwise remove one trailing dot. The name must match `[a-z0-9_-]+(\.[a-z0-9_-]+)*`, or the result is false. This drops percent-encoded, full-width, and other non-ASCII hosts, and empty labels.
    4. If the last label is a number in a browser's sense (`[0-9]+`, or `0x` followed by zero or more hex digits), the browser reads the whole host as an IPv4 address. Then `ipaddress.IPv4Address(name)` must parse, which needs four plain decimal parts with no leading zeros, and `is_public_address` must be true. Otherwise the result is false.
    5. Otherwise it is a name. It is false when it has no dot, or is `localhost`, `localdomain`, `local`, `internal`, `intranet`, `private`, `corp`, `home`, `home.arpa`, or `lan`, or ends with `.` plus one of them. Otherwise it is true.
- The suffixes `localdomain` (the loopback name many `/etc/hosts` files define, as in `localhost.localdomain`) and `intranet`, `private`, `corp`, and `home` (names RFC 6762, Appendix G, lists as used privately) were added at review on 2026-11-18, after the spec review found them kept.
- **`filter_image_urls`** replaces its scheme-and-host condition (`feeds.py:127`) with `not is_public_url(url)`. The avatar, 1×1, excluded, duplicate, and cap rules stay as they are.
- Why the browser's view matters: the digest page is rendered in the reader's browser, which parses the stored address with the WHATWG URL rules, not with `urllib`. Step 4 follows the WHATWG "ends in a number" rule, so every host a browser would read as an IPv4 number is either a public dotted address or dropped. Public addresses written in other numeric forms are dropped too. They are rare in feeds.
- Alternative considered: normalize hosts the way a browser does (percent-decoding, UTS 46 mapping, the full IPv4 number parser) and then check the result. Rejected: more code that must match browsers exactly, for hosts that real feeds do not use. Refusing anything that is not a plain ASCII name is simpler and fails safe.
- Alternative considered: resolve names during collection. Rejected:
  - the reader's browser may resolve the name differently, and later (DNS rebinding);
  - lookups would add network traffic and delay to every check, where today keeping candidates makes no request.
- Alternative considered: serve images through CatchUp, with `safe_fetch`'s checks. Rejected for this change: it changes the privacy model and needs a new endpoint and caching. It is the only way to catch names that resolve to local addresses (Risks).

### D4. Filter stored images when a digest is read

- `_serialize_digest` returns only the entries of `item.images` that are dicts whose `url` passes `is_public_url`. Order is kept.
- This covers every digest, including the latest digest on the main screen, and digests saved before this change. No migration, and the stored rows are unchanged.
- Candidates stored before this change are still given to the summary call, and a summary may choose one. It is stored with the summary and the digest, and then hidden when the digest is read, so such an item can show fewer images than it chose. This affects only items collected before the update. Alternative considered: also filter at `runner.py:316`. Rejected: the read-time filter is the one that protects the reader, and a second filter adds a seam without changing what is shown.

## Risks / Trade-offs

- **Names that resolve to local addresses are not caught.** Examples: `192.168.1.1.nip.io`, or a public domain with an `A` record for `10.0.0.5`. The browser requests them. Only serving images through CatchUp would catch these (D3). The README says so.
- **Some public images are dropped.** Hosts in IDN form that are not punycode, numeric hosts not written as plain dotted IPv4, and single-label names. They are rare in feeds, and images are optional.
- **Stale previews still cost the server time.** A dropped answer's fetches still run on the server, up to its usual limits.
- **The popup ignores a 401 that arrives after the view changed.** The next action that reaches CatchUp shows the disconnected view.

## Testing

Test-first (D-016). Seams:

- `catchup.net.public_hosts.is_public_url(url)`: a parametrized table. `is_public_address` is covered through that table and through `safe_fetch`'s tests.
- `filter_image_urls`, through a feed entry (`backend/tests/test_discovery.py`) and through `POST /api/captures` (`backend/tests/test_extension_api.py`).
- `safe_fetch`'s existing tests, including NAT64 (`backend/tests/test_safe_fetch.py:264-275`), unchanged.
- `GET /api/digests/{id}` and `GET /api/digests/latest` for a digest whose `DigestItem.images` is written directly (`backend/tests/test_digest_history.py`).
- Sources page: deferred `fetch` promises per request in `frontend/src/pages/Sources.test.tsx`.
- Popup: deferred `fetch` promises in `extension/src/test/popup.test.ts`, following `keeps busy Add focusable…`.

Named mutations, each run alone and restored:

| Id | Mutation | Must fail |
|---|---|---|
| H1 | `is_public_url` returns true for IP literals without calling `is_public_address` | table rows for private IPv4 and IPv6 literals |
| H2 | remove the numeric-last-label step (4) | `0x7f.1` and `127.1` rows |
| H3 | do not remove the trailing dot | `example.com.` kept row |
| H4 | remove the ASCII name check (3) | full-width `１２７.０.０.１` row |
| H5 | remove `local` from the local suffixes | `nas.local` row |
| H6 | allow names without a dot | `printer` row |
| H7 | remove the NAT64 step from `is_public_address` | kept row `http://[64:ff9b::808:808]/a.png` and `test_nat64_embedded_public_address_allowed` |
| H8 | `filter_image_urls` keeps its old scheme-and-host condition | the feed and capture tests |
| H9 | `_serialize_digest` returns `item.images` unfiltered | the saved-digest test |
| H10 | remove the backslash check from step 1 | the two backslash rows |
| F1 | Sources: apply answers without the counter check | address-changed and earlier-error tests |
| F2 | Sources: remove `if (previewing) return` | second request sent while loading |
| F3 | Sources: no `aria-disabled` on Preview | loading test |
| F4 | Sources: no `LOADING` message | loading test |
| F5 | Sources: `onChange` does not increment the counter or end `previewing` | address-changed test |
| F6 | Sources: `saveXAndPreview` previews after a stale `PUT` | X token stale test |
| F7 | Sources: the `previewing` guard returns before `event.preventDefault()` | loading test (`fireEvent.submit` returns false) |
| F8 | Sources: `saveXAndPreview` applies a preview answer without the stale check | X token stale preview test |
| P1 | Popup: remove the busy guard in `previewSite` | Follow pressed twice |
| P2 | Popup: no `aria-disabled` on Follow | Follow pressed twice |
| P3 | Popup: remove the view check | page saved while a preview loads |
| P4 | Popup: no progress message | Follow pressed twice |
| P5 | Popup: `connected()` replaces content without counting a view | page saved while a preview loads |
| P6 | Popup: `finally` does not set `trigger` back to `aria-disabled="false"` | Follow available again after an error |

At review, Claude runs `scripts/docker-smoke.sh` and a live check:
- the Sources page in a browser against a slow local preview;
- a digest whose saved images include a local address, with the network requests the page makes.
