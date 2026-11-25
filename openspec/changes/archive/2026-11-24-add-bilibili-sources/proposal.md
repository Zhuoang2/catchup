# Proposal

## Why

The user asked on 2026-10-17 whether CatchUp can follow Bilibili uploaders, and #40 records the request. Bilibili publishes no feeds, and its user agreement forbids getting its content with automated programs (section 5.6(3), 2025-04-30). Open-source tools that list an uploader's videos use Bilibili's signed web API, and Bilibili's lawyers acted against public documentation of that API in January 2026 (research.md).

On 2026-11-22 the user chose Proposal 1 of `design.md`: CatchUp reads uploaders through an RSSHub that the user runs, and CatchUp itself never contacts Bilibili.

## What Changes

- **A new source kind, "Bilibili uploader" (`bilibili`).** The user pastes `https://space.bilibili.com/<mid>` on the Sources page, or uses "Follow this site" on that page in the extension.
  - CatchUp reads the uploader through RSSHub's route `/bilibili/user/video/<mid>`, as JSON Feed.
  - It saves the source under the stable address `bilibili:uploader:<mid>`, so a new RSSHub address keeps it.
  - Pasting the configured RSSHub's own address for that route works too.
  - Video pages, `b23.tv` short links and other Bilibili pages are refused with a message that asks for the space address.
- **The RSSHub address is an environment setting,** `CATCHUP_RSSHUB_URL`. When it is empty, Bilibili addresses are refused with a message that points to the README.
  - The configured RSSHub origin may be a private or loopback address. That is the only exception to the private-address rule. It does not apply to redirects, other ports, or other private addresses.
- **CatchUp never requests a Bilibili host** (`bilibili.com`, `b23.tv`, `hdslb.com`, `bilivideo.com`, with subdomains): not as a feed, linked page, article page, or redirect target, for any source.
- **Videos are summarized only from subtitles,** as D-013 requires for videos.
  - CatchUp reads the subtitle attachments that RSSHub adds to its JSON Feed (`data:` URLs with SRT text). It decodes them locally and never fetches an attachment address.
  - RSSHub gets subtitles from Bilibili only with the user's own logged-in cookie, configured in RSSHub. CatchUp never asks for or stores that cookie.
  - A video without subtitles waits up to `CATCHUP_CAPTION_WAIT_HOURS` (24 hours), and is checked again on each run. It then goes to Creator updates with the new reason "no subtitles from RSSHub".
  - Bilibili items get no linked pages and no image candidates.
- **An optional Compose override, `compose.rsshub.yaml`,** runs RSSHub next to CatchUp and sets `CATCHUP_RSSHUB_URL`. The default `compose.yaml` does not change.
- **README** gets a "Bilibili uploaders" section: how to run RSSHub, the address setting, the subtitle cookie, public instances, and Bilibili's terms.
- **The Sources page, Home and the extension popup** name the new kind. They show the uploader's space address instead of the internal feed address.

## Capabilities

### New Capabilities

- `bilibili-uploaders`:
  - recognizing uploader addresses, and refusing other Bilibili addresses;
  - the RSSHub address and its private-address exception;
  - preview and confirm through RSSHub;
  - reading new videos on each run, and subtitles;
  - waiting for subtitles and the Creator updates reason;
  - never requesting a Bilibili host;
  - how the Sources page and the extension show the kind.

### Modified Capabilities

- `source-management`:
  - "Preview a source from a pasted URL": Bilibili addresses are previewed through RSSHub;
  - "Fetch user-supplied URLs safely": the exception for the configured RSSHub origin.
- `transcripts`:
  - "Recognize podcast and YouTube sources": a sixth kind that is never reclassified;
  - "Record why a transcript is unavailable": the reason "no subtitles from RSSHub".
- `digest-generation`:
  - "Creator updates": the new reason.
- `user-interface`:
  - "Sources show their kind and confirm deletion inline": the new kind name, and the space address in place of a feed address.
- `local-deployment`:
  - a new requirement for the optional RSSHub Compose override.

## Impact

- **Backend:**
  - new `sources/bilibili.py` and `net/bilibili_hosts.py`;
  - `config.py`, `net/safe_fetch.py`, `context/links.py`, `sources/feeds.py` (one optional field on `FeedEntry` and `Feed`), `collection.py`, `api/sources.py`, `digest/runner.py`;
  - no new dependency and no migration: `sources.kind` is free text, and the RSSHub address is an environment setting.
- **Frontend:** `components/ui.tsx`, `components/Icon.tsx`, `pages/Sources.tsx`, `pages/Home.tsx`.
- **Extension:** `src/popup.ts`.
- **Deployment and docs:** new `compose.rsshub.yaml`; `.env.example`, `README.md`.
- **Process:** D-038 in `docs/process/decision-log.md`; a row in `docs/process/requirements-changes.md`.
- **Not touched:** `api/settings.py` and `pages/Settings.tsx` (#12 changes them), `models.py`, the context pass, the extension's extractors.
- **Risk outside the code:** the user's RSSHub still makes the automated requests that Bilibili's agreement forbids. The README states it.
