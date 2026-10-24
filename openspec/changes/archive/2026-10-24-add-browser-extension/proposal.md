# Proposal

## Why

CatchUp's server can only read public feeds and pages, by design (`net/safe_fetch.py` sends no cookies). Two things that users want are therefore missing:
- **Adding the site they are reading takes several steps.** They copy the address into the Sources page.
- **Content behind a login cannot be read at all.** This includes an X post with the author's own replies (F5, F8, #41).

On 2026-10-20 the user chose "click to capture" (design Proposal 1) for issue #58. On 2026-10-21 they set the details:
- Chrome and Edge first;
- a popup;
- connecting by copying a token from Settings;
- X supported, reading only the author's own replies.

The prerequisite, refusing cross-site writes (#59, D-022), is merged.

## What Changes

- **A browser extension** for Chrome and Edge (Manifest V3), in a new `extension/` folder. Its popup acts on the current tab:
  - **Follow this site** previews and saves the tab's site through the existing preview and confirm API, with the Sources page's messages.
  - **Add this page to my next digest** reads the page as it is rendered at that moment: address, title, site name, author, time, main text, images, links, and, on an X post, the author's own visible replies. The page waits for the next digest run the user starts, and a waiting page can be removed.
  - **Open CatchUp.**
- **What the extension never does.**
  - It reads a page only after the user's click (`activeTab` + `scripting`).
  - It never reads cookies, passwords, or site storage.
  - It never scrolls, clicks, or opens pages by itself.
  - It asks for no site access except `http://127.0.0.1` and `http://localhost`.
- **Connecting a browser.** In Settings → Browser extension, "Connect a browser" shows a token once, to paste into the extension. Connected browsers are listed with their last use, and "Disconnect" revokes the token.
- **The cross-site rule (D-022) gains one exception.** A request with a valid token is accepted on the extension's operations only. An invalid or revoked token is refused.
- **Saved pages in the pipeline.**
  - They live under one built-in source, "Saved from browser", of a new fourth kind. It is never checked as a feed.
  - At the next run they are summarized like website items, and shown under the page's own site name, for example "X · Simon Willison".
  - Their context comes from the links they recorded, under today's rules, and from the captured author replies. The server never fetches the saved page itself.
- **Migration `0006_captures`.** It adds the token table, plus two nullable item columns: the site name, and the captured replies.
- **Docs:**
  - README: install the extension, connect it, what it reads and when, and X's terms risk;
  - decision D-024.

## Capabilities

### New Capabilities
- `browser-extension`:
  - connecting a browser;
  - following the current site;
  - adding the current page to the next digest;
  - X posts with the author's replies;
  - what the extension never does;
  - installing it from the repository.

### Modified Capabilities
- `model-settings`: "Refuse write requests from other sites" accepts a valid connection token on the extension's operations.
- `content-collection`:
  - "Check every source on each run" leaves out the built-in source;
  - an ADDED requirement covers context for pages saved from the browser.
- `source-management`: an ADDED requirement for the built-in "Saved from browser" source.
- `transcripts`: "Recognize podcast and YouTube sources" gains the fourth kind, which is never classified.
- `user-interface`:
  - "Sources show their kind and confirm deletion inline" gains the fourth kind, and the number waiting;
  - an ADDED requirement for the Settings group.
- `digest-generation`: an ADDED requirement for summarizing saved pages under their site name.

## Impact

- **A new package:** `extension/` (TypeScript, Vite, vitest), with its own CI job. It is not part of the Docker image, because `.dockerignore` lists only `backend/` and `frontend/`.
- **Backend:**
  - `main.py` (the token exception);
  - `models.py`;
  - `migrations/versions/0006_captures.py`;
  - new `api/extension.py` (tokens, status, captures);
  - `api/sources.py` (the waiting count);
  - `digest/runner.py` (checks, pending selection, the site name);
  - `context/gather.py` (captured pages);
  - `sources/feeds.py` (a shared image-URL filter).
- **Frontend:**
  - `components/ui.tsx` (the kind);
  - `pages/Sources.tsx` (the row);
  - `pages/Settings.tsx` (the group);
  - `pages/Home.tsx` (the source count);
  - `components/DigestArticle.tsx` (the kind icon).
- **Docs:** `README.md`, and `docs/process/`.
- **Not changed:** feed collection, discovery, summaries' prompts, and the Docker image's contents.
