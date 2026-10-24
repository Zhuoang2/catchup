# Proposal

## Why

Users want to follow X (Twitter) creators, so that each digest run picks up those accounts' new posts. Today CatchUp cannot follow X accounts (#41). The browser extension can only save one post at a time, which has little value, because the user can read that post directly. Reading X without its API is against X's terms, and scripting the site risks the user's account (D-024).

The user decided (2026-10-22) that CatchUp follows X accounts through the official X API, with the user's own credentials, asked for when they first follow an account. On 2026-10-24 they chose Proposal 1: an app-only Bearer token, pasted once.

## What Changes

- **A new source kind, "X account" (`x`).** The user pastes `https://x.com/<username>` on the Sources page, or uses "Follow this account" on an X profile in the extension.
  - CatchUp looks the account up through the X API, shows a preview, and follows it on confirm.
  - It never requests x.com pages.
- **The X API token.** The user's own app-only Bearer token is stored encrypted, like the model key.
  - It is asked for in place, the first time an X account is followed, on the Sources page or in the extension.
  - It is managed in a new Settings group, "X accounts": save, replace, remove, test.
  - The extension may save the token only when none is saved.
- **Each digest run reads each followed account's new posts** since the last read, through the API.
  - Retweets and replies to other people are left out.
  - The author's replies in their own thread, when the thread's first post is in the same run, are kept as that post's author replies.
- **A per-run read limit,** `CATCHUP_X_READS_PER_RUN` (default 200 posts, about $1). Posts that do not fit wait for the next run, and the run reports how many X posts it read and how many accounts have posts waiting.
- **After an X post is delivered** in a digest, its stored text and replies are cleared. The digest keeps its summary, title, and link.
- **X API errors are reported in the source's status:** rate limits, a rejected token, a missing or protected account.
- **README** replaces "CatchUp does not follow X accounts" with how to get a token, how to set a spending limit in the X console, and X's policy points.

## Capabilities

### New Capabilities

- `x-accounts`:
  - recognizing X account addresses;
  - preview and confirm through the X API;
  - reading new posts on each run, with threads;
  - the per-run read limit and waiting posts;
  - X API errors;
  - clearing delivered posts' text.

### Modified Capabilities

- `source-management`: the preview names a fifth kind, "X account", and explains X-specific reasons (a token is needed or was rejected; an account not found, protected, or not an account).
- `content-collection`: an X account left for the next run by the read limit is checked as `deferred` (shown as "Waits for the next run"), not as a failure or "no new items". Context for X posts follows the rules for pages saved from the browser.
- `model-settings`:
  - the stored X token is protected like the model key;
  - the extension token gains one operation: saving the X token when none is saved.
- `browser-extension`: on an X profile or post page, the popup offers "Follow this account" with "Add this page", and asks for the X token when none is saved. It still never contacts X itself. On other X pages, it offers only "Add this page".
- `user-interface`:
  - Settings gains an "X accounts" group;
  - kind names gain "X account";
  - the Sources page asks for the token in place;
  - the run result shows X posts read, and accounts waiting.
- `transcripts`: the list of kinds gains "X account", which is never classified.
- `digest-generation`: X posts are summarized like website items, under "X · <name>", with their links and author replies.

## Impact

- **Backend.**
  - Migration `0007`: the `x_credentials` and `x_accounts` tables, and two new run counters.
  - A new X API client module.
  - Settings routes for the token.
  - X branches in source preview and confirm, in the source check, and in the context pass.
  - The run's check-rewrite step leaves "waiting" checks alone.
  - Delivery clears X posts' text.
  - The extension token's allow-list gains one operation.
- **Frontend:** the Settings "X accounts" group; the Sources inline token prompt, error wording, and kind label and icon; the Home run result, rail, and check labels.
- **Extension:** X profile detection, "Follow this account", the token prompt, and the error wording.
- **Docs:** README, decision D-025, a requirements-changes row, and the AI usage log.
- **No new dependencies.** The X API is called with `httpx`, which is already a dependency.
- **Cost.** X API reads are billed to the user's own X developer account. CatchUp caps reads per run, and README tells the user to set a spending limit in the X console.
