# Implementation review notes

- Tasks 1.1–4.2 completed in order, one commit per group. Plan artifacts
  (`proposal.md`, `design.md`, spec delta) were not edited.
- Automated checks: backend 206 passed (96% statement coverage); frontend 22 passed and build passed;
  wheel includes migrations; Docker smoke passed on local arm64; Compose
  healthy with loopback binding; local amd64/arm64 build passed; both
  workflows pass actionlint; strict OpenSpec validation passed.
- Image size: 427,128,247 bytes (407.34 MiB). The negative smoke case with
  a broken health URL failed as expected. See
  `docs/process/test-report-add-docker-packaging.md` for the complete
  scenario mapping and smoke output.
- Review follow-up: real-model UI check, later migration upgrade, and GHCR
  publish/visibility and multi-architecture manifest require reviewer/user
  action after merge. Compose pins `/data` and `/app/frontend` regardless of
  `.env`; the standalone Docker command pins `/data` as well.

## Reviewer follow-up (2026-10-04)

- Pinned the Compose data/frontend paths, commented the optional source
  checkout data path in `.env.example`, and pinned `/data` in the `docker run`
  example. With a temporary `.env` specifying relative paths, `docker compose
  config --format json` showed `/data` and `/app/frontend`. The temporary file
  was removed.
- The Docker guide now retains `localhost` and `127.0.0.1` when configuring
  allowed hosts, and explains `latest` (after the first release), `edge`
  (current main), and version tags. Both paragraphs were read back.
- Fresh `docker build -t catchup:local .` and
  `scripts/docker-smoke.sh catchup:local`: all eight checks passed.
  `cd backend && uv run pytest`: 206 passed. `actionlint` on both workflows
  and `openspec validate add-docker-packaging --strict`: passed.

## CI fix by the reviewer (2026-10-05)

- The first CI run on PR #20 failed at job setup: `Unable to resolve action astral-sh/setup-uv@v10`. `setup-uv` publishes only full version tags (latest `v10.2.0`) and no moving `v10` major tag. Neither actionlint nor local runs check that a tag exists, so this surfaced only on GitHub.
- Checked every action reference against the GitHub API (`git/ref/tags/<tag>`). Only `astral-sh/setup-uv@v10` was missing; the others exist (`checkout@v7`, `setup-node@v7`, `setup-buildx-action@v4`, `build-push-action@v7`, `setup-qemu-action@v4`, `login-action@v4`, `metadata-action@v6`).
- Fixed directly: `astral-sh/setup-uv@v10.2.0`. A one-line change, so no Droid run.
- Root cause in planning: `design.md` D6 assumed major tags for every action. The research recorded "latest tag v10.2.0" but not whether a `v10` alias exists.
