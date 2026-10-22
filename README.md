# CatchUp

CatchUp is a self-hosted, on-demand personal digest. Configure an
OpenAI-compatible model (DeepSeek is tested), then add the sites and feeds you
follow. The main screen, Latest, shows your newest saved digest and a Generate
digest button. CatchUp collects what is new since each source's last successful
check and writes a topic-grouped digest with links to the originals. Older
digests stay available in History.

The project is under active development. Requirements live in
`openspec/specs/`; completed changes are in `openspec/changes/archive/`.

## Development setup

Install Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and Node.js
20.19+ or 22.12+ (as required by Vite 8). From the repository root, first
enable the pre-commit hook, which blocks commits whose staged lines look like
API keys or secrets:

```sh
git config core.hooksPath "$PWD/.githooks"
```

Git does not clone this setting, so run it once per clone. It applies to every
worktree of that clone, including worktrees on branches created before the
hook was added. Then create the environment file:

```sh
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Paste the generated value into `CATCHUP_SECRET_KEY` in `.env`. Do not commit
that file. In separate terminals, run:

```sh
cd backend
uv sync
set -a; . ../.env; set +a
uv run uvicorn catchup.main:app --reload
```

Alternatively, start the backend with `uv run catchup serve` from `backend/`
after loading the same environment. This listens on `127.0.0.1:8000` by
default; use `uv run catchup serve --help` for host and port options.

```sh
cd frontend
npm ci
npm run dev
```

Open the Vite address shown in the terminal. It proxies `/api` to the backend
at `http://127.0.0.1:8000`. To serve the built frontend from FastAPI instead,
run `npm run build` from `frontend/` and open `http://127.0.0.1:8000`.
The backend creates and migrates `CATCHUP_DATA_DIR/catchup.sqlite3` at startup.
By default, the backend accepts requests only for `localhost`, `127.0.0.1`,
and `[::1]` (with or without a port). If you deploy behind a domain, set
`CATCHUP_ALLOWED_HOSTS` to a comma-separated list that includes that domain,
for example `localhost,127.0.0.1,[::1],catchup.example.org`. Do not add
untrusted domains or `*`. Changing a model provider URL requires entering
the API key again; CatchUp will not send a stored key to a new address.
From their respective directories, run backend tests with `uv run pytest`
and frontend tests/build with `npm test -- --run` and `npm run build`.
Tests require neither a network connection nor a real model key.

## Install as an app

Start CatchUp first, then open it in Chrome or Edge on macOS and use the
browser's **Install** action in the address bar or menu. In Safari, use
**File → Add to Dock**. Open the installed app while the server is running.
`localhost` and `127.0.0.1` are separate origins, so installing from each
address creates a separate app with separate browser state.

If the server is unavailable, navigation shows an offline page with commands
to start CatchUp and a Reload button. Digests and settings are not cached
for offline use. To remove the service worker, open your browser's DevTools,
go to Application (or Storage) → Service Workers, select CatchUp's origin,
and choose **Unregister**. Reload the page afterwards. Unregister separately
for `localhost` and `127.0.0.1` if you have used both.

## Browser extension

The optional Chrome and Edge extension lets you **Follow this site** when it
has a supported feed, or **Add this page to my next digest** without a feed.
Saved pages wait for your next manual digest run; the extension does not start
one. This extension is separate from the installable web app above.

Start the local CatchUp server, then build and load the extension:

```sh
cd extension
npm ci
npm test -- --run
npm run build
```

In Chrome, open `chrome://extensions`, turn on **Developer mode**, choose
**Load unpacked**, and select this repository's `extension/dist` folder.
Chrome 134 and later require Developer mode to keep unpacked extensions
enabled. In Edge, open `edge://extensions`, turn on Developer mode, and
use **Load unpacked** on the same folder. Rebuild and reload the unpacked
extension after updating it.

In CatchUp, go to **Settings → Browser extension** and create a connection.
Copy its one-time token to the extension's **Options** page along with the
local server address (default `http://127.0.0.1:8000`). The options page
stores both in `chrome.storage.local` and can test the connection. Keep the
token private. To revoke access, disconnect the browser in CatchUp Settings.
The extension accepts only `127.0.0.1` or `localhost` with an HTTP port; it
cannot connect to a server on a remote host.

The extension requests `activeTab` and `scripting` to read the current page's
visible DOM **only when you press Add** in the popup. It collects the title,
main text, selected metadata, images, and links; on a matching X post it can
also capture visible replies by its author. Following a site sends the
current tab's URL to CatchUp for feed preview, then follows the feed only
after confirmation. `storage` keeps the local address and connection token.
The only `host_permissions` are for `http://127.0.0.1/*` and
`http://localhost/*`; they let the popup contact your local CatchUp API.
The extension never runs a background worker or content script, reads pages
automatically, follows an X account, schedules digest generation, or sends
the page to any other server. CatchUp may send saved page content to your
configured model provider during a later digest run.

It never reads cookies, saved passwords, or site storage. It does no
background reading and does not scroll, click, or open pages on your behalf.
Generic page extraction uses Mozilla Readability 0.6.0 (Apache-2.0); its
license is bundled in `extension/dist/readability-LICENSE.md`.

In the next digest run, the CatchUp server reads up to
`CATCHUP_LINKS_PER_ITEM` links recorded on each saved page, as it does for
website items. It requests them itself, without your cookies. A link that
carries a private token, such as an email-confirmation or unsubscribe link,
may act when it is requested, so do not save pages that show such links.

Known limits:

- A page saved while a digest run is in its context pass may be summarized
  in that run without linked context. This short window can produce a
  summary without links.
- On a short page beside a longer sponsor block, the saved text can include
  the sponsor text, or hold only that text.

**X's terms prohibit scraping in any form.** Saving an X page is at your
own risk and only reads what your browser currently displays after you press
Add. CatchUp does not follow X accounts or log in on your behalf.

## Privacy

Collected content is sent to the configured model provider. Self-hosting
does not keep that content local if you choose a cloud provider.

Chosen digest images load directly from their source sites when a digest is
shown, including the latest digest on the home page. This contacts those
sites with your IP address but sends no referrer. In Settings → Digest,
**Show images from source sites** is on by default; turn it off to prevent
these image requests. If CatchUp cannot read that setting, images are shown.

## Run with Docker

Install Docker with Compose **2.24 or newer**. No local Python, uv, or Node
installation is needed. From a directory containing `compose.yaml`, generate
an instance secret in a private `.env` file:

```sh
printf 'CATCHUP_SECRET_KEY=%s\n' "$(openssl rand -hex 32)" > .env
```

Do not commit or share `.env`. Keep this secret across upgrades and backups,
or previously saved model credentials cannot be decrypted. Compose pins
`CATCHUP_DATA_DIR=/data` and `CATCHUP_FRONTEND_DIST=/app/frontend`, even if
`.env` contains values intended for development.

The `latest` tag is the newest release, available after the first `vX.Y.Z`
release tag. The `edge` tag tracks `main`; `X.Y.Z` pins a specific release.
Until the first release, build from this checkout, or change the image in
`compose.yaml` to `ghcr.io/zhuoang2/catchup:edge` after it is published.
Start from the published image when available, or build from this checkout:

```sh
docker compose up -d
# Instead, to build from source:
docker compose up -d --build
```

Open `http://localhost:8000`. The API and web interface share this port.
If using only Docker rather than Compose, the equivalent command is:

```sh
docker run -d --name catchup --env-file .env -e CATCHUP_DATA_DIR=/data \
  -p 127.0.0.1:8000:8000 -v catchup-data:/data \
  ghcr.io/zhuoang2/catchup:latest
```

The provided Compose file binds **only to `127.0.0.1`**. CatchUp has **no
login**: anyone who can access an exposed instance can read data and change
settings. Do not expose it to an untrusted network. If you deliberately
expose it, change the loopback address in `compose.yaml`, set
`CATCHUP_ALLOWED_HOSTS` to include your intended domain **and** `localhost`
and `127.0.0.1` (for the container health check), for example
`CATCHUP_ALLOWED_HOSTS=localhost,127.0.0.1,catchup.example.com`. Do not use
`*`. CatchUp accepts requests that change data only from its own pages or
tools that send no browser origin headers. A page on another site, or on
another local port, is refused. A proxy in front of CatchUp must pass the
browser's `Host` header, including its port (in nginx, `$http_host`, not
`$host`). Provide your own access control and TLS. Collected
content is sent to the configured model provider, even when CatchUp itself
runs locally.

To upgrade the published image without deleting the volume:

```sh
docker compose pull && docker compose up -d
```

For a source-built service, use `docker compose up -d --build` instead.
The named `catchup-data` volume survives container replacement; migrations
run automatically before the server accepts requests. For a consistent backup
or restore, stop the service first. The commands below find Compose's actual
volume name (which includes the project name) and use the locally running
image, so they also work with a source-built image:

```sh
docker compose stop catchup
container="$(docker compose ps -aq catchup)"
volume="$(docker inspect "$container" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
image="$(docker inspect "$container" --format '{{.Image}}')"
docker run --rm --network none -v "$volume:/data:ro" --entrypoint python "$image" \
  -c 'import sys, tarfile; t = tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"); t.add("/data", arcname="."); t.close()' \
  > catchup-data.tar.gz
# To restore this backup to the stopped service's data volume:
docker run --rm --network none -i -v "$volume:/data" --entrypoint python "$image" \
  -c 'import sys, tarfile; tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz").extractall("/data", filter="data")' \
  < catchup-data.tar.gz
docker compose up -d
```

Back up `.env` separately and securely. Restoring replaces files in the
volume; restore only into an empty volume or remove its old contents first
after making another backup. A bind mount in place of the named volume must
be writable by UID **999** (the non-root container user). To move an existing
source-checkout database, stop the service and copy its `catchup.sqlite3`
into the volume before starting it; keep the same instance secret if it
contains an encrypted model key.

## Supported sources

CatchUp supports RSS/Atom feeds, including sites that declare a feed or
expose one at a common path. Examples include blogs, Bluesky and Mastodon
profiles, and Reddit subreddits (availability can depend on the host network).
Podcast feeds are recognized when most entries have audio enclosures. A
podcast episode is summarized **only** when the feed publishes an accessible
`<podcast:transcript>` (plain text, VTT, SRT, JSON or HTML). CatchUp also
accepts Apple Podcasts show and episode URLs, resolving them to the show's
RSS feed. Episodes without a transcript wait for
`CATCHUP_TRANSCRIPT_WAIT_DAYS` (default 7) before they appear without a
summary in **Creator updates**, grouped by show. Text-only posts in a podcast
feed still use their article text.

YouTube channel feeds are supported. **Fetch captions locally** is off by
default; when off, videos appear in Creator updates without summaries.
Enabling it fetches captions from YouTube from this computer. **YouTube's
Terms of Service do not allow automated access. Turn this on only if you
accept that risk.** CatchUp requests original-language captions, prefers
manual tracks over auto-generated ones, and never translates or downloads
audio/video. Videos with no captions yet wait for `CATCHUP_CAPTION_WAIT_HOURS`
(default 24) before appearing in Creator updates. Requests are spaced and
limited to `CATCHUP_CAPTIONS_PER_RUN` (default 20); deferred videos stay
pending. Shorts are skipped by default, unless you switch off Skip Shorts
in Settings. Creator updates show a reason for missing transcripts or captions
without sending show notes or descriptions to the model.

For website items, CatchUp reads related links and author replies from public pages
only. Context fetches honor each site's robots.txt.
`CATCHUP_LINKS_PER_ITEM` (default 8) limits linked pages per item.
`CATCHUP_CONTEXT_FETCHES_PER_RUN` (default 60) limits requests per run
(including robots.txt).
Set `CATCHUP_AUTHOR_REPLIES` (default on) to `0`, `false`, or `no` to turn off
author-reply fetching. Pages that cannot be read are skipped without failing
the digest.

Feed documents may be up to `CATCHUP_MAX_FEED_BYTES` (default 33554432,
32 MiB). Articles and transcripts remain limited to 5 MiB. Text longer
than a model call's budget is summarized in parts and combined; if a small
local model does not report its context window, set
`CATCHUP_SINGLE_CALL_CHARS` to a positive budget that fits the model.
`CATCHUP_LONG_ITEM_CHARS` (default 20000) sets when transcript summaries
include an overview and key points. **Configuration change:**
`CATCHUP_MAX_ITEM_CHARS` has been removed; use
`CATCHUP_SINGLE_CALL_CHARS` instead. The old variable is ignored with a
startup warning. Model token totals are shown when the provider reports them.

Reddit support ends on **2026-11-13** because Reddit is
[discontinuing RSS feeds](https://techcrunch.com/2026/09/30/reddit-is-killing-rss-feeds-ending-public-api-access-because-of-ai-bots/).
Source requests identify the client as
`CatchUp/<version> (+https://github.com/Zhuoang2/catchup)`. Optionally set
`CATCHUP_USER_AGENT_CONTACT` to append a contact inside the parentheses,
for example `CatchUp/0.1.0 (+https://github.com/Zhuoang2/catchup; by /u/example)`.
The contact must be printable ASCII, no longer than 100 characters.
Following X accounts, automatically collecting pages without feeds, and
fetching content behind a login or paywall are not supported. You can save
an individual page through the optional browser extension. CatchUp does not
transcribe audio or summarize video visuals.

## License

CatchUp is released under the [MIT License](LICENSE).
