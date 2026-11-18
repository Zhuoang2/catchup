# Proposal

## Why

Two defects came from the system review on 2026-11-01:

- **#73. A slow preview has no progress, and an old answer can replace a new one.**
  - A preview can take a long time: each fetch may take up to 30 s, and a page without a declared feed is probed at up to 8 common locations. The Sources page shows nothing while it waits, and Preview stays enabled (`frontend/src/pages/Sources.tsx:169-181`, `:241`).
  - Each answer is shown as it arrives, whatever the address field holds by then (`Sources.tsx:173`, `:194`). A probe previewed address A, then B. B answered first, then A. The card showed A while the field showed B, and Confirm saved A, because Confirm saves the preview's feed (`Sources.tsx:212`).
  - In the browser extension, "Follow this site" has no progress state and no busy state either (`extension/src/popup.ts:186-187`, `:261-295`). Pressing it twice sends two previews. If the user saves the page while a preview is pending, the late preview replaces the saved-page view and takes focus.
- **#65 (security part, 2026-11-02 comment). Digest images can make the reader's browser request devices on their own network.**
  - `filter_image_urls` checks only that an image has an `http` or `https` address with a host (`backend/src/catchup/sources/feeds.py:116-138`). Images such as `http://192.168.1.1/…`, `http://localhost:631/…`, and `http://[::1]:9000/…` are kept as candidates. If a summary chooses one, the digest shows it, and the reader's browser requests that address (`frontend/src/components/DigestArticle.tsx:43-44`).
  - The same filter is used for X posts (`sources/x_accounts.py:74`) and for pages saved from the browser (`api/extension.py:183`).
  - Images that were stored before a fix stay in the database. They are candidates of pending items, summary choices reused with a summary, and the images of saved digests. Saved digests are served by one function, `_serialize_digest` (`api/digests.py:57`, images at `:75`), used by both `/api/digests/latest` and `/api/digests/{id}`.

The rest of #65 (visible captions, formula images, the prompt) waits for the user's own source test (#14) and stays open.

## What Changes

- **Sources page: progress while a preview loads.** While a preview loads, Preview stays focusable but is announced as unavailable, and pressing it (or Enter in the field) does nothing. The status region says "Loading the preview…". "Save and preview" in the X token form works the same way.
- **Sources page: only the current address's answer is shown.** Editing the address drops the pending preview and makes Preview available again. A preview or error that arrives for an address no longer in the field is ignored, so Confirm can only save the address the field shows.
- **Popup: progress while a preview loads.** While "Follow this site" or "Follow this account" is working, the button stays focusable but is announced as unavailable, pressing it again does nothing, and the status line says "Loading the preview…". If the popup's content changed before the answer arrived, the answer is ignored.
- **Image addresses must be public.** CatchUp drops an image candidate when its address names this computer or a local network:
  - IP addresses that are not public, by the rule that already guards CatchUp's own fetches;
  - numeric host forms that browsers read as IPv4 addresses, such as `2130706433`, `0x7f.1`, and `127.1`, unless they are a public address in plain dotted form;
  - `localhost` and names under it, names without a dot, and names under `.localdomain`, `.local`, `.internal`, `.intranet`, `.private`, `.corp`, `.home`, `.home.arpa`, and `.lan`;
  - hosts that are not plain ASCII names, such as percent-encoded or full-width forms that a browser would turn into one of the above;
  - addresses with a backslash, which browsers read as `/`: `http://192.168.1.1\@cdn.example.com/a.png` looks like a `cdn.example.com` address, but a browser requests it from `192.168.1.1`.

  CatchUp does not look up names. A public-looking name that resolves to a local address is not detected (design, Risks).
- **Stored images are filtered when a digest is read.** Saved digests never show an image whose address fails the same rule, including digests saved before this change. Nothing in the database is rewritten.
- No API shape, data model, or migration change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `content-collection`: "Keep image candidates for items" also leaves out images whose address is not public, for every kind of item that keeps image candidates, with scenarios for a private IP, a numeric host form, and a local name.
- `user-interface`: "Show chosen images from their source sites" never shows or requests an image whose address is not public, including in digests saved earlier. A new requirement, "Show preview progress, and only the current address's preview", covers the Sources page.
- `browser-extension`: "Keep focus and announcements in the popup" adds "Follow this site" and "Follow this account" to the busy buttons, a progress message, and ignoring an answer after the content changed.

## Impact

- Code:
  - `backend/src/catchup/net/safe_fetch.py`: the public-address rule moves into a function both callers use, with no change to fetch behavior;
  - a new `backend/src/catchup/net/public_hosts.py` with the image-address check;
  - `backend/src/catchup/sources/feeds.py` (`filter_image_urls`) and `backend/src/catchup/api/digests.py` (`_serialize_digest`);
  - `frontend/src/pages/Sources.tsx`;
  - `extension/src/popup.ts`.
- Tests: `backend/tests/test_public_hosts.py` (new), `test_discovery.py`, `test_digest_history.py`, `test_extension_api.py`, `test_safe_fetch.py`; `frontend/src/pages/Sources.test.tsx`; `extension/src/test/popup.test.ts`.
- Docs: decision log (D-033), requirements-changes table, a test report, the AI usage log.
- Out of scope:
  - the rest of #65 (captions, formula and tiny images, the prompt);
  - a busy state for Confirm on the Sources page and in the popup (a repeated Confirm is refused by the server as a duplicate);
  - rewriting stored rows;
  - DNS lookups for image hosts.
