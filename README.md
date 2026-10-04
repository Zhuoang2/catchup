# CatchUp

CatchUp is a self-hosted, on-demand personal digest. Configure an
OpenAI-compatible model (DeepSeek is tested), add the sites and feeds you
follow, and click Generate Digest. CatchUp collects what is new since each
source's last successful check and writes a topic-grouped digest with links
to the originals. Saved digests stay available in History.

The project is under active development. Requirements live in
`openspec/specs/`; completed changes are in `openspec/changes/archive/`.

## Development setup

Install Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and Node.js
20.19+ or 22.12+ (as required by Vite 8). From the repository root:

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

Collected content is sent to the
configured model provider. Self-hosting does not keep that content local if
you choose a cloud provider.

## Supported sources

CatchUp supports RSS/Atom feeds, including sites that declare a feed or
expose one at a common path. Examples include
blogs, Bluesky and Mastodon profiles, and Reddit subreddits (availability
can depend on the host network).
X, pages without feeds, podcasts/YouTube, and content behind a login or
paywall are not supported in this release.
