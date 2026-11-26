# CatchUp

CatchUp is a self-hosted, on-demand personal digest. Configure an
OpenAI-compatible model (DeepSeek is tested) or Anthropic, then add the sites and feeds you
follow. The main screen, Latest, shows your newest saved digest and a Generate
digest button. CatchUp collects what is new since each source's last successful
check and writes a topic-grouped digest with links to the originals. Older
digests stay available in History.

The project is under active development. Requirements live in
`openspec/specs/`; completed changes are in `openspec/changes/archive/`.

## Development setup

Install git, [uv](https://docs.astral.sh/uv/), and Node.js 22.12 or newer
from [nodejs.org](https://nodejs.org) or a version manager. Distribution
packages can be older than this Node.js version. CI and the Docker image use
Node.js 24. Python 3.12 or newer is supported; uv installs and uses Python
3.12 for the backend, as `backend/.python-version` specifies, so you do not
need to install it yourself.

Only the frontend tests need a separate Python: they run `python3` from
`PATH` (any Python 3). Secret generation needs `openssl`, included with
macOS and most Linux installs. On Debian or Ubuntu, install these tools:
`sudo apt update && sudo apt install git curl ca-certificates openssl python3`.

Clone the repository:

```sh
git clone https://github.com/Zhuoang2/catchup
cd catchup
```

From the repository root, first enable the pre-commit hook, which blocks
commits whose staged lines look like API keys or secrets:

```sh
git config core.hooksPath "$PWD/.githooks"
```

Git does not clone this setting, so run it once per clone. It applies to every
worktree of that clone, including worktrees on branches created before the
hook was added. Then create the environment file:

```sh
(
  [ -f .env.example ] || { echo 'Run this from the repository root.' >&2; exit 1; }
  umask 077; set -C
  key="$(openssl rand -hex 32)" &&
  { grep -v '^CATCHUP_SECRET_KEY=' .env.example; printf 'CATCHUP_SECRET_KEY=%s\n' "$key"; } > .env
)
```

These commands write the secret without showing it. They stop without
writing if generation fails, and refuse to overwrite an existing `.env`.
Keep that file, or move it away deliberately before creating a new one:
a new secret makes saved model keys unreadable. Do not commit `.env`.
Build the frontend before starting the backend:

```sh
cd frontend
npm ci
npm run build
```

Then, in another terminal starting from the repository root:

```sh
cd backend
uv sync
set -a; . ../.env; set +a
uv run catchup serve
```

Open `http://127.0.0.1:8000`. The backend serves `frontend/dist` only if it
existed when the backend started; restart the backend after a later build.
Use `uv run catchup serve --help` for host and port options, or
`uv run uvicorn catchup.main:app --reload` for backend development after
loading the same environment.

The health address is `http://127.0.0.1:8000/api/health`, which answers
`{"status":"ok"}`.

For frontend development, use the Vite dev server instead, in a separate
terminal starting from the repository root:

```sh
cd frontend
npm run dev
```

Open the Vite address shown in the terminal. It proxies `/api` to the backend
at `http://127.0.0.1:8000`.
The backend creates and migrates `backend/data/catchup.sqlite3` by default
at startup (`CATCHUP_DATA_DIR=./data`, relative to the directory where the
backend starts, which is `backend/` in these steps).
By default, the backend accepts requests only for `localhost`, `127.0.0.1`,
and `[::1]` (with or without a port). If you deploy behind a domain, set
`CATCHUP_ALLOWED_HOSTS` to a comma-separated list that includes that domain,
for example `localhost,127.0.0.1,[::1],catchup.example.org`. Do not add
untrusted domains or `*`. Changing the provider or its URL requires entering
the API key again; CatchUp will not send a stored key to a new provider or address.
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
has a supported feed, **Follow this account** on a public X profile or post,
or **Add this page to my next digest** without a feed.
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
extension after updating it. Pin CatchUp to the toolbar from the puzzle-piece
menu. Unpinned, it is listed lower in that menu on sites it cannot read
until you click it, and with many extensions it can be out of view.

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
automatically, calls the X API itself, schedules digest generation, or sends
the page to any other server. Follow this account sends the tab's URL to
your local server; see [X accounts](#x-accounts) for token setup and costs.
CatchUp may send saved page content to your
configured model provider during a later digest run.

It never reads cookies, saved passwords, or site storage. It does no
background reading and does not scroll, click, or open pages on your behalf.
Generic page extraction uses Mozilla Readability 0.6.0 (Apache-2.0); its
license is bundled in `extension/dist/readability-LICENSE.md`.
It saves only text the page shows, and takes the main text from
Readability's strict first pass, so a short post is not replaced by a
longer sponsor block or sidebar.

In the next digest run, the CatchUp server reads the links recorded on each
saved page at the **Linked pages** level chosen in Settings, as it does for
website items. It requests them itself, without your cookies. A link that
carries a private token, such as an email-confirmation or unsubscribe link,
may act when it is requested, so do not save pages that show such links.

Known limits:

- A page saved while a digest run reads linked pages waits for the next run,
  which reads its links first.
- A sponsor block that the page does not mark as one, in its class or id,
  can still be saved with a short post.

**X's terms prohibit scraping in any form.** Saving an X page is at your
own risk and only reads what your browser currently displays after you press
Add. This saved-page capture is separate from following through the X API;
CatchUp does not log in to X on your behalf.

## Privacy

Collected content is sent to the configured model provider. Self-hosting
does not keep that content local if you choose a cloud provider.

Chosen digest images load directly from their source sites when a digest is
shown, including the latest digest on the home page. This contacts those
sites with your IP address but sends no referrer. In Settings → Digest,
**Show images from source sites** is on by default; turn it off to prevent
these image requests. If CatchUp cannot read that setting, images are shown.

CatchUp never shows an image whose address points at this computer or a local
network, such as `192.168.…`, `localhost`, or `printer.local`, including in
digests saved earlier. It does not look up names, so a public-looking name
that points at a local address is not caught; turn images off if that matters.

## X accounts

To follow a public account, create an App under your own developer account at
[console.x.com](https://console.x.com/), then copy the App's **Bearer token**.
Paste it into **Settings → X accounts**, into the prompt on the **Sources**
page, or into the extension's prompt when you choose **Follow this account**.
CatchUp encrypts the token on your computer using `CATCHUP_SECRET_KEY`. The
extension sends it only to your local CatchUp server and does not store it in
browser storage. You cannot follow protected accounts or your home timeline.

**As of 2026-10-24**, X's pay-per-use prices are **$0.005 per post read** and
**$0.010 per user read**, deduplicated per UTC day. Previewing an account
performs a user lookup and reads up to five posts; each digest run may read
more posts. Replies returned by the API can count as reads even when CatchUp
does not include them in the digest. Set a **spending limit** in the X console
as a hard ceiling. `CATCHUP_X_READS_PER_RUN` defaults to 200 posts across all
followed accounts (including returned replies); set it to `0` to defer reads.
**Waits for the next run** means an account ran out of this run's shared
budget, not that its posts were discarded. CatchUp resumes it on a later
manual run.
If the read limit stops a read inside a thread, the author's replies read
before the limit are dropped and are not added later.

Read the [X Developer Policy](https://docs.x.com/developer-terms/policy)
before using this feature. It says:

> You must keep all API keys or other access credentials private.

Developers “may not use … API keys or other access credentials owned by
others” or “request that people provide their X password, account credentials,
or developer application information (including consumer key) to you directly”.
Our reading is that this self-hosted instance uses the **owner's own token**,
held on their computer; CatchUp's authors never receive it. X's policy does
not explicitly address this arrangement. You are responsible for complying
with X's terms and controlling access to your instance.

X requires stored content deleted or changed on X to be removed or updated
as soon as reasonably possible, or **within 24 hours** of a request from X or
the account owner. CatchUp clears an X post's raw text, replies, and linked
context after delivery, but keeps its title, summary, and link in saved
digests. It does **not** monitor later edits or deletions. In **Settings →
X accounts**, **Delete all X data** removes your token, followed X accounts,
their collected items, and their entries in saved digests (including derived
summaries and affected topic text). Use it to comply with a deletion request
or when your X access ends. Pages saved separately with the extension's
**Add this page** remain. X post text may be sent to your chosen
**model provider** for summarization, as with other sources. X's rules do not
explicitly say whether such a provider counts as a third party.

## Bilibili uploaders

Follow an uploader by pasting its space address, such as
`https://space.bilibili.com/2267573`, on Sources or using the extension's
**Follow this site**. CatchUp never contacts Bilibili; your RSSHub makes
those requests. It reads the uploader's JSON Feed and summarizes videos
only from subtitles included in that feed, never from video descriptions.
Without subtitles, a video waits for `CATCHUP_CAPTION_WAIT_HOURS` (default
24 hours), then appears in Creator updates as **No subtitles from RSSHub**.
CatchUp does not download video or audio, or collect Bilibili images,
comments, or linked pages.

**Bilibili's user agreement, section 5.6(3), updated 2025-04-30, forbids
getting its content with automated programs without Bilibili's written
permission, for any reason. You take that risk when using your RSSHub.**
RSSHub gets subtitles only with your own logged-in Bilibili cookie.
Keep that cookie only in RSSHub's settings: CatchUp never asks for or
stores it. For the Compose setup below, configure `BILIBILI_COOKIE_<uid>`
(your logged-in account's numeric id, not the uploader's) in `.env.rsshub`.
Keep this file private and do not commit or share it. Using the cookie
can put your Bilibili account at risk.

We recommend running your own RSSHub. A public RSSHub instance receives
the ids of the uploaders you follow, publishes no terms, and may not
return subtitles. Instances on Cloudflare Workers do not return subtitles.

### Optional RSSHub beside CatchUp

First complete the [Docker installation](#run-with-docker), including
creating the private `.env` with your instance secret. Work from that
installation directory, not `backend/`.

Bilibili uploaders need a CatchUp version that includes them. Until the
`latest` image does, use the `edge` image or a source build: an older
CatchUp would request the pasted Bilibili address itself.

For a **published-image install**, download `compose.rsshub.yaml` next to
`compose.yaml`:

```sh
curl -fsSLo compose.rsshub.yaml https://raw.githubusercontent.com/Zhuoang2/catchup/main/compose.rsshub.yaml
```

This install has no `COMPOSE_FILE` line yet. Add the following line to
your existing `.env`, keeping its instance secret:

```dotenv
COMPOSE_FILE=compose.yaml:compose.rsshub.yaml
```

Then start both services and wait for CatchUp's health check:

```sh
docker compose up -d --wait
```

For a **source build**, the override is already in the checkout. Change
the existing `COMPOSE_FILE=compose.yaml:compose.build.yaml` line in `.env`
to the following, rather than adding a second `COMPOSE_FILE` line:

```dotenv
COMPOSE_FILE=compose.yaml:compose.build.yaml:compose.rsshub.yaml
```

Then rebuild and start both services:

```sh
docker compose up -d --build --wait
```

The optional override sets `CATCHUP_RSSHUB_URL=http://rsshub:1200` for
CatchUp and runs `diygod/rsshub:latest` without publishing an RSSHub port.
That image is a third-party download from Docker Hub; CatchUp does not build
or publish it. As of 2026-11-22, it is about 130–133 MB compressed
(amd64/arm64).
If uploader lists fail and need RSSHub's browser fallback, change its `image`
in `compose.rsshub.yaml` to `diygod/rsshub:chromium-bundled`, about 391–507 MB
compressed depending on architecture, then run the appropriate start command
above again. The browser fallback may be slow; a later manual digest run can
use RSSHub's cached result.

To use an RSSHub you already run instead of this override, set
`CATCHUP_RSSHUB_URL` in the CatchUp process environment and restart it.
For example, use `https://rsshub.example/hub`; a path prefix is allowed,
but credentials, a query, or a fragment are not. This is an operator
environment setting, not a CatchUp Settings field.

## Run with Docker

Install Docker with Compose **2.24 or newer**. No local Python, uv, or Node
installation is needed. Secret generation needs `openssl`, included with
macOS and most Linux installs. On Debian or Ubuntu, use
`sudo apt update && sudo apt install curl ca-certificates openssl`.
Choose a published image or a source build. Run every Compose command
from the installation directory (the one with `compose.yaml` and `.env`),
not from a subdirectory such as `backend/`.

### Published image

Create a directory for your installation and download `compose.yaml` into it,
or use that file from a clone:

```sh
mkdir catchup
cd catchup
curl -fsSLo compose.yaml https://raw.githubusercontent.com/Zhuoang2/catchup/main/compose.yaml
```

The `latest` tag is the newest `vX.Y.Z` release and can lag behind `main`;
`X.Y.Z` pins a specific release, and the `edge` tag tracks `main`. To run
the current `main`, build from source below, or change the image in
`compose.yaml` to `ghcr.io/zhuoang2/catchup:edge`.

### Source build

Clone the repository so the Dockerfile and sources are available:

```sh
git clone https://github.com/Zhuoang2/catchup
cd catchup
```

### Create the instance secret and start

From your installation directory, generate an instance secret in a private
`.env` file:

```sh
(umask 077; set -C; key="$(openssl rand -hex 32)" && printf 'CATCHUP_SECRET_KEY=%s\n' "$key" > .env)
```

The command stops without writing if generation fails and refuses to
overwrite an existing `.env`. Keep it, or move it away deliberately before
creating a new one: a new secret makes saved model keys unreadable.
Do not commit or share `.env`. Keep this secret across upgrades and
backups, or previously saved model credentials cannot be decrypted.
Compose pins `CATCHUP_DATA_DIR=/data` and
`CATCHUP_FRONTEND_DIST=/app/frontend`, even if `.env` contains values
intended for development.

For the published image only, start CatchUp with the command below.
For a source build, skip this start command and continue with the
`COMPOSE_FILE` step below instead:

```sh
docker compose up -d --wait
```

For the published image only, the equivalent command without Compose is:

```sh
docker run -d --name catchup --env-file .env -e CATCHUP_DATA_DIR=/data \
  -p 127.0.0.1:8000:8000 -v catchup-data:/data \
  ghcr.io/zhuoang2/catchup:latest
```

For a source build, first add this line to `.env`. Compose reads it on
every command, so builds, upgrades, backups, and restores all use the local
image `catchup:local`, never the published image's tag:

```sh
(
  set -e
  [ -s .env ] || { echo 'Create .env with the instance secret first.' >&2; exit 1; }
  grep -qx 'COMPOSE_FILE=compose.yaml:compose.build.yaml' .env ||
    printf '\nCOMPOSE_FILE=compose.yaml:compose.build.yaml\n' >> .env
)
```

This refuses to create `.env` without a secret and adds the line only once,
even if the file has no final newline. Then build and wait for health:

```sh
docker compose up -d --build --wait
```

Open `http://localhost:8000`. The API and web interface share this port.
Check the health address:

```sh
curl http://localhost:8000/api/health
```

It answers `{"status":"ok"}`. Compose's `--wait` returns after the container
health check passes, so this address is ready when the start command ends.

The provided Compose file binds **only to `127.0.0.1`**. CatchUp has **no
login**: anyone who can access an exposed instance can read data and change
settings. Do not expose it to an untrusted network. If you deliberately
expose it, change the loopback address in `compose.yaml`, set
`CATCHUP_ALLOWED_HOSTS` to include your intended domain. Keep `localhost`
for local browser access and `127.0.0.1` for the container health check,
for example
`CATCHUP_ALLOWED_HOSTS=localhost,127.0.0.1,catchup.example.com`. Do not use
`*`. CatchUp accepts requests that change data only from its own pages or
tools that send no browser origin headers. A page on another site, or on
another local port, is refused. Other sites also cannot show CatchUp inside
their own pages, so they cannot trick you into clicking its controls. A
proxy in front of CatchUp must pass the browser's `Host` header, including
its port (in nginx, `$http_host`, not `$host`). Provide your own access
control and TLS. Collected content is sent to the configured model provider,
even when CatchUp itself runs locally.

Before upgrading the published image, make a backup with [Back up](#back-up).
Then upgrade without deleting the volume:

```sh
docker compose pull && docker compose up -d --wait
```

**Existing source-build users:** if your checkout predates
`compose.build.yaml`, do your first upgrade in this order:

1. Make a backup with [Back up](#back-up); the block works in the old setup.
2. Run `git pull`, so that `compose.build.yaml` exists.
3. Add `COMPOSE_FILE=compose.yaml:compose.build.yaml` to `.env` with the
   block above.
4. Run `docker compose up -d --build --wait`.

Before `git pull`, adding that line makes every Compose command fail.
Without the line, `up -d --build` silently keeps running your previous
build under the published tag instead of rebuilding. After the first
build as `catchup:local`, you can remove the old local tag with
`docker image rm ghcr.io/zhuoang2/catchup:latest`, so switching back to the
published image later pulls the real one.

For later source-built upgrades, make a backup with [Back up](#back-up),
then, from the installation directory:

```sh
(
  set -e
  [ -f compose.yaml ] && [ -f .env ] || { echo 'Run this from your installation directory (the one with compose.yaml and .env).' >&2; exit 1; }
  git pull
  docker compose up -d --build --wait
)
```

The named `catchup-data` volume survives container replacement; migrations
run automatically before the server accepts requests. Each block below
works in a new shell. Run it from your installation directory, not a
subdirectory. It finds Compose's actual volume name (including the project
name) and uses the installation's image name, so source builds work too.
These blocks work only for an installation started with Compose, and only
with the named volume. They do not find a container started with the
`docker run` command above. For a bind mount, stop CatchUp and back up by
copying its directory instead.

Each block stops at its first error. If a backup fails, fix the cause and
start CatchUp again with `docker compose up -d --wait`. A leftover
`.partial` file is not a backup and can be deleted. If a restore fails
after emptying the volume, run the restore again with a good backup
instead of starting CatchUp on the emptied volume.

When an archive check rejects a backup, it prints a Python error (a
traceback). In "Restore into this installation", nothing has been stopped
or changed at that point. In the new-machine block, only what `create`
made exists: an empty container and volume, and the image if it was missing.

### Back up

Backups are private, timestamped files in `"$HOME/catchup-backups"`, outside
the checkout. Each backup gets a new name and never replaces an earlier
one. A failed archive write leaves a `.partial` file, not a usable backup:

```sh
(
  set -e
  [ -f compose.yaml ] && [ -f .env ] || { echo 'Run this from your installation directory (the one with compose.yaml and .env).' >&2; exit 1; }
  docker compose config -q
  umask 077
  mkdir -p "$HOME/catchup-backups"
  backup="$HOME/catchup-backups/catchup-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
  [ ! -e "$backup" ] || { echo 'Backup already exists; try again later.' >&2; exit 1; }
  container="$(docker compose ps -aq catchup)"
  [ -n "$container" ] || { echo 'No Compose container for CatchUp here. After docker compose down, run docker compose create, then run this block again.' >&2; exit 1; }
  volume="$(docker inspect "$container" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
  [ -n "$volume" ] || { echo 'No named volume at /data; these commands work only with the named volume.' >&2; exit 1; }
  image="$(docker inspect "$container" --format '{{.Config.Image}}')"
  docker compose stop catchup
  docker run --rm --network none -v "$volume:/data:ro" --entrypoint python "$image" \
    -c 'import sys, tarfile; t = tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz"); t.add("/data", arcname="."); t.close()' \
    > "$backup.partial"
  mv "$backup.partial" "$backup"
  docker compose up -d --wait
  printf '%s\n' "$backup"
)
```

Back up `.env` separately and securely. Keep the same instance secret or
saved model credentials cannot be decrypted.

### Restore into this installation

**Make a backup first.** It gets a separate name, so the backup you want to
restore stays safe. Use `ls "$HOME/catchup-backups"` to find that backup,
and replace the example `backup=` filename below with it.

The block checks the entire archive before stopping the service or
emptying anything. It then replaces all data in the stopped service's
volume, including hidden files:

```sh
(
  set -e
  [ -f compose.yaml ] && [ -f .env ] || { echo 'Run this from your installation directory (the one with compose.yaml and .env).' >&2; exit 1; }
  docker compose config -q
  backup="$HOME/catchup-backups/catchup-YYYYMMDDTHHMMSSZ.tar.gz"
  [ -s "$backup" ] || { echo 'Choose an existing non-empty backup file.' >&2; exit 1; }
  container="$(docker compose ps -aq catchup)"
  [ -n "$container" ] || { echo 'No Compose container for CatchUp here. After docker compose down, run docker compose create, then run this block again.' >&2; exit 1; }
  volume="$(docker inspect "$container" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
  [ -n "$volume" ] || { echo 'No named volume at /data; these commands work only with the named volume.' >&2; exit 1; }
  image="$(docker inspect "$container" --format '{{.Config.Image}}')"
  docker run --rm --network none -i --entrypoint python "$image" \
    -c 'import gzip, shutil, sys, tarfile; f = gzip.GzipFile(fileobj=sys.stdin.buffer); t = tarfile.open(fileobj=f, mode="r|"); [tarfile.data_filter(m, "/data") for m in t]; shutil.copyfileobj(f, open("/dev/null", "wb"))' \
    < "$backup"
  docker compose stop catchup
  docker run --rm --network none -v "$volume:/data" --entrypoint python "$image" \
    -c 'from pathlib import Path; import shutil; [(shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()) for p in Path("/data").iterdir()]'
  docker run --rm --network none -i -v "$volume:/data" --entrypoint python "$image" \
    -c 'import sys, tarfile; tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz").extractall("/data", filter="data")' \
    < "$backup"
  docker compose up -d --wait
)
```

### Restore on a new machine

Set up the same install path described above, without starting CatchUp.
Skip secret generation: securely copy the same `.env` instead,
including the original secret and the source-build `COMPOSE_FILE`
line if used. For the published image, get `compose.yaml`. For a source
build, clone the repository: `create` builds a missing image, so it needs
the Dockerfile and sources, not just the Compose files.

In the installation directory, make the copied files private:

```sh
chmod 600 .env
mkdir -p -m 700 "$HOME/catchup-backups"
```

Copy the backup into `"$HOME/catchup-backups"`, then replace the example
`backup=` filename below with it. This refuses a volume that already
holds data; use "Restore into this installation" for that case:

```sh
(
  set -e
  [ -f compose.yaml ] && [ -f .env ] || { echo 'Run this from your installation directory (the one with compose.yaml and .env).' >&2; exit 1; }
  docker compose config -q
  backup="$HOME/catchup-backups/catchup-YYYYMMDDTHHMMSSZ.tar.gz"
  [ -s "$backup" ] || { echo 'Choose an existing non-empty backup file.' >&2; exit 1; }
  docker compose create
  container="$(docker compose ps -aq catchup)"
  [ -n "$container" ] || { echo 'No Compose container for CatchUp here. After docker compose down, run docker compose create, then run this block again.' >&2; exit 1; }
  volume="$(docker inspect "$container" --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Name}}{{end}}{{end}}')"
  [ -n "$volume" ] || { echo 'No named volume at /data; these commands work only with the named volume.' >&2; exit 1; }
  image="$(docker inspect "$container" --format '{{.Config.Image}}')"
  docker run --rm --network none -i --entrypoint python "$image" \
    -c 'import gzip, shutil, sys, tarfile; f = gzip.GzipFile(fileobj=sys.stdin.buffer); t = tarfile.open(fileobj=f, mode="r|"); [tarfile.data_filter(m, "/data") for m in t]; shutil.copyfileobj(f, open("/dev/null", "wb"))' \
    < "$backup"
  docker run --rm --network none -v "$volume:/data:ro" --entrypoint python "$image" \
    -c 'from pathlib import Path; import sys; sys.exit("Volume is not empty; use Restore into this installation instead.") if any(Path("/data").iterdir()) else None'
  docker run --rm --network none -i -v "$volume:/data" --entrypoint python "$image" \
    -c 'import sys, tarfile; tarfile.open(fileobj=sys.stdin.buffer, mode="r|gz").extractall("/data", filter="data")' \
    < "$backup"
  docker compose up -d --wait
)
```

A bind mount in place of the named volume must be writable by UID **999**
(the non-root container user). To move an existing source-checkout database,
stop the development backend first so its database file is complete, then
copy `backend/data/catchup.sqlite3` into the stopped container's volume
before starting it. Keep the same instance secret if it contains an
encrypted model key.

## Supported model providers

Choose one provider in Settings. Collected content is sent to the chosen
provider to generate summaries and group them into topics.

- **OpenAI-compatible:** APIs that follow OpenAI's Chat Completions format.
  DeepSeek is tested, and `https://api.deepseek.com` is the default base URL.
- **Anthropic:** uses the native Messages API. Get a key from the Anthropic
  Console and use `https://api.anthropic.com`, or edit the address for a proxy.
  CatchUp lists models from your account, with `claude-opus-5-5` first when
  available. Opus 5.5 costs $4 input and $20 output per million tokens.
  Some models always think, so CatchUp allows at least 16,000 output tokens
  per request; thinking counts toward that limit.

  For `claude-fable-5-2`, `claude-fable-5-1`, `claude-opus-5-5`,
  `claude-opus-5`, and `claude-sonnet-5-5`, a refused request is retried
  within the same call on a fallback model chosen by Anthropic, and billed
  at that model's rates. Other models do not request a fallback.
  A custom address must pass Anthropic's beta headers for this feature.
  The SDK also reads `ANTHROPIC_CUSTOM_HEADERS` from the server's environment.

**Reasoning:** choose **Provider default** to send no reasoning parameter,
**Low** to reason less, or **Off** to request no reasoning (OpenAI-compatible
providers only). OpenAI-compatible requests send `reasoning_effort` as `low`
or `none`; Anthropic's Low sends `output_config.effort` as `low`, including
when requesting a fallback model. Less reasoning can make digests faster
and cheaper, but summaries and topics may be less careful. If a run fails
with the Reasoning message, choose Provider default in Settings and
generate again.

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

Bilibili uploaders are supported through an RSSHub you run and configure;
see [Bilibili uploaders](#bilibili-uploaders) for setup and the terms risk.

For website items, CatchUp reads related links and author replies from public pages
only. Context fetches honor each site's robots.txt, including the sites that
links redirect to.
When a site's robots.txt cannot be read because of a server error or a network failure, CatchUp skips that site's linked pages and author replies for that run.
`CATCHUP_LINKS_PER_ITEM` (default 8) limits linked pages per item (twice that at Deep).
`CATCHUP_CONTEXT_FETCHES_PER_RUN` (default 60) limits requests per run
(including robots.txt; twice that at Deep).
CatchUp reads linked pages for up to 4 items at the same time, and keeps
requests to one host at least 1 second apart. While it reads them, the run
shows how many pages it has read, out of the pages it can still read within
that limit.
Set `CATCHUP_AUTHOR_REPLIES` (default on) to `0`, `false`, or `no` to turn off
author-reply fetching. Pages that cannot be read are skipped without failing
the digest.

Settings → Digest → **Linked pages** chooses how much of this a run reads. **Normal**, the default, reads up to `CATCHUP_LINKS_PER_ITEM` links per item, and author replies. **Shallow** reads up to 3 links per item, or fewer when `CATCHUP_LINKS_PER_ITEM` is lower, and author replies. **Deep** reads up to twice `CATCHUP_LINKS_PER_ITEM` links per item, keeps up to 6,000 characters of each page and 32,000 per item, and allows twice `CATCHUP_CONTEXT_FETCHES_PER_RUN` requests per run; author replies are read as at Normal. **Off** sends no context request at all, so no linked pages or author replies are read; replies saved with a page from the browser, or kept from a followed X account's thread, are still used. Shallow and Normal keep the per-run limit. A run uses the level saved when it starts. Deep's larger context leaves less of each summary request for the item's own text, so long items are summarized in more parts; with a small model, prefer Normal or Shallow.

Feed documents may be up to `CATCHUP_MAX_FEED_BYTES` (default 33554432,
32 MiB). Articles and transcripts remain limited to 5 MiB. Text longer
than a model call's budget is summarized in parts and combined; if a small
local model does not report its context window, set
`CATCHUP_SINGLE_CALL_CHARS` to a positive budget that fits the model.
Topic grouping is sized from the same context window, in batches of at
most `CATCHUP_GROUPING_BATCH_CHARS` characters (default 200000); with such
a model, lower that setting too.
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
for example `CatchUp/0.2.0 (+https://github.com/Zhuoang2/catchup; by /u/example)`.
The contact must be printable ASCII, no longer than 100 characters.
Automatically collecting pages without feeds and fetching content behind
a login or paywall are not supported. You can save
an individual page through the optional browser extension. CatchUp does not
transcribe audio or summarize video visuals.

## License

CatchUp is released under the [MIT License](LICENSE).
