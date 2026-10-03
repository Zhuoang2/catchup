# CatchUp

CatchUp is a self-hosted, on-demand personal digest. This repository is under
development. The current scaffold includes the API, database, frontend routes,
and CI; model setup, source collection, and digest generation are later tasks
in `openspec/changes/add-core-digest-flow/tasks.md`.

## Development setup

Install Python 3.11 or newer, [uv](https://docs.astral.sh/uv/), and Node.js 20
or newer. From the repository root:

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
From their respective directories, run backend tests with `uv run pytest`
and frontend tests/build with `npm test -- --run` and `npm run build`.
Tests require neither a network connection nor a real model key.

When model setup is implemented, collected content will be sent to the
configured model provider. Self-hosting does not keep that content local if
you choose a cloud provider.

## Supported sources

The initial source implementation is planned for RSS/Atom feeds, including
sites that declare a feed or expose one at a common path. Examples include
blogs, Bluesky and Mastodon profiles, and Reddit subreddits (availability
can depend on the host network). These adapters are not in this scaffold yet.
X, pages without feeds, podcasts/YouTube, and content behind a login or
paywall are not supported in this release.
