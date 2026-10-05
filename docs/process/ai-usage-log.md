# AI Tool Usage Log

Real usage records for the technical spec, alpha reflection, and final report. Each entry: date, tool/model, purpose, prompt (verbatim or faithful excerpt), outcome, problems, adjustment.

## 2026-10-05 — Podcast and video sources, review round 1 (Factory Droid)

- Prompt (faithful excerpt): "Implement review fixes 8.1–8.7 on `add-podcast-and-video-sources` in task order ... use offline tests ... one group-8 commit ... Docker verification ... stop if D12 conflicts with earlier decisions; do not edit planning artifacts, push, tag, or open a PR."
- Outcome: Shared-link-safe episode identity and transcript matching, post-parse DTD entity screening, transcript/caption joining, lossless text splitting, redirect-hop spacing, ordered summary rendering and exact-name Creator updates grouping. Final checks: 342 backend tests with 96% coverage, 35 frontend tests, build, strict validation, Docker build and smoke passed. The full results are in `test-report-add-podcast-and-video-sources.md`.
- What failed / adjustment: Vitest was absent in this worktree; `npm ci` installed the locked dependencies. The first full backend run found an old call-count assertion that assumed oversized unspaced words fail before reaching the fake model; updated it for the new hard-split behavior and reran the suite green. Tests used fixture feeds, fake transports and model clients, with no live provider calls or real sleeps.

## 2026-10-05 — Podcast and video sources, group 1 (Factory Droid, GPT-6 Sol)

- Prompt (faithful excerpt): "Implement OpenSpec change add-podcast-and-video-sources using the openspec-apply-change skill ... work through tasks.md in order and check off each task only after its verification passes ... commit after each task group ... no real network or model providers in tests ... do not edit planning artifacts."
- Outcome: Added migration 0002 with an upgrade/downgrade regression test, pinned transcript and XML dependencies, and added validated environment settings. Backend 240 tests, frontend 22 tests, and frontend build passed. No external services were called in tests.
- What failed / adjustment: The first downgrade test failed because SQLite rebuilt a parent table while foreign keys were enabled and child rows existed. Using native SQLite `DROP COLUMN` through Alembic batch mode preserved the referenced rows; the second test passed. The removed item cap's runner call temporarily uses the new override or fallback budget until long-text handling is implemented in group 6.

## 2026-10-05 — Podcast and video sources, group 2 (Factory Droid, GPT-6 Sol)

- Prompt: Same user request as group 1, with particular emphasis on offline tests, transcript-status selection and group commits.
- Outcome: Added configurable 32 MiB feed fetches while keeping articles at 5 MiB and the cache at 5 MiB per entry; classified feeds by YouTube host or majority audio enclosures; showed source kinds in preview; resolved Apple Podcasts pages through a mocked iTunes lookup. The interim runner excludes items awaiting transcripts so a partially implemented change cannot summarize descriptions. Full checks: 257 backend tests, 25 frontend tests and frontend build passed.
- Problems / adjustment: The first patch for the safe-fetch test missed its context; reapplied only that test. Confirmed that pending audio and video would otherwise reach the old summary path before the later selection task, so restricted the interim summary query to transcript-ready items.

## 2026-10-05 — Podcast and video sources, group 3 (Factory Droid, GPT-6 Sol)

- Prompt: Same user request as groups 1–2, with the reviewer requirement to keep lxml recovery hardened and never log fetched content.
- Outcome: Added multi-candidate parsing with feedparser fallback, format conversion, and per-check podcast resolution with up to two safe fetches. A transcript replaces cached summaries; missing ones stay waiting. Full checks: 272 backend tests, 25 frontend tests, and frontend build passed.
- What failed / adjustment: A focused experiment showed libxml expands an internal entity in an attribute even with `resolve_entities=False`. The hardened candidate parser now declines DTD-bearing documents; feedparser's non-expanding single-candidate fallback remains available. Added a regression test for the attribute case.

## 2026-10-05 — Podcast and video sources, group 4 (Factory Droid, GPT-6 Sol)

- Prompt: Same user request, especially "selection is decided by transcript_status as in design.md D7, and expiry statuses are written only in the save transaction."
- Outcome: Added status-driven selection and atomic delivery, Creator updates snapshots and history API, and wait/deferred counts in the run view. Full checks passed: 278 backend tests, 28 frontend tests, frontend build. A further three backend cases confirmed expiry despite failed feed checks (9 focused cases passed).
- What failed / adjustment: The first grouping test tried to create two sources with the same feed URL and SQLite rejected the duplicate. Changed the test fixture to reuse a source for multiple items, as the product does.

## 2026-10-05 — Podcast and video sources, group 5 (Factory Droid, GPT-6 Sol)

- Prompt: Same user request, emphasizing no real YouTube calls in tests, injected spacing and clocks, and never logging fetched content.
- Outcome: Added optional caption preferences and UI warnings, Shorts baseline rules, a spaced requests client with original-language track choice and exception mapping, a per-run capped caption pass, and supported-sources documentation. After updating the tests for the new caption pass, 310 backend tests, 29 frontend tests, frontend build, and README/config variable cross-check passed.
- What failed / adjustment: Two earlier Creator updates tests expected unfetched YouTube videos to remain deferred even with caption fetching off. With the real pass enabled, those videos correctly become `captions_off`; the tests now expect that state. A separate waiting/deferred test uses caption opt-in and a cap of one to exercise the intended held-item path.

## 2026-10-05 — Podcast and video sources, group 6 (Factory Droid, GPT-6 Sol)

- Prompt: Same user request, including updating existing model fakes instead of weakening assertions and logging no fetched content.
- Outcome: Added strict context-window metadata parsing and caching, complete-text part/combine summaries and transcript key points, and thread-safe token accounting through the run, digest API and UI. Full checks passed: 327 backend tests, 34 frontend tests, and frontend build.
- Adjustment: The old truncation test was updated to assert both halves of the original input reach part prompts, rather than accepting a cut-off suffix. Existing model fakes were updated to return structured model metadata and usage totals.

## 2026-10-05 — Podcast and video sources, group 7 (Factory Droid, GPT-6 Sol)

- Prompt: Same user request; "Docker is running on this machine, so run the docker build and scripts/docker-smoke.sh in task 7.1; never push, tag, or open a PR."
- Outcome: 327 backend tests passed at 96% statement coverage; 34 frontend tests and build passed; strict OpenSpec validation, local Docker build and all eight smoke checks passed. Results and the omitted live-source/provider checks are in `test-report-add-podcast-and-video-sources.md`.
- Adjustment: The existing Docker smoke script's exact preference JSON assertion needed the two new fields. Updated the assertion without dropping the restart and saved-language checks, then built and ran the smoke test successfully. No remote actions were taken.

## 2026-10-04 — Docker packaging implementation (Factory Droid, GPT-6 Sol)

- Purpose: Implement `add-docker-packaging` (#7), groups 1–4, on a branch from main.
- Prompt (faithful excerpt): "Implement OpenSpec change add-docker-packaging ... using the openspec-apply-change skill ... check off each task only after its verification passes. Commit after each task group. Do not edit proposal.md, design.md, or the spec deltas ... pytest makes no real network calls, uses no real API key, writes nothing outside temp dirs, and uses no real sleeps; Docker checks use only local images, throwaway volumes, and loopback ports."
- Outcome: Self-contained package, local Docker/Compose deployment, smoke script, CI and release workflow definitions, and user guide. Four group commits; 206 backend and 22 frontend tests, frontend build, smoke, wheel check, both-architecture local build, actionlint and strict validation passed. No image pushed or tag created.
- Problems / adjustment: The local `actionlint` executable was missing, so Homebrew installed it before linting. A deliberately broken image health URL proved the smoke script rejects unhealthy containers. The source `.env.example` sets a relative data path; the Docker guide instead generates a secret-only `.env` so `/data` remains the persistent location. Real-key and GHCR checks remain for review.

### Reviewer follow-up (Factory Droid, GPT-6 Sol)

- Prompt (faithful excerpt): "Reviewer findings ... three small fixes ... Data directory must not depend on the container's working directory ... keep localhost and 127.0.0.1 in CATCHUP_ALLOWED_HOSTS ... latest exists only after the first vX.Y.Z tag ... commit once."
- Outcome: Compose pins `/data` and `/app/frontend` even when `.env` supplies relative paths; the standalone Docker example pins `/data`. Documentation now explains health-check hosts and available image tags. A temporary `.env` confirmed Compose's precedence; fresh Docker smoke, 206 pytest cases, actionlint, and strict OpenSpec validation passed.
- Adjustment: The first Docker guide only warned against a relative data path; the review identified that deployment should enforce the persistent path rather than depend on that warning or the container's current directory.

## 2026-10-04 — Source reliability implementation (Factory Droid, GPT-6 Sol)

- Purpose: Implement OpenSpec change `improve-source-reliability`, groups 1–4, on a branch from main.
- Prompt (user, faithful excerpt): "Implement OpenSpec change improve-source-reliability (GitHub issue #3) using the openspec-apply-change skill ... Work through ... tasks.md in order (groups 1-4) and check off each task only after its verification passes. Commit after each task group. Do not edit proposal.md, design.md, or the spec deltas ... no real network, no real API key, no writes outside pytest temp dirs, no real sleeps in tests."
- Outcome: Descriptive User-Agent and bounded rate-limit retry, preview feed cache, per-run host spacing, clear rate-limit responses/UI, docs and test mapping. Four group commits; 197 backend and 22 frontend tests pass, build and strict validation pass. No live sources or model were used.
- What failed / adjustment: `parsedate_to_datetime` returned a naive date for asctime; interpreted that format as UTC. A fake sleep test caught an unnecessary zero-second sleep. The earlier end-to-end test expected confirm to fetch again; corrected its request count to four after caching. Default sleeps were intercepted in the test fixture, while timing assertions use fake clocks and sleeps.

## 2026-10-01 — Product discussion and proposal (Codex)

- Tool: Codex.
- Purpose: Product discussion, scope narrowing, proposal drafting and polishing, limited competitor research, workflow figure.
- Outcome: Proposal text (`docs/proposal.md`), handoff document (`docs/handoff.md`), workflow figure (`assets/catchup-workflow.png`).
- Note: The original conversation memory (`../work/agent-memory.md`, outside this repo) mixes in unrelated tool records and outdated ideas, so the handoff distilled only the relevant parts. Detailed prompts from that phase are not reproduced here.

## 2026-10-01 — Making the planning skills OpenSpec-aware (Claude Code, Opus 5.5)

- Purpose: Fit the user's existing RePPIT skills (research → proposal → plan) into an OpenSpec workflow without writing every document twice.
- Prompt (user, translated from Chinese): "I think we can manage the project with OpenSpec. For every update, you first research, then propose, then plan. After planning, Droid implements, and finally you review. What do you think?"
- Outcome: The three global skills now detect an OpenSpec project with `openspec list --json` (non-null `root`) and write into `openspec/changes/<name>/` (`research.md`, `design.md`, `proposal.md`, spec deltas, `tasks.md`). Projects without OpenSpec keep the old `research/`, `proposals/`, `plans/` paths. Originals are backed up outside the repo.
- Verification: In a throwaway project, `openspec list --json` returned `root: null` without OpenSpec and a path with it. An extra `research.md` in a change folder did not break `openspec validate`.
- Adjustment / lesson: The skills read each artifact's rules from `openspec instructions <artifact>` at run time instead of copying OpenSpec's formats, so they survive OpenSpec upgrades. A worktree pitfall turned up during testing: Droid's worktree starts from the last commit, so plans must be committed before hand-off. This is now a step in the plan skill.

## 2026-10-01 — Codex → Claude Code handoff prompt (Claude Code, Opus 5.5)

- Purpose: Transfer the project from Codex to Claude Code.
- Prompt (user, verbatim):

  > 请接手 CatchUp 项目。先读取 CLAUDE.md、docs/handoff.md、docs/proposal.md，以及项目文件夹中的 Final Project Description，了解产品设想和课程要求。同时读取本机存在的 ~/.codex/AGENTS.md。
  > 课程要求以 Final Project Description 原文为准；交接文件中的课程摘要仅供参考。如发现材料之间存在冲突，请明确指出。
  > 已确认的产品方向不需要重新 brainstorm。请区分既定需求、后续功能和未定技术细节，先简短复述你的理解，再结合课程交付要求和时间节点，提出推荐技术方案与分阶段实施计划，随后推进核心流程。只对确实影响实现的关键未定项向我提问。
  > 开发过程中保留需求变化、设计决策、测试结果，以及真实的 AI 工具使用实例、提示词调整和成功或失败经验，为 technical spec、alpha release 和最终报告积累材料。

- What worked: The prompt named the source of truth for course rules (the original brief over the handoff summary). It separated confirmed requirements from open decisions and told the agent not to reopen settled questions.
- Outcome so far: Claude compared the handoff's course summary with the brief and listed the differences in its reply. It initialized git and OpenSpec, merged the project instruction files, and created these process logs.

## 2026-10-01 — Source feasibility research (Claude Code subagent, Opus 5.5)

- Purpose: Before recommending supported sources, verify current (2025–2026) facts instead of relying on model memory.
- Prompt (excerpt): "I need CURRENT (2025–2026) facts, verified with web search / official docs / GitHub issues, not memory… return a concise summary… with a source URL for each claim and an explicit 'unverified' marker where you couldn't confirm."
- Outcome (findings that changed the plan):
  - YouTube channel RSS still exists but returned intermittent 404/500 in live tests (1 of 3 channels stable). Public reports of 404s start around 2025-12, worse from datacenter IPs. Feeds list only the latest 15 uploads.
  - `youtube-transcript-api` 1.2.4 (2026-01) has had no release for 8 months. Its README says YouTube blocks most cloud-provider IPs, and an open issue reports PO-token failures. The YouTube Data API can download captions only for videos the caller can edit.
  - `<podcast:transcript>` adoption is low: a small 2026 sample found it on 8.8% of episodes across 8 AI podcasts. Apple's transcripts have no public API. An Apple Podcasts URL resolves to its RSS feed via the no-auth iTunes Lookup API (verified live).
  - feedparser 6.0.14 and trafilatura 2.2.0 are both released July 2026 and maintained. trafilatura includes feed autodiscovery.
- Lesson: Verifying first changed the plan. Blogs/RSS become the reliable first source type. YouTube is best-effort, likely to fail on a cloud-hosted demo. Podcast coverage will be thin unless transcription is added later. The prompt's demand for URLs and "unverified" markers made the report easy to check.

## 2026-10-02 — First RePPIT cycle for `add-core-digest-flow` (Claude Code, Opus 5.5)

- Purpose: Research → two proposals → plan for the core flow, run through the OpenSpec-aware RePPIT skills.
- Research: Two parallel subagents verified current DeepSeek API facts and library behavior. Findings that shaped the design:
  - DeepSeek retired and renamed models in September 2026, so model IDs are not hard-coded.
  - JSON mode can return empty content, so empty responses are retried.
  - feedparser has no entry-id fallback and no timeout.
  - `trafilatura.find_feed_urls` returns article links, not feed URLs.
- Proposals: Proposal 1 (item ledger) vs Proposal 2 (per-source time checkpoints). The user asked how "new vs old" is decided, so Claude explained it with a worked table of runs, and the explanation went into `design.md`. The user then rejected a proposed 50-item cap and asked for a future "top N" feature; both changes are logged in `requirements-changes.md`. The user chose Proposal 1.
- Plan: proposal.md, five spec deltas (model-settings, source-management, content-collection, digest-generation, digest-history), the final design.md, and 22 tasks in tasks.md. `openspec validate --strict` passes.
- Lesson: The user's clarifying question exposed that "new content" was explained only abstractly. A concrete run-by-run example made the semantics reviewable, and it became a spec requirement with scenarios.

## 2026-10-02 — First Droid hand-off: task group 1 of `add-core-digest-flow` (Factory Droid, GPT-6 Sol)

- Purpose: First implementation by Factory Droid, limited to group 1 (scaffolding and CI) as a trial before handing over the remaining 17 tasks.
- Command: `droid exec --auto medium -w add-core-digest-flow -o json "<prompt>"`
- Prompt (verbatim):

  > Implement ONLY task group 1 (tasks 1.1 to 1.5) of OpenSpec change add-core-digest-flow using the openspec-apply-change skill. Read openspec/changes/add-core-digest-flow/proposal.md, design.md, specs/ and tasks.md first. Work through tasks 1.1-1.5 in order and check off each task in tasks.md only after its verification passes. Do not start group 2. Do not edit proposal.md, design.md, or the spec deltas. Commit when group 1 is done. If a task is blocked or the plan looks wrong, stop and report instead of improvising. At the end, report: what you did per task, the exact verification commands you ran and their results, any deviations from the plan, and the branch/worktree path.

- Prompt adjustment vs the template in the plan skill: Scope was narrowed to one group ("ONLY", "Do not start group 2"). The prompt adds an explicit reading list and a required end-of-run report (per-task summary, the exact verification commands and results, deviations, worktree path) so the review can check claims instead of trusting them.
- Outcome (Droid's report): commit `0da6d26`, 5/22 tasks checked, 4 backend + 1 frontend tests passing, `openspec validate --strict` passing. It reported its own failure (an SPA fallback route shadowed an API route) and its fix, and it upgraded Vitest to clear two `npm audit` advisories. It also added its own entry to this log, as `AGENTS.md` instructs; that entry is kept below.
- Cost: 29 turns, ~4.4 minutes, 242,373 Factory credits (from the `droid exec` JSON result).

### Droid's own record of group 1 (Factory Droid, GPT-6 Sol)

- Purpose: Implement only tasks 1.1–1.5, the application scaffold, migration, UI routes, static serving, documentation, and CI.
- Prompt (user, excerpt): "Implement ONLY task group 1 (tasks 1.1 to 1.5) of OpenSpec change add-core-digest-flow using the openspec-apply-change skill. ... Work through tasks 1.1-1.5 in order and check off each task in tasks.md only after its verification passes. Do not start group 2. ... Commit when group 1 is done."
- Outcome: Backend health/error tests, SQLite/Alembic startup test, frontend navigation test/build, SPA/API isolation test, development setup, and CI. Four backend and one frontend tests pass locally. No real key or live network is needed for the tests.
- What failed: A first static fallback route shadowed a test-added API endpoint (one backend test failed). Changed the fallback to serve only 404 responses outside `/api`, then all four tests passed. The initial `npm ci` reported two moderate Vitest dev-dependency advisories; upgrading to patched Vitest 4.1.11 cleared `npm audit` while tests and build still passed.
- Adjustment: Checked each task's stated verification before updating its checkbox. Left application features in later groups unimplemented.

### Claude Code review of group 1 (Opus 5.5)

- Method: Claude did not trust the report. It checked out the branch in a separate worktree, re-ran every verification command, compared the migration against the models (`alembic.autogenerate.compare_metadata`, no drift), tested multi-threaded SQLite access, and read every non-generated file.
- Confirmed: all of Droid's stated test and build results reproduced, and `npm audit` showed 0 vulnerabilities.
- Findings that Droid's own checks missed:
  1. [must] Two tests built the app from environment settings, so running the suite created `backend/data/catchup.sqlite3`. It would also migrate a user's real database if `CATCHUP_DATA_DIR` were set. Reproduced by running pytest in a clean checkout.
  2. [must] `openai` was pinned to `<3` (locked 2.54.0) although 3.x is current. This was caught before any client code was written against the old major.
  3. [should] `AppError` lived in `main.py`, which would cause circular imports once routers import it.
  4. [should] Mutual foreign keys between `digest_runs` and `digests`; SQLAlchemy warns this may become an error.
  5. [optional] Vite 6 / TypeScript 5.8 instead of the current Vite 8 / TypeScript 7.
- Lesson: Every task's "Verify" line passed, yet finding 1 was still a real defect. Verification lines check what the plan names, not side effects such as files written outside the test sandbox. Future plans should state "tests must not touch real data or the network" as a verifiable criterion, not only as a note. Findings were sent back to the same Droid session (`droid exec -s`).

### Droid's record of the review fixes (Factory Droid, GPT-6 Sol)

- Purpose: Correct issues found in review of the scaffold before starting group 2.
- Prompt (user, excerpt): "Code review of your group 1 commit 0da6d26 found issues. Fix them on branch add-core-digest-flow, still within group 1 (do not start group 2): ... Tests must never touch a real data dir ... Change to openai>=3,<4 ... Move AppError ... make digest_runs.digest_id a plain nullable integer ... [optional] Upgrade [Vite and TypeScript] only if npm test, npm run build and npm audit stay clean."
- Outcome: Test applications use a temporary data directory; a sentinel-directory test detects accidental writes to the configured location. OpenAI 3 is locked, shared errors are independent of the app module, and the digest table cycle is removed. The optional frontend upgrade passed tests, build, and audit.
- What failed / adjustment: No checks failed in this round. Added regression tests for the two database issues, and updated the Node requirement in the README to match Vite 8.

### Claude Code re-verification of the fixes (Opus 5.5)

- Re-ran everything in a fresh worktree of commit `5441843`:
  - 6 backend tests pass, also with `-W error::sqlalchemy.exc.SAWarning`, and no `backend/data` is created.
  - `openai` 3.24.0 is locked; `Base.metadata.sorted_tables` raises no warning.
  - Vite 8.3.2, TypeScript 7.0.2, plugin-react 6.1.1: frontend test and build pass, `npm audit` reports 0 vulnerabilities.
  - `openspec validate --strict` passes.
- Remaining weakness: The new sentinel test builds its settings before setting `CATCHUP_DATA_DIR`, so it passes regardless and would not catch a future test that calls `create_app()` without settings. The original bug is fixed. An autouse fixture that points every test at a temporary data dir is added to the next hand-off instead.
- Cost: the session counter went from 29 to 41 turns and from 242,373 to 371,518 credits, so the fix run cost ~129K credits (see the cost note under groups 2–3).

## 2026-10-03 — Model settings implementation (Factory Droid, GPT-6 Sol)

- Purpose: Implement tasks 2.1–2.4 and the carried-over test sandbox fix.
- Prompt (user, excerpt): "Implement ONLY task groups 2 and 3 (tasks 2.1-2.4 and 3.1-3.4) ... Replace it with an autouse fixture ... tests make no real network calls ... never read a real API key, and never write outside pytest temp dirs. Check off each task only after its verification passes. Commit after group 2 and again after group 3."
- Outcome: The autouse fixture redirects app data to per-test temp dirs, removes the instance secret, and rejects unmocked DNS/connect calls. Added Fernet protection, a model client, settings APIs and a language picker UI.
- What failed / adjustment: The first frontend run lacked dependencies (`npm ci` fixed it). Vitest 4 did not automatically clean up DOM trees between tests (three queries failed), so explicit Testing Library cleanup was added. OpenAI 3 uses httpx2, so a test-only transport bridge sends its requests through respx's httpx router without network calls.

## 2026-10-03 — Source management implementation (Factory Droid, GPT-6 Sol)

- Purpose: Implement tasks 3.1–3.4, with no work on content collection or generation.
- Prompt: The same user prompt above requested group 3, offline tests, checking each task only after verification, and a second commit.
- Outcome: Safe fetching with DNS and redirect checks, timeouts and a 5 MB cap; feed parsing, HTML discovery and bounded same-origin probing; source preview/confirm/list/delete with first-add baseline and pending marking; and a Sources page. Tests use fixture bytes, respx and patched DNS.
- What failed / adjustment: A safe-fetch test revealed that Python's `is_global` alone allows multicast; explicit multicast and other reserved-address checks fixed it. Two respx tests matched a generic route before the specific feed route; registering the specific route first fixed their failures. The probing budget was shared across candidate requests and their redirects so redirects cannot exceed eight requests or leave the origin. Final review also tightened group 2's provider URL validation to reject embedded credentials rather than echoing them in settings or connection errors.

## 2026-10-03 — Groups 2–3 of `add-core-digest-flow` (Factory Droid, GPT-6 Sol) and review (Claude Code, Opus 5.5)

- Hand-off prompt changes after the group 1 lesson:
  - Rules moved from notes into verification criteria: "Rules for every task, treated as verification criteria (not just notes): tests make no real network calls …, never read a real API key, and never write outside pytest temp dirs."
  - The carried-over sentinel-test fix comes first.
  - Commit per group, and a required report of deviations and uncertainties.
- Droid's result: commits `54a5cd3` (group 2) and `74ea0c5` (group 3); 76 backend + 9 frontend tests; 13/22 tasks. The new autouse fixture blocks DNS and socket connections for every test. Cost: ~10 minutes; the session counter rose from 41 to 109 turns and from 371,518 to 1,518,203 credits, so this run cost ~1.15M credits (see the cost note below).
- Claude's review:
  - Method: re-ran everything in a separate worktree (76 + 9 tests, 94% backend coverage, build, audit 0) and read all source files. Hypotheses were then checked with small experiments instead of being reported as guesses: the SDK default timeout, IP-classification edge cases, a `text/plain` CSRF attempt, and a foreign Host header.
  - Findings:
    1. [must, security] The stored API key was reused when the base URL changed. With no Host check (a foreign Host returned 200), a DNS-rebinding page could repoint the provider and receive the key. **The root cause was Claude's own design text** ("missing fields fall back to stored values"), not Droid's code.
    2. [must] `safe_fetch` had a per-read timeout but no total deadline, so a slow-drip server could hold a request open.
    3. [must] The model client inherited the SDK default read timeout of 600 s (verified), so a connection test could hang for 10 minutes.
    4. [should] `httpx2` was imported but not declared; an empty `choices` list would crash; NAT64 `64:ff9b::7f00:1` passed the address guard.
  - Ruled out by experiment: simple CSRF (FastAPI rejected a `text/plain` body with 422).
- Process: Claude amended the spec (two new requirements), design (D9, D4 additions), and tasks (2.5, 3.5) on the branch, logged the requirement change, and sent the fixes back to the same Droid session.
- Lesson: Reviewing only against the plan would have missed finding 1, because the code matched the design. A short threat-model pass ("who can reach this API, and what can they make it do?") belongs in every review of a security-relevant group.

## 2026-10-03 — D9 and D4 review fixes (Factory Droid, GPT-6 Sol)

- Purpose: Implement only tasks 2.5 and 3.5 after review amended the plan.
- Prompt (user, excerpt): "The main finding is a security issue whose root cause was the original design text, not your code: the stored API key could be sent to a changed base_url, and with no Host check a DNS-rebinding page could exploit that. Implement ONLY tasks 2.5 and 3.5, then stop ... no real network, no real key, no writes outside pytest temp dirs."
- Outcome: Reject changed provider URLs without a new key, enforce an environment-configured Host allowlist, pass explicit model-call timeouts, retry empty choices, declare httpx2, enforce a 30-second fetch deadline, and check NAT64's embedded IPv4 address. Added offline tests with a fake provider, respx and a fake clock.
- What failed / adjustment: The focused backend tests passed on the first run. The initial full frontend command could not find Vitest in this fresh worktree; `npm ci` installed the locked dependencies, then tests and build passed. Local Host tests use a default-only configuration; other tests add TestClient's synthetic `testserver` Host through the autouse fixture without broadening the production default.
- Fix result: Droid commit `571daca` (tasks 2.5, 3.5). Claude re-verified it in a fresh worktree:
  - 95 backend tests at 94% coverage, 9 frontend tests, build passing, `openspec validate --strict` passing.
  - Experiments: a foreign Host header now gets 400, while `127.0.0.1` and the Vite dev proxy host `localhost:5173` still work. `httpx2` is declared.
- **Cost note (correction):** `droid exec -s` reports the session's **cumulative** turns and credits; the turn counts rise 29 → 41 → 109 → 128. Per-run costs:

  | Run | Credits |
  | --- | --- |
  | Group 1 | ~242K |
  | Group 1 fixes | ~129K |
  | Groups 2–3 | ~1.15M |
  | Fixes 2.5/3.5 | ~417K |
  | **Total so far** | **~1.94M** |

  Resuming one long session also makes every later call re-read a growing context. For group 4 onward, a fresh session per group is cheaper; the OpenSpec files already carry the needed context.

## 2026-10-03 — Content collection implementation (Factory Droid, GPT-6 Sol)

- Purpose: Implement only task 4.1, including safe article extraction and per-source check outcomes.
- Prompt (user, faithful excerpt): "Implement ONLY task group 4 (task 4.1, content collection), using the openspec-apply-change skill ... source_checks.http_status must be recorded ... secondary link match must ignore links equal to the source's feed_url ... possible-gap flag applies only to a successful check of a source that already has recorded items ... no real network ... Commit once at the end."
- Outcome: Added `check_source(session, source, run_id, settings)`, first-sight recording and gap detection, HTTP status on check failures, and article extraction with feed fallback. Confirm-time pending entries also use the same extractor so the first digest has full text when available. Offline tests cover all content-collection scenarios.
- What failed / adjustment: No tests failed. The course brief file named in `AGENTS.md` was absent in this worktree; task 4.1 did not depend on it. During implementation, noticed confirm-time pending entries would otherwise bypass extraction; reused the extraction helper there and adjusted existing test fixtures to supply sufficiently long feed text where article fetching is not under test. No real key or live network was used.
- Verification: `uv run pytest` (112 passing before the last gap-edge test); final `uv run pytest --cov=catchup --cov-report=term` (113 passing, 95% overall, 100% collection); `npm test -- --run` (9 passing); `npm run build` and `openspec validate add-core-digest-flow --strict` passed.

## 2026-10-03 — Group 4 in a fresh Droid session (Factory Droid, GPT-6 Sol) and review (Claude Code, Opus 5.5)

- Change in approach: a new `droid exec` session instead of resuming the long one (`-s`), to stop paying for an ever-growing context. Because the new session had no memory, the prompt carried the context explicitly:
  - a reading list (AGENTS.md, the relevant design decisions and spec, and the existing modules to reuse)
  - four reviewer notes that anticipated pitfalls found while reading earlier code: HTTP status missing from `FetchError`; linkless entries carrying the feed URL as their link; the exact gap rule; extraction only via `safe_fetch`
  - an explicit boundary: expose `check_source` for the runner; build no runner, API, or UI
- Result: commit `0eedcd6`, 16/24 tasks, 113 backend tests. Every content-collection scenario is mapped to a test in `review-notes.md`.
- Cost: 27 turns, ~4 minutes, **~252K credits**. That is about the same as group 1, versus ~1.15M for groups 2–3 in the resumed session. Fresh sessions plus an explicit context prompt worked better on cost, without losing quality.
- Review: no required fixes; one trade-off recorded (synchronous article extraction). The only discrepancy was reported coverage of 95% vs 94% reproduced.
- Lesson: Putting the pitfalls into the prompt in advance prevented a fix round. All four notes were handled correctly on the first pass.

## 2026-10-03 — Digest generation group 5 (Factory Droid, GPT-6 Sol)

- Purpose: Implement only tasks 5.1–5.4: summaries, topic grouping, run lifecycle, API, and Generate page.
- Prompt (faithful excerpt): "Runner thread and stage-1 workers must never share a SQLAlchemy session ... Put the model-client factory on app.state ... Read digest_language once at run start ... POST /api/digest-runs: 409 model_not_configured ... 409 run_active ... collecting-stage progress ... no real network, no real API key, no writes outside pytest temp dirs, and no fixed sleeps in tests. ... Commit after each of 5.1-5.2 and 5.3-5.4."
- Outcome: Added four-way model-only summary workers, validated topic refs with batching/merge, short-transaction run persistence with startup recovery, progress API, and polling UI. Summaries are reused only in the matching language; saved digest and delivery are atomic. Tests map all digest-generation scenarios in `review-notes.md`. Committed the first pair of tasks separately from the runner/UI pair.
- What failed / adjustment: No focused or full checks failed. `npm ci` was needed in the fresh worktree. Strengthened a concurrent fake to route responses by item title rather than scheduling order, and changed fatal-error handling not to wait for unrelated model workers. No real model or feed was contacted.

## 2026-10-03 — Group 5 (Factory Droid, fresh session) and review (Claude Code, Opus 5.5)

- Prompt: a fresh session again, this time with **nine reviewer notes written before any code existed**. Among them:
  - session isolation between threads
  - the model-client factory on `app.state` so the background thread is testable
  - a synchronous entry point so tests need no sleeps
  - the language-keyed summary cache
  - the error policy per error type
  - one-transaction save
  - collecting-stage progress, carried over from the group 4 review
- Result: commits `89bdc02`, `51fe105`; 20/24 tasks; 130 backend + 15 frontend tests. Every digest-generation scenario is mapped to tests. Cost: 36 turns, ~5.4 minutes, ~341K credits.
- Review: no required fixes. Three low-severity items are carried into the next hand-off instead of paying for a separate fix session.
- Lesson: Anticipating the design pitfalls of the hardest group in the prompt again avoided a fix round. Folding low-severity findings into the next group's prompt is cheaper than an immediate fix session.

## 2026-10-03 — Digest history group 6 (Factory Droid, GPT-6 Sol)

- Purpose: Implement tasks 6.1–6.2 and three carried-over group 5 review fixes, without starting group 7.
- Prompt (faithful excerpt): "Implement ONLY task group 6 (tasks 6.1-6.2, digest history) plus three carried-over review items, using the openspec-apply-change skill ... Read digests only from the snapshot tables ... The restart test must create a second app on the same data dir ... no real network, no real API key, no writes outside pytest temp dirs, no fixed sleeps in tests. ... Commit once at the end."
- Outcome: Snapshot-backed history API and reader UI with ordered topics/items and safe links; runner logs unexpected failures with exception text redacted, localizes the fallback topic, and skips items deleted mid-run. Automated coverage includes deletion, restart, language variants, and an all-items-deleted case. Final checks: 142 backend and 19 frontend tests, build and strict OpenSpec validation pass.
- What failed / adjustment: A frontend test expected `getByText('Blog')` to match text split around a date element; it was changed to assert against the containing item. A UTC test expected `+00:00` while FastAPI emitted `Z`; the assertion was corrected. No live model, key, or network was used.

## 2026-10-03 — Group 6 (Factory Droid, fresh session) and review (Claude Code, Opus 5.5)

- Prompt: group 6 tasks plus the three carried-over group 5 findings, each with a required test (for example, a `caplog` test proving the decrypted key never appears in logs).
- Result: commit `083c9df`, 22/24 tasks, 142 backend + 19 frontend tests. Cost: 31 turns, ~3.7 minutes, ~289K credits.
- Review: no required fixes. Reading the code across endpoints, rather than only the new endpoint, found an inconsistency that no per-group test could catch: one endpoint normalized SQLite's naive datetimes to UTC and another did not. Carried into group 7 with one model-layer fix.

## 2026-10-03 — Integration and report group 7 (Factory Droid, GPT-6 Sol)

- Purpose: Finish tasks 7.1–7.2 and fix the two findings carried over from group 6.
- Prompt (faithful excerpt): "Implement task group 7 (7.1 end-to-end API test, 7.2 test report) plus two carried-over review items, using the openspec-apply-change skill ... Fix [timestamp handling] once at the model layer ... keep only http/https entry links ... [test] configure with a mocked provider, preview and confirm a fixture feed, run, digest saved, second run no_new_content, the feed gains one entry ... citations come from stored data ... no real network, no real API key, no writes outside pytest temp dirs, no fixed sleeps in tests."
- Outcome: UTC model type and feed-link guard with regression tests; complete three-run API integration test; report mapping all 48 spec scenarios to tests, with 95% backend statement coverage. Full backend 147 passed, frontend 19 passed, build and strict OpenSpec validation passed.
- What failed / adjustment: Initial integration test injected a model object rather than a factory into the settings dependency; the test failed before any feed work, then passed after changing the override to return a factory. Frontend tests initially could not find Vitest in this new worktree; `npm ci` installed the lockfile dependencies and the suite passed. No real feed/provider check was attempted, per the review hand-off.

## 2026-10-03 — Group 7 (Factory Droid, fresh session) and review (Claude Code, Opus 5.5)

- Prompt: the carried-over fixes come first, so the end-to-end test and the report cover the final code. The test report must map every spec scenario and list any scenario without a test explicitly instead of hiding it.
- Result: commit `65f058a`, 24/24 tasks, 147 backend + 19 frontend tests, test report with 48/48 scenarios mapped. Cost: 29 turns, ~4.2 minutes, ~317K credits.
- Review: Claude did not trust the mapping table. A script checked that every scenario is named and that every cited test exists (57/57). No required fixes.
- Implementation totals for the change: ~3.14M Factory credits across 9 Droid runs. The resumed long session (groups 1–3 plus fixes) cost ~1.94M; the four fresh-session groups (4–7) cost ~1.20M together.

## 2026-10-03 — Manual verification with real DeepSeek and public sources (Claude Code, Opus 5.5, with the user)

- Claude ran the app locally and drove the UI in the built-in browser. The user typed their own DeepSeek key into Settings; Claude never handled it.
- Run 1 failed. Claude did not guess at the cause:
  1. It read the stored run and item state from the database (read-only): 4 of 11 summaries and the grouping call were empty.
  2. It confirmed in DeepSeek's docs that thinking mode is on by default.
  3. It tested the hypothesis with an uncommitted local change that raised the budgets. Run 2 succeeded.
- This was the most valuable test of the change. A design assumption (512-token summaries) passed 147 mocked tests but broke against the real provider's default behavior. Real sources also showed untitled social posts, a misleading notice, and metadata-heavy summaries.
- Process: findings became spec requirements and tasks 8.1–8.4 on the branch, then went to a fresh Droid session (user's choice). Larger issues (Reddit link posts, rate limiting, a thinking toggle) were deferred to the next change.
- Lesson: Mocked tests verify the contract we imagined. One short real run per change against the real provider and real sources is necessary, and it should happen before the plan is considered done.

## 2026-10-03 — Group 8 manual-verification fixes (Factory Droid, GPT-6 Sol)

- Purpose: Implement only tasks 8.1–8.4 after the real-source/DeepSeek review, without repeating live verification.
- Prompt (user, faithful excerpt): "Implement ONLY group 8, using the openspec-apply-change skill, then stop. ... Use exactly the budgets in design.md D3. ... titles from the plain text. ... Follow the new rule in D5 exactly. ... prompt wording only; keep 'json' and the example output; keep the language instruction. ... no real network, no real API key, no writes outside pytest temp dirs, no fixed sleeps. ... Commit once at the end."
- Outcome: Raised model output budgets, derived readable titles from untitled posts without changing the identity fallback, limited the whole-site notice to articles and deeper-page origin probes, and added substance-focused summary prompt rules. Added six backend tests (153 total); mapped all 52 spec scenarios. Backend/frontend tests, build, and strict validation passed using offline fixtures, mocks, and fake clients.
- What failed / adjustment: The first title test expected truncation too early; corrected its expected word-boundary title. An initial mapping audit counted table headers; restricted it to actual spec names, then 52/52 mapped with 85 valid backend references. `npm ci` was needed in this new worktree before frontend tests. Real-provider output quality remains for reviewer/user re-test, not inferred from prompt assertions.

## 2026-10-03 — Group 8 (Factory Droid, fresh session), review, and re-test (Claude Code, Opus 5.5)

- Droid: commit `d2d2d94`, 28/28 tasks, 153 backend + 19 frontend tests. Cost: 31 turns, ~3 minutes, ~263K credits.
- Review: Claude re-ran everything and re-audited the report by script (52/52 scenarios, 64 cited tests exist). Code matched design D3/D5.
- Re-test on real sources with the user's stored key:
  - Every manual-test finding was confirmed fixed (titles, notice, metadata-free summaries, budgets).
  - The "delete a source keeps old digests" scenario was confirmed on real data.
  - One new real-world issue: confirming a Reddit source right after preview gets rate-limited. Deferred.
- Correction: Claude had reported "6 topics" for run 2; a recount showed 5. Fixed in the test report.
- Final implementation cost for the change: ~3.40M Factory credits across 10 Droid runs.
- Archive (user approved the merge): `openspec archive add-core-digest-flow -y` merged the deltas into five main specs (32 requirements; `openspec validate --specs --strict` passes; no placeholder Purposes). It moved the change to `openspec/changes/archive/2026-10-03-add-core-digest-flow/`. The README was updated from "scaffold" wording to the current state.

## 2026-10-04 — `improve-source-reliability`: research, scope change, implementation, review (Claude Code, Opus 5.5; Factory Droid, GPT-6 Sol)

- **Research changed the scope.** A subagent asked to verify Reddit's RSS structure and rate-limit rules found that Reddit will stop all RSS on 2026-11-13. Claude confirmed this against the TechCrunch report before relying on it. The user then dropped the Reddit link-post extractor (#2, closed) and kept only generic fetch reliability.
- Proposals: in-process handling (chosen) vs persistent cooldowns. The user asked for both proposals' downsides before deciding; Claude listed six for each.
- Droid, fresh session, with seven reviewer notes anticipating pitfalls (backward-compatible `safe_fetch`, no real sleeps, locks, cache key = final URL, one shared message prefix, `AppError` details, UA contact validation):
  - 9/9 tasks, 4 commits, 197 backend + 22 frontend tests
  - 58 turns, ~6.6 minutes, ~590K credits
- Review: no required fixes; two low-severity notes recorded.
- Live check without a model key:
  - a real server saw the CatchUp User-Agent
  - Reddit preview → immediate confirm succeeded with 0 extra feed requests; this step had failed before the change
- Lesson: Asking a research subagent to verify the current external rules, not just the data format, surfaced a platform shutdown that made half of the planned work obsolete. Checking it before planning saved implementing a feature with a six-week lifespan.
- Archive (user approved the merge): `openspec archive improve-source-reliability -y` added 5 requirements to the main specs (`source-management` now 8, `content-collection` now 8; strict validation passes). It moved the change to `openspec/changes/archive/2026-10-04-improve-source-reliability/`.
- **Process slip (merge):** the user approved "archive, wait for CI, then merge". To avoid polling CI, Claude ran `gh pr merge --merge --auto`. The repository has no branch protection or required checks, so GitHub merged immediately instead of waiting (merge commit `bd127f3` at 08:36:05Z). Claude checked right away: both CI runs for the merged head `a7c5efa` had completed successfully at about the same time, so the merged code was the tested code. The slip was reported to the user as it happened.
  - Lesson: `--auto` only waits when the branch requires status checks. Either require the CI checks on `main` or merge only after reading a green status.

## 2026-10-05 — `add-docker-packaging`: review and real Docker run (Claude Code, Opus 5.5; Factory Droid, GPT-6 Sol)

- Droid, fresh session, with eight reviewer notes:
  - `env.py` becomes importable
  - `Settings` defaults
  - venv location and a matching Python path
  - `tsc` needs test files in the build context
  - chown `/data` before `VOLUME`
  - no curl or jq
  - keep the CI job names that branch protection requires
  - never push or tag

  Result: 11/11 tasks, 206 backend tests, an image of 407 MiB, ~510K credits. A small fix round cost ~139K.
- Droid itself flagged a possible data-loss path: an `.env` with `CATCHUP_DATA_DIR=./data` overriding `/data`. **Claude tested it instead of accepting or dismissing it.** The database still landed on `/data`, but only because the image has no `WORKDIR` (cwd `/`). The verdict was downgraded from "must" to "should", and the fix still went in: compose pins the variable, and `docker run` docs pass `-e`. Lesson: test a claimed risk before ranking it. Here the reasoning was right about the fragility and wrong about the current impact.
- Real run on the user's Mac, following the README literally:
  - healthy in 5 s, loopback-only port
  - the user entered their key; a Chinese digest was generated in ~30 s
  - data identical across restart and container recreation, and the stored key still decrypted
- Archive (user approved the merge and a `v0.1.0` release): `openspec archive add-docker-packaging -y` created the main spec `local-deployment` (7 requirements). The change moved to `openspec/changes/archive/2026-10-04-add-docker-packaging/`.

## 2026-10-05 — Merge and first release `v0.1.0` (Claude Code, Opus 5.5)

- The first CI run on PR #20 failed because `astral-sh/setup-uv@v10` does not exist (only full version tags). Claude checked every action reference against the GitHub API, found only this one missing, and pinned `v10.2.0` itself as a one-line fix.
- Auto-merge was refused at first because the repository did not allow it. This also explains why PR #19 merged immediately: with no required checks, `--auto` falls back to a direct merge. With the user's approval, Claude enabled auto-merge and made `docker` a required check (D-012). Claude then checked the check-run timestamps to confirm the merge happened only after CI passed.
- With the user's approval, Claude published release `v0.1.0` at `b5fec1a` with release notes (highlights, run instructions, known limitations). The first attempt failed because a release target must be a full SHA, not a short one.
- Lesson: Every remote assumption failed once and needed a check against the live service: action tag aliases, repository merge settings, and release target formats. Local linting does not cover them.
- Post-merge check (2026-10-05): the release workflows succeeded. An anonymous registry query showed the package is public with all four tags. Both architectures are present, and the published image passed the smoke test. Claude almost misread the image labels: a local `compose --build` had tagged its own build with the published name. Lesson: before inspecting a "published" image, remove any local tag with the same name.

## 2026-10-04 — `add-podcast-and-video-sources`: merge decision and supplementary research (Claude Code, Opus 5.5, with a general-purpose subagent)

- Prompt (user, in Chinese, excerpt): "Merge #5 and #6, then start the supplementary research", covering `<podcast:transcript>` formats, iTunes Lookup, DeepSeek context and output limits, and token counts for the 3.6-hour sample under different processing approaches. Before this, the user had made long-transcript truncation a must-handle item and asked whether their Bilibili workflow (a speech-to-text model on the audio, then an AI summary) would work for YouTube.
- Claude renamed the change folder, moved #5 to In Progress on the board, and ran `/reppit-research` in OpenSpec mode. A background subagent fetched the podcast namespace spec, six real transcript feeds, five feeds without transcripts, feedparser behavior, iTunes Lookup, and adoption statistics. In parallel, Claude read the code path and ran the current `discover()` live against podcast URLs.
- Claude re-checked the two subagent findings that affect the design before writing them down:
  - Feed sizes against the 5 MB fetch limit: The Daily's full archive is 20.3 MB, and The Vergecast fails on main today.
  - feedparser keeping only the last `<podcast:transcript>` tag: 4 tags in the raw XML, 1 returned.
- Token counts: Claude first asked to download DeepSeek's 1.9 MB offline tokenizer. The user asked why token counts were needed. Claude explained that they decide between a single call and chunking, and pointed out that `deepseek-flash`'s 1M-token context makes exact counts unnecessary. With the user's agreement, it used DeepSeek's documented character ratios instead: about 51k tokens for the 3.6-hour sample. Lesson: check the limit that drives the decision before asking for precise measurements.
- Speech-to-text facts were recorded as context only. No audio was downloaded. YouTube's terms forbid downloading, and the handoff does not commit to transcription.
- Date correction: entries above dated 2026-10-05 actually happened on 2026-10-04 (local time, per commit timestamps).

## 2026-10-05 — `add-podcast-and-video-sources`: proposals, amendments, and plan (Claude Code, Opus 5.5)

- `/reppit-proposal` produced two proposals in `design.md` (`be46efb`):
  - P1: transcripts in `content_text`; a single call with a chunking fallback; global YouTube settings; no speech-to-text.
  - P2: a digest-time provider chain; always chunked; speech-to-text for podcast audio through a user-supplied key; ffmpeg in the image.

  Claude recommended P1.
- The user chose P1 and, before planning, sent five amendments (translated excerpt):
  - "change 'not summarized' into a positive 'Creator updates' section … grouped by creator / show … no model call"
  - "fix the contradiction between late transcripts and no repeats: podcast episodes wait up to 7 days … each item appears in only one digest"
  - "do not hard-code the single-call limit: derive it from `context_window` returned by `/models`; fall back to 60,000 characters"
  - "the captions library bypasses safe_fetch's spacing: fetch videos sequentially with the same host spacer, cap videos per run, record 'blocked' separately from 'no captions'"
  - "prefer the video's original-language captions (manual > auto), never machine-translated"
- **What the amendments fixed.** The user found a real flaw in Claude's design: "listed once" and "re-checked for 7 days" contradicted each other under the existing delivered/pending states. Claude had also left the single-call budget as a fixed number that suited only large-context models. Lesson: when a design adds a waiting state, walk through an item's full lifecycle across several runs before proposing it.
- **What Claude added while revising, and the user accepted:**
  - a fifth reason, `captions_failed`
  - stopping caption requests after the first block
  - resolving transcripts in the run's check phase instead of at confirm (confirming 5 videos would otherwise take 15+ s)
  - renaming the override to `CATCHUP_SINGLE_CALL_CHARS`, because `.env.example` hard-codes `CATCHUP_MAX_ITEM_CHARS=20000`, and copied configs would silently override the derived budget
- **Before writing the budget design,** Claude checked DeepSeek's List Models docs: `context_window` and `max_output_tokens` are documented. The live response is still to be verified in review.
- **`/reppit-plan` output:**
  - `proposal.md`
  - deltas for `source-management`, `content-collection`, `digest-generation`, `model-settings`, and a new `transcripts` capability
  - the final `design.md` (D1–D11)
  - `tasks.md` (7 groups, 21 tasks)

  `openspec validate --strict` passes.
- **A drafting slip, caught before validation:** spec wording used "MAY" and "may" for normative rules, which the OpenSpec instructions forbid. Claude rewrote the sentences with SHALL/MUST.
- **Independent plan review.** The user asked for a separate conversation to review the plan, and said its suggestions should not be accepted wholesale: each should be checked against the code before any change. Claude ran a fresh general-purpose subagent with no access to the planning conversation. Its instructions were to report only evidence-backed problems, without editing files.
  - The reviewer reported 20 findings: 1 blocker, 5 major, 14 minor or unverified.
- **Claude's verification of each finding:**
  - Code reads:
    - `api/sources.py:90` (confirm's cache-miss fetch, missing from the plan's call sites)
    - `models.py:38` (the table is `model_config`, not `model_configs`)
    - `api/runs.py:11` (the route is `/api/digest-runs`)
    - `feed_cache.py:12` (50 cached bodies × 32 MB)
    - `Settings.tsx:83` (a preferences save sends only `digest_language`)
    - `safe_fetch.py:111` (`trust_env=False`)
    - `summarize.py:53` (a stale cached summary would be reused)
    - the test fakes' locations
  - Experiments in the scratchpad:
    - lxml without `recover` rejects a feed containing `&nbsp;`; with `recover=True` it finds the transcript tag
    - leading whitespace before `<?xml` fails
    - youtube-transcript-api 1.2.4's `TranscriptList.build` indexes YouTube JSON directly, so a format change raises a plain `KeyError`
- **Accepted (17, all confirmed). The main fixes:**
  - Expiry is computed in memory, written only in the save transaction, and `no_transcript` is included in selection. Before, a run failing after expiry could strand an episode forever.
  - YouTube captions moved to a separate pass after all checks, oldest first, keyed by `identity_key`. Before, a deferred video that dropped out of its channel's 15-entry feed was never handled.
  - Every podcast status without a transcript now expires.
  - Catch-all error containment per item. Before, an unexpected library error would fail every future run.
  - lxml `recover=True` with a feedparser fallback.
  - confirm uses the feed limit, and the cache skips bodies over 5 MB.
  - A stricter podcast classification (iTunes metadata or a majority of audio enclosures), never downgraded.
  - Selection keyed by status; strict context-window parsing.
  - Optional preference fields; `trust_env=False`.
  - Wait days stored on the digest, with a `digest-history` delta added.
  - Spec wording fixes; the original-language rule relaxed to best effort without an auto-generated track.
- **Not adopted:**
  - Cutting token usage and the long-transcript format as "not requested": both were part of Proposal 1, which the user chose. This finding was factually wrong.
  - A lower fallback than 60,000 characters: the user set that value; small local models are documented instead.
- **Raised with the user instead of changed:** whether newly uploaded videos without auto-captions yet deserve a grace period (unverified; it would change the user's "list once immediately" rule).
- Lesson: the reviewer's highest-value findings were lifecycle bugs across runs and failure paths, which the planner had walked only on the happy path. Checking every claim also caught one wrong claim, which would have removed agreed scope.
- **Second review round.** The user approved the caption wait suggested by the reviewer's #17, and asked for the revised plan to be re-checked by the same review conversation. Claude added `caption_wait`/`unplayable_wait` with `CATCHUP_CAPTION_WAIT_HOURS` (default 24). Reading the library source (1.2.4) showed why both cases must wait:
  - `TranscriptsDisabled` is raised whenever `captionTracks` is missing, so uploader-disabled and not-yet-generated captions cannot be told apart.
  - Upcoming premieres raise `VideoUnplayable`.
- **The re-review found no blockers.**
  - It confirmed 16 earlier findings resolved and reported 2 major and 6 minor new findings.
  - Claude verified the main one by experiment: feedparser maps `itunes:author` to `author`, so iTunes metadata cannot be detected from its output. Live Substack feeds (astralcodexten.com, noahpinion.blog) declare the iTunes namespace and `itunes:author`/`owner`/`block` with zero audio enclosures, so under the planned "iTunes metadata" rule these newsletters would have become permanent podcasts, with every post sent to Creator updates.
  - The fix goes further than the reviewer's suggestion: classification uses only the share of audio enclosures, and non-audio entries of a podcast source are handled as text (`text` status). A misclassification therefore cannot hide text posts.
- **The other findings, applied after checking against the plan text:**
  - D8 step 2 now specifies what happens to wait, NULL, and `captions_off` items when the cap or a block is hit.
  - A false "every status is in the summarize or creator-update set" sentence was corrected.
  - The order "oldest" is defined as `discovered_at`, then `id` (all entries of one check share one timestamp, `collection.py:64`).
  - The waiting and deferred message texts are defined.
  - The feedparser fallback now applies after any lxml failure.
  - Toggle edge cases are documented, and `captions_off` items are fetched again once the setting is on.
  - The cap-starvation risk is noted.
- Lesson: a reviewer's "suspected, could not verify" item (Substack) turned out to be the most consequential once checked live. Unverified findings deserve a quick experiment, not a dismissal.
