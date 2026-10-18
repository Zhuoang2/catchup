# AI Tool Usage Log

Real usage records for the technical spec, alpha reflection, and final report. Each entry: date, tool/model, purpose, prompt (verbatim or faithful excerpt), outcome, problems, adjustment. The user often wrote prompts in Chinese; those prompts are quoted here in English translation.

## 2026-10-07 — UI redesign final review fixes (Factory Droid, GPT-6 Sol)

- Prompt (faithful excerpt): "Implement tasks 13.1 through 13.12 in order: use diagnosing-bugs for 13.1-13.6 (show the failing check first, then fix, keep the regression test) and tdd for 13.7-13.11 ... check off a task only after its verification passes; commit after each task; do not edit proposal.md, design.md, specs/, or prototypes/; add no runtime dependencies; keep tests free of real network and real sleeps; never push, tag, or open a PR."
- Outcome: Corrected run/digest snapshot counts, source-load and first-source states, one-time run failure announcement, per-screen titles, offline-page refresh, URL wrapping, hover contrast, copy and digest navigation. Strengthened tests were mutation-checked. Eleven task commits plus the final checks/report commit; 357 backend tests (96% coverage), 117 frontend tests, build, strict OpenSpec validation and local Docker build/smoke passed. See `test-report-redesign-ui-ux.md` for red checks and full results.
- Problems / adjustment: This worktree lacked Vitest; installed locked frontend dependencies with `npm ci`. A first digest-title fixture mixed route id 7 with returned id 3; aligned them. A report unittest initially expected the prior four script tests rather than five after adding itself; corrected the assertion. The root-level unittest discover found zero tests; reran from `frontend/`. No external provider/feed was used in tests and no code was published.

## 2026-10-06 — UI redesign review fixes (Factory Droid)

- Prompt (faithful excerpt): "Implement approved review fixes 10.1–10.8 in order ... verify and commit after each task ... use the effective C7 cascade ... do not edit plans, specs or prototypes, add runtime dependencies, make real network calls or sleeps in tests, or push."
- Outcome: Replaced per-digest History requests with constant-query list previews, mapped saved languages to BCP-47, kept Generate responsive across independent request failures, scoped form errors, restored delete focus, ported missing C7 rules, and aligned date/markup/offline styling. Final results: 354 backend tests (96% coverage), 79 frontend tests (41 axe scans), build, strict OpenSpec validation, and local Docker build/smoke passed. Details and unperformed manual checks are in `test-report-redesign-ui-ux.md`.
- Problems / adjustment: This worktree needed `npm ci` and a locked backend environment. A Generate test initially asserted token text as a whole node and another waited on an always-visible heading; both were corrected to wait for the relevant rendered state. A real 320 px check found the fourth nav link overflowing by 2 px because the narrow padding rule lost to a more specific rule; matching specificity removed the overflow. An audit listed nine residual prototype-only/generic classes rather than treating them as unported live styles. No provider, feed or production deployment was contacted.

## 2026-10-06 — UI redesign implementation (Factory Droid)

- Prompt (faithful excerpt): "Implement all 14 tasks, 1.1–9.1, for OpenSpec `redesign-ui-ux` ... verify each task before checking it and commit after each task group ... do not edit proposal.md, design.md, spec deltas, or prototypes; do not push, tag, or open a PR." After two stops on plan contradictions, the user approved the corrections in `e77e098` and `e05dada` and instructed Droid to stop only for genuinely blocking contradictions, choosing the design/prototype-consistent reading for minor ambiguities.
- Outcome: Added snapshot migration and API fields, the C7 token system and shared React shell, redesigned Digest/History/Generate/Sources/Settings, install assets and offline-only service worker, plus tests and Docker smoke. Each of groups 1–8 was committed after its checks; the full results and remaining manual review are in `test-report-redesign-ui-ux.md`. The final automated run passed 352 backend tests (96% coverage), 56 frontend tests, build, strict validation, and Docker build/smoke.
- Problems / adjustment: Installed locked frontend dependencies after Vitest was missing. Replaced a Vitest-incompatible raw CSS import with a filesystem read; jsdom cannot paint for axe contrast, so token contrast is tested numerically. Fixed Sources confirmation list semantics after axe flagged `role="group"` on an `li`. The first Docker smoke attempt exposed unreadable 600-mode static files in the non-root image; set public text assets to 644, rebuilt, and reran green. Browser spot checks covered the first-run layout, narrow Settings/Sources, and the real offline fallback, but the full visual parity and native install review remain for Claude.

## 2026-10-05 — Podcast and video sources, manual-test fixes (Factory Droid)

- Prompt (faithful excerpt): "Manual-test round for add-podcast-and-video-sources ... two new commits ... track choice ... pull the branch's latest commit first, then implement tasks 9.1-9.2 in order ... no real network in tests, no real sleeps ... commit once after group 9."
- Outcome: Starting worktree was already clean at `fd95f85`; no remote branch existed to pull. Replaced first-generated-track guessing with the pinned YouTube library's player caption JSON and default audio/caption indices, falling back to ordered public track heuristics when metadata is invalid or missing. Offline fakes reproduce the 21-track auto-dub case. Full checks: 349 backend tests at 96% coverage, 35 frontend tests, build, strict OpenSpec validation, Docker build and smoke passed.
- Adjustment: Installed the missing backend and frontend dependencies from their lockfiles. No test required live YouTube or model access; the manual observations came from the user's review.

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
- Prompt (user, translated from Chinese):

  > Please take over the CatchUp project. First read CLAUDE.md, docs/handoff.md, docs/proposal.md, and the Final Project Description in the project folder to understand the product idea and the course requirements. Also read ~/.codex/AGENTS.md on this machine.
  > The original Final Project Description is authoritative for the course requirements; the course summary in the handoff file is for reference only. If you find conflicts between the materials, point them out explicitly.
  > The confirmed product direction does not need another brainstorm. Distinguish confirmed requirements, later features, and undecided technical details. First restate your understanding briefly; then, given the course deliverables and deadlines, propose a recommended technical approach and a phased implementation plan, and then move the core flow forward. Ask me only about key open items that really affect the implementation.
  > During development, keep the requirement changes, design decisions, test results, and real examples of AI tool use, prompt adjustments, and successes or failures, to build up material for the technical spec, the alpha release, and the final report.

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

- Prompts (user, verbatim, with English translations):
  - "Also, your point 1, long-transcript truncation, is important; handle it in the plan as well."
  - "Oh, don't merge yet. Try other ways of handling YouTube videos. For Bilibili videos I used a speech-to-text model to get captions of what is said, then had an AI summarize them. Can this pipeline work on YouTube?"
  - "OK, I understand. Then let's merge #5 and #6 first and start the supplementary research."

  The research covered `<podcast:transcript>` formats, iTunes Lookup, DeepSeek context and output limits, and token counts for the 3.6-hour sample under different processing approaches.
- Claude renamed the change folder, moved #5 to In Progress on the board, and ran `/reppit-research` in OpenSpec mode. A background subagent fetched the podcast namespace spec, six real transcript feeds, five feeds without transcripts, feedparser behavior, iTunes Lookup, and adoption statistics. In parallel, Claude read the code path and ran the current `discover()` live against podcast URLs.
- Claude re-checked the two subagent findings that affect the design before writing them down:
  - Feed sizes against the 5 MB fetch limit: The Daily's full archive is 20.3 MB, and The Vergecast fails on main today.
  - feedparser keeping only the last `<podcast:transcript>` tag: 4 tags in the raw XML, 1 returned.
- Token counts: Claude first asked to download DeepSeek's 1.9 MB offline tokenizer. The user asked "Why do you need to know the token count?" Claude explained that they decide between a single call and chunking, and pointed out that `deepseek-flash`'s 1M-token context makes exact counts unnecessary. With the user's agreement, it used DeepSeek's documented character ratios instead: about 51k tokens for the 3.6-hour sample. Lesson: check the limit that drives the decision before asking for precise measurements.
- Speech-to-text facts were recorded as context only. No audio was downloaded. YouTube's terms forbid downloading, and the handoff does not commit to transcription.
- Date correction: entries above dated 2026-10-05 actually happened on 2026-10-04 (local time, per commit timestamps).

## 2026-10-05 — `add-podcast-and-video-sources`: proposals, amendments, and plan (Claude Code, Opus 5.5)

- `/reppit-proposal` produced two proposals in `design.md` (`be46efb`):
  - P1: transcripts in `content_text`; a single call with a chunking fallback; global YouTube settings; no speech-to-text.
  - P2: a digest-time provider chain; always chunked; speech-to-text for podcast audio through a user-supplied key; ffmpeg in the image.

  Claude recommended P1.
- The user chose P1 and, before planning, sent five amendments (verbatim excerpts, with English translations):
  - "Turn 'not summarized (no captions)' into a positive 'Creator updates' section after the topic summaries … grouped by creator / show … no model call."
  - "Fix the contradiction between 'late transcripts' and 'no repeats' … a podcast item without a transcript stays out of digests and waits up to 7 days … every item appears in exactly one digest."
  - "Do not hard-code the single-call limit … derive it from the `context_window` returned by `/models`; fall back to 60,000 characters."
  - "It has no SSRF risk, but it bypasses safe_fetch's spacing and rate limiting … fetch videos one by one with the same host spacer; cap the videos per run; record and show 'blocked by YouTube' separately from 'the video has no captions'."
  - "Prefer captions in the video's original language (manual > auto), never YouTube's machine-translated captions; the model handles the summary language."
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
- **Independent plan review.** The user asked: "Open another conversation to review your plan; don't accept its suggestions wholesale; verify them against its answers, and change things only once a problem is confirmed". Claude ran a fresh general-purpose subagent with no access to the planning conversation. Its instructions were to report only evidence-backed problems, without editing files.
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
- **Second review round.** The user replied "Add the waiting period, then have the review conversation check again". Claude added `caption_wait`/`unplayable_wait` with `CATCHUP_CAPTION_WAIT_HOURS` (default 24). Reading the library source (1.2.4) showed why both cases must wait:
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

## 2026-10-05 — `add-podcast-and-video-sources`: implementation review and fix round (Claude Code, Opus 5.5; Factory Droid, fresh session `72e07ca6`)

- **Droid's first pass:**
  - 21/21 tasks in 7 commits, ~2.19M credits.
  - Claude re-ran everything in a separate worktree: 327 backend tests (96% coverage), 34 frontend tests, the build, `openspec validate --strict`, and the Docker build plus smoke test (8/8), all matching Droid's report.
  - Live checks:
    - The Vergecast (6.2 MB) previews as a podcast.
    - Apple show and episode URLs resolve, with the whole-show notice.
    - astralcodexten.com stays a feed.
    - A YouTube channel is recognized.
    - A Buzzsprout VTT transcript converts to 35,559 characters with speakers.
    - Captions for `s7d2d8FhevU` come back at 172,818 characters, with the spacer called before each of the library's 3 requests.
- **Droid's own deviation, tested rather than assumed.** Droid skipped lxml for any document with a DOCTYPE, claiming libxml expands attribute entities even with `resolve_entities=False`. Claude's experiment confirmed it (`url="https://h/&x;.vtt"` → `EXPANDED`). This was a security gap the plan had missed.
- **Code review: Claude plus an independent subagent.** The subagent had to prove each bug with a script. Claude re-ran every proof and checked the most consequential one against 10 live podcast feeds:
  - **Shared links:** The Daily has 64 entries with 1 distinct `<link>`, and a Captivate show has 121 with 1. The v0.1 link dedup therefore recorded only the first episode, ever, and the new transcript matching gave episodes a sibling's transcript.
  - CJK transcripts without whitespace failed to split.
  - `SummaryText` dropped lines.
  - Word-level JSON and caption snippets became one word per paragraph.
  - A UTF-16 feed bypassed the DOCTYPE byte check.
  - Nits: redirect spacing, language matching, the namespace prefix, part size, 3-digit hours, group order.
- **Fix round.** With the user's approval, Claude added D12, task group 8, and spec rules (shared links; transcript ownership; internal DTD entities) on the branch (`ab40245`), then resumed the same Droid session with the evidence. Droid's fix (`c89fa23`, ~0.82M credits; the reported credits are cumulative) passes 342 backend and 35 frontend tests. Claude re-verified:
  - The reviewer's scripts now give the correct results.
  - A live preview and confirm of The Daily via the Apple URL records all 64 episodes (5 pending, 59 baseline); before the fix, only 1.
  - A live check phase gives The Daily `waiting` (no tags) and Buzzsprout `found` (35,559 characters).
  - Docker smoke 8/8.
- **A reviewer script misled once.** The public-DOCTYPE script inserted a second DOCTYPE into a fixture that already had one, so it reported 1 candidate. Reading the script resolved it: the fixture alone yields 4. Lesson: when a proof disagrees with a passing test, read the proof too.

## 2026-10-05 — `add-podcast-and-video-sources`: manual test with the user (Claude Code, Opus 5.5; Factory Droid session `72e07ca6`)

- **Setup.** The image was built from the branch and run on `127.0.0.1:8000` with a throwaway volume. The user entered their DeepSeek key in Settings; Claude never handled it.
- **Results:**
  - Buzzsprout: a 35k-character transcript was summarized as an overview plus 6 key points, in zh-Hans.
  - The Daily (added through its Apple URL): 64 episodes recorded, and 5 waiting for transcripts.
  - Token totals of 8,663/1,893 matched the DeepSeek usage page (checked by the user).
  - The live `/models` response gave `context_window` 1,048,576, which closed the plan's only open question.
  - With captions off, a Creator-updates-only digest listed the Google for Developers video with `captions_off`; the Short did not appear.
- **YouTube RSS outage.** Every channel's `feeds/videos.xml` returned 404 for more than 40 minutes, with any User-Agent. This is the intermittent outage noted in #6.
  - For the captions-on step, with the user's choice ("option B"), Claude reset the already delivered test video to `to_fetch` in the throwaway database, which simulates a new upload. The caption fetch and summary then ran for real.
- **The test found two defects:**
  - **Wrong caption language.** CatchUp summarized **Arabic** captions of an English video. YouTube had listed an auto-generated track for each of 20 auto-dub languages, Arabic first, which refuted the plan's unverified assumption that "the first auto-generated track is the original".
    - Claude inspected the player data: `audioTracks[defaultAudioTrackIndex]` is `en-US.4` (dubs are `.10`), and its `defaultCaptionTrackIndex` points at the manual English track.
    - The user approved the revised rule (YouTube's default-audio caption, then public heuristics, never a guess). Claude planned it (`fd95f85`, task group 9), and Droid implemented it (`1ce6342`, ~0.48M credits).
    - The retest picked the 893-character manual English track. The summary now uses the original name "Journal Receipts" instead of a translated one.
  - **Misleading token display.** Runs without model calls showed "Tokens: not reported". Claude fixed it directly as a small change with tests and a spec scenario (`40ff3d2`); the retest shows 0/0.
- **Follow-ups (not in this change):**
  - A 404 on a declared feed is reported as "The declared feed could not be parsed" (pre-existing). Filed as a new issue.
  - One confirm returned 422 and could not be reproduced. The cache was verified with a stable feed; the likely cause is the YouTube 404 flapping.
- Lesson: an assumption the plan explicitly marked "unverified" failed in the first real test. Marking it made the cause quick to find. Testing with a real multi-language video earlier, during research, would have caught it before implementation.

## 2026-10-05 to 2026-10-06 — `redesign-ui-ux`: research, design brief, and prototype rounds (Claude Code, Opus 5.5, with the user)

- **Kickoff.** After D-014 (local web app, installable as a PWA), the user asked: "I think the next step could be designing the UI and UX first. What do you think?"
  - `/reppit-research` documented the frontend as it is: five pages, about 620 lines, a 4-line stylesheet, every state and API shape, and how FastAPI serves `dist/`.
  - It also checked the PWA facts: Chrome install criteria; localhost counts as a secure context; Safari "Add to Dock"; no Firefox install on macOS; `.webmanifest` MIME type in the published image.
  - Claude then wrote `design-brief.md` for Claude Design (claude.ai/design), with real zh-Hans sample content from the manual test.
- **Claude Design was unavailable.** The user reported: "My account doesn't seem to have the Design feature; any recommendation among these plugins?"
  - Claude recommended the Design plugin for critique and accessibility later, and HTML prototypes now.
  - The user installed the plugin on claude.ai. Its skills did not load into the running session, so it was deferred to a new session.
- **Round 1.** The user asked: "OK, make five; start the prototypes".
  - Claude built a shared renderer (`shared/data.js`, `render.js`, `base.css`): all six screens and 22 states, with a control bar for direction, screen, state, theme, and a 420 px width, using container queries.
  - It built five direction stylesheets: A quiet reader, B focused workspace, C morning briefing, D soft cards, E native desktop.
  - A token contrast script found 4 AA misses, which were fixed.
  - Invented article titles were replaced with labeled placeholders.
- **The user chose C:** "I prefer C, the morning-briefing newspaper style". Via a question, the user decided:
  - error color separate from the brand red
  - a masthead with date and edition number
  - two body-font versions to compare (C2)
- **The user asked for more variants:** "They feel about the same; redesign a few versions using C as the template".
  - Claude built C3 Broadsheet, C4 Salmon paper, C5 Tabloid, and C6 Swiss grid.
  - It fixed narrow-window navigation, which vanished in the C family, and disabled-button specificity.
  - It also fixed its own contrast script, which merged dark-theme variables in the wrong cascade order.
- **"C3 does look good, but something feels off"**. Claude diagnosed six causes from a full-size screenshot:
  - two-column splits of short summaries
  - justified mixed CJK/Latin text stretching letter spacing
  - a CJK drop cap
  - three typefaces, including a system sans inherited from C
  - about eight horizontal rules in the first screen
  - a web-style TOC sidebar

  The fix was C3b.
- **"C3b's body is a different width from everything else; learn from newspaper websites"**.
  - nytimes.com was blocked in the browser pane, and the hidden pane could not take screenshots, so Claude measured layouts with JavaScript instead:
    - Guardian front: a 1300 px container, 16×60 px columns, a 20 px gap, a 3-column section-title column, and 1 px column rules.
    - Guardian article: a 220 px meta column, a 620 px (8-column) centre column that is aligned, not centered, and a 4-column rail.
    - FT: a 1228 px container, a centered logo, and left-aligned sections.
  - The result is C7: one container, 12 columns, topic section rows with the title in columns 1–3 and newspaper columns of items.
- **"These parts not being centered doesn't look good, does it?"**, about Settings.
  - Claude kept the grid alignment rather than centering, which would reintroduce C3b's misaligned edges.
  - It filled the width the way newspaper sites do: a 4-column rail with a rule on Generate, Sources, and History, and Settings as section rows with margin notes.
- **The user settled:** "OK, go with C7 for now; commit the prototypes".
- **Failures and lessons:**
  - A hash-only navigation does not reload the page, so CSS edits looked unapplied twice. Claude switched the preview server to `Cache-Control: no-store`, reloaded explicitly, and confirmed computed styles before concluding anything.
  - The contrast script initially got the CSS cascade wrong. Re-deriving the merge order from CSS specificity found two more misses.
  - Measuring real sites with JavaScript produced concrete numbers (container, columns, column widths) that a screenshot alone would not. Those numbers settled the "centered or aligned" question.
- **Design plugin review of C7 (2026-10-06).** The user asked: "In a new session, have the Design plugin run a design critique and an accessibility check on C7; check the results when it finishes".
  - In the new session the plugin skills loaded. Claude ran them through an independent subagent (`design:design-critique`, then `design:accessibility-review`) that had no access to the design discussion. The plugin's own MCP connectors (Figma, Notion, …) needed authorization and were not used.
  - **Findings:** 0 critical, 12 major critique findings, and 15 WCAG 2.1 AA issues (7 major, 8 minor), each with a measurement or a CSS selector.
  - **Claude's verification** re-measured the key ones and confirmed them all: `--subtle` 4.15:1; switch track 1.24:1; error ≈ warn; the first topic at 70% of the viewport; "No. 3" vs "No. 1"; no `lang` on Chinese text; scroll without focus; a live region that disappears; dates a day early.
  - **Own errors the review exposed:**
    - Claude's earlier contrast script had used 3:1 for informative `--subtle` text.
    - Its own "error separate from brand red" fix had made error nearly identical to warn.
    - Its margin-note placement put the YouTube risk note about 550 px from its toggle. The reviewer was right to reverse this.
  - **The user approved the fix plan:** "OK, change it according to this plan".
  - **Fixes applied** to the shared renderer and the C-family styles (listed in `openspec/changes/redesign-ui-ux/design-review-c7.md`, "Resolution"). They were re-verified by measurement:
    - the first topic now starts at 45% of the viewport
    - the narrow header shrank from 250 to 113 px
    - focus moves to `#main` and `#t0`
    - 12 `lang="zh-Hans"` elements
    - the switch hit area is 220×26 px
    - a single primary action per Generate state
    - strict contrast passes in both themes
- **Proposal and plan (2026-10-06).** `/reppit-proposal` compared two approaches. P1 ported the prototype CSS with a minimal service worker; P2 used CSS Modules, Radix, and a Workbox precache. Before proposing, Claude found that saved digests lack a language and item source kinds (`models.py:128-161`), which C7 needs for `lang` and kind icons, so both proposals included migration `0003`.
  - The user replied: "Choose Proposal 1, following your recommendations; commit, then start /reppit-plan".
  - `/reppit-plan` wrote `proposal.md`, three spec deltas (new `user-interface`; modified `local-deployment` and `digest-history`), the final `design.md` (D1–D8, with the effective C7 token table extracted programmatically from the prototype cascade), and `tasks.md` (9 groups, 14 tasks). `openspec validate --strict` passes.
- **Droid run 1 stopped on the plan (2026-10-06).** After the user approved the plan ("No problem, go ahead"), Claude committed it (`3fe19a6`) and launched Factory Droid in a fresh session (`droid exec --auto medium -w redesign-ui-ux`), telling it to stop and report if the plan looked contradictory.
  - Droid read the artifacts and stopped after 6 turns, with no files changed. It reported two contradictions: task 2.2's ≥ 20° hue test fails on the D2 colors (accent vs error 17.3° light, 15.1° dark), and task 5.1 required exactly one primary button in every Generate state while D4 gives No new content none.
  - **Claude's verification:** both confirmed by computing the hues and reading `render.js generate()`. Both were Claude's planning errors: the 20° threshold had not been checked against the token values, and the spec said "exactly one" while the design table had a state with none. Claude also found a third issue Droid would hit next: `tokens.css` had to hold "exactly the D2 table", but the prototype also uses `--error-border` and non-color tokens, and the switch thumb has an `rgba()` shadow outside the allowed exceptions.
  - The user chose to shift the error color (option A over lowering the threshold) and approved the other two fixes: "Choose A; change 2 and 3 per your proposal; then resume Droid".
  - **Lesson:** every numeric check written into a plan is now computed against the planned values before the plan is handed off.
  - **Droid run 2 (same session) stopped again** before task 1.1: the manifest and `index.html` `theme-color` values must be literal colors, which the "no color literals outside `tokens.css`" rule forbade. Confirmed. Before resuming, Claude re-computed every numeric check in the plan (all contrast pairs in both themes, the hue gaps, the `#77736a` failure case), checked that every cited spec scenario exists, and that `vitest-axe` accepts vitest 4. It then scoped the rule to the app's stylesheets and components, listed the files that must mirror the tokens literally (offline page, manifest, meta tags, icon script and icons, tests), and stated the meta tag values.
- **Droid run 3 and the implementation review (2026-10-06/07).** Resumed in the same session with the clarified plan and the instruction to stop only for genuine blockers. Droid implemented all 14 tasks in 9 commits (about 49 minutes, 155 turns; about 2.39M credits cumulative for the session) and wrote a test report that explicitly listed what it had not verified (the visual parity matrix, a keyboard pass, browser install UI).
  - **Claude's review** in a separate worktree re-ran every check (352 backend tests at 96%, 56 frontend tests, the build, strict validation). It seeded a throwaway database with the prototype's sample data and compared the app with the prototype in the browser pane by measuring computed styles and positions instead of reading small screenshots. It drove live state changes by updating the run in the database while the page polled. Layout and copy matched closely; the first topic starts at 40% of a 900 px viewport and the narrow header is 94 px.
  - **Independent review subagent** (general-purpose, read-only): 17 findings. Claude verified all of them in code or in the browser and rejected none. The must-fix was that `lang` was set from the raw language setting, so "Same as original" produced `lang="original"`; Claude's own seed data used only Chinese and had missed it. The others included all-or-nothing loading on Generate and History, field errors attached to the wrong inputs, focus lost in the inline delete confirmation (also found by Claude), unported prototype rules, and lost Generate test coverage. Claude added two of its own: the offline page did not match the prototype, and the digest index lacked counts.
  - **Lesson:** the porting instruction "merge the five-file cascade" lost later overrides; the fix round asks for a mechanical class-coverage check against the prototype instead of trusting the port by eye.
  - The user chose to extend the list endpoint and keep the prototype's disabled primary button while running: "A: choose A1; B: as you recommend; after the changes, resume Droid". The user also pointed out that Claude's replies had drifted into English ("The output has turned into English again"); Claude saved this as a standing rule.
  - **Fix round (2026-10-07).** Droid implemented tasks 10.1–10.8 in 8 commits (about 15 minutes, 264 turns; about 4.32M credits cumulative for the session); 354 backend and 79 frontend tests pass. Claude re-checked in a fresh worktree and in the browser:
    - History issues one request.
    - A digest saved with "Same as original" has no `lang` attribute.
    - Focus moves to Cancel when the delete confirmation opens and returns to the row's Delete button on Cancel.
    - At 320 px all four nav links fit with no overflow.
    - The topic title (23.2 px) and the nav font now match the prototype.
    - The offline page, served by the worker with the server stopped, now has the C7 serif, centered style.
  - **Claude's own review error:** Claude had asked for visible per-section counts in the digest index. Droid noted that the C7 cascade hides `.toc-count` (`c3b.css:25`). Claude had compared `textContent`, which includes hidden elements, and misread the prototype. Claude restored the hidden rule (`d47fbf8`) and corrected task 10.7.
  - An offline check that first failed was a test artifact: Claude had deleted the worker's cache by hand earlier. A fresh origin (`127.0.0.1`) passed.
- **Adding `tdd` and `diagnosing-bugs` to the workflow (2026-10-07).** The user compared the project flow with a reference flow (`/opsx:propose` → `/opsx:apply` with `/tdd` per task → `/code-review` → `/opsx:archive`, and `/diagnosing-bugs` for bugs). They pasted an installation note, saying "I think we can add these two skills to our flow".
  - Claude read both skills from GitHub before installing. It found one conflict with unattended Droid runs: `tdd` requires confirming test seams with the user. Claude resolved it in the `AGENTS.md` rule: the seams named in each task's verification count as agreed.
  - The pasted note said the skills would land in `.factory/skills/`. The installer actually used `.agents/skills/` plus symlinks for Claude Code. Claude checked Factory's documentation, which lists `<repo>/.agents/skills/**/SKILL.md` as a Droid skill location.
  - Recorded as D-016.
- **Choosing the review tools (2026-10-07).** The user pasted a comparison of Matt Pocock's `/code-review` (two axes: standards and spec) with Anthropic's `/code-review` plugin and the hosted Code Review service, and asked whether to install Pocock's version. Claude read that skill's `SKILL.md` and advised against installing it, for these reasons:
  - Its name collides with the built-in skill.
  - The repository has no coding-standards file.
  - It needs a separate setup step.
  - The existing review sub-agent already checked against the spec; the actual gap was that the fix round had no code review at all.

  The comparison's concern that Anthropic's tool reads only `CLAUDE.md` did not apply, because `CLAUDE.md` is a symlink to `AGENTS.md`. The user agreed: "OK, review the fix round with these steps and write it into AGENTS.md". The step is now in `AGENTS.md` and recorded under D-016.
- **First use of the fixed review step: reviewing the fix round of `redesign-ui-ux` (2026-10-07).**
  - **The two reviews of `88b5b7d..f4f726e`:**
    - Claude Code's built-in `/code-review` at high effort reported 9 findings, all low severity. The top ones: a successful poll cleared the startup load error; the delete and the list refresh shared one catch; `lang` ignored language tags typed into "Other".
    - An independent spec sub-agent quoted the plan line for each of its 7 findings. It also confirmed group 10 by running probes: it put old behavior back into the code and saw the tests fail. The probes also showed one hollow test (the Creator-updates kind-label check passed even with the old code), a stale test report, and a timezone-dependent test.
  - **Claude's verification:** 12 findings confirmed, 2 judged no change, and 1 overlapping between the two reviews. The 2 with no change:
    - A failed model-settings read assumes a model is configured. Droid had documented this choice, and it is acceptable once the error stays visible.
    - The "No topics" fallback is unreachable, because the runner saves no digest without topics or Creator updates.
  - **Own error:** Claude's task 10.7 had told Droid to keep the long date on the hero "Last digest" line, but the prototype uses the short format there. It is corrected in 11.5.
  - **Decision and fix round:** the user approved, and agreed to show "Your sources" only when sources exist and to focus the "No sources yet" heading after the last delete: "OK; the heading as you suggest; after the changes, resume Droid".
    - Before the fix round, Claude merged `main` into the branch so that Droid's worktree has the new skills and rules. Both conflicts were text appended at the end of the process logs, and both sides were kept.
    - Task group 11 names the seam for each task. It assigns `diagnosing-bugs` to the four bugs and `tdd` to the rest.
  - **Droid fix round 2, first stop (2026-10-07).** Droid fixed 11.1–11.3 with the `diagnosing-bugs` loop. For each one it reported the failing check it saw before the fix, its ranked causes, and the confirmed cause; for example, "Startup alert disappeared after two successful poll ticks", caused by a shared error state that the poll cleared. It then stopped at 11.4. The reason: 10.2 maps "Japanese" case-insensitively to `ja`, while 11.4 named `japanese` as an example that must not map. This was Claude's error in choosing the negative example; the intent was that the language-tag path must not accept unknown 8-letter subtags. Claude replaced the example with `abcdefgh` and resumed Droid.
- **Fixed review step on group 11, and reviewer fixes (2026-10-07).**
  - **The review.** Group 11 was reviewed with both parts of the step.
    - `/code-review` reported 3 findings.
    - The independent spec sub-agent reported 7, after re-introducing each old behavior in a copy of the repository. Every group 11 test failed as it should.
    - Claude verified all of them. The real ones were a race in the digest list that returns a 500 (the sub-agent reproduced it), a names table that answered for `constructor`, an untested error path in `digestLang`, an untested focus branch, stale report sentences, a D5 note missing, and a POSIX-only `TZ=` prefix. Three were judged no change: a stale load alert until reload, hypotheses missing from commit messages, and an extra wording test.
  - **The fixes.** The user chose to have Claude fix them directly rather than run Droid again: "Fix it yourself, then review it following the process". The session's Droid credits stood at about 6.9M.
    - Claude worked test-first, recorded as task group 12. The race test failed with `KeyError` before the fix. For guards that already existed, Claude removed the guard temporarily to show the test fails without it.
    - One new focus test was flaky (1 of 3 runs failed). Claude made it wait for focus and confirmed it: 5 of 5 runs pass, and 3 of 3 runs fail with the mutation in place.
  - **The review of Claude's own fixes, with the same step.**
    - `/code-review` reported 3 low findings.
    - The spec sub-agent confirmed all five fixes by mutation and found only nits. The timezone pin did not hold under `--pool=threads`, and two test cases could never fail.
    - Claude fixed these as well. `src/test/setup.ts` now throws unless the zone is pinned. Lowercasing became locale-independent, shown by a test that emulates Turkish case rules and failed first. The cases that could never fail were removed.
- **Final review of the whole change (2026-10-07).** The user asked for another review before manual testing: "Review it again". Claude reviewed the whole change (`main...HEAD`) rather than only the last commit, with both parts of the fixed review step.
  - **Findings.** `/code-review` reported 7 findings. The independent spec sub-agent went requirement by requirement and re-introduced broken behavior to see whether tests fail; it reported 11. Claude verified all of them, and after removing duplicates, 15 remained, none rejected. The most notable:
    - "Digest ready: N items" left out Creator updates, because run `items_total` counts only summarized inputs.
    - Sources showed a made-up empty state when loading failed.
    - The cached offline page could never update, because the cache name is constant and `sw.js` does not change.
    - Every screen had the same document title.
    - A run failure was announced twice.
    - In the dark theme, `--subtle` on `--hover` is 4.39:1.
    - About a dozen behaviors could be broken without any test failing.
  - **Decisions.** Two findings were contradictions in Claude's plan, which the user decided: "A and B as you recommend; hand it to a new Droid session".
    - The spec asked for the full feed URL while the design said 2 lines; full URLs were chosen.
    - Generate had no state for a configured model with no sources; "Add sources" becomes the primary action.
  - **Hand-off.** Claude wrote task group 13 with context for a new implementer and the seam for each task. The fix round goes to a new Droid session: the previous session's cumulative usage was about 6.9M credits, so a fresh session avoids re-sending that long context on every turn.
- **Fixed review step on group 13, and reviewer fixes (2026-10-08).** The fresh Droid session (`b81cc6fa`) finished group 13 in 12 commits, using about 1.42M credits, compared with about 6.9M accumulated by the previous long session. Its report listed a failing check for every task.
  - **The review.**
    - `/code-review` reported 4 low findings.
    - The spec sub-agent re-introduced broken behavior for each task. It confirmed that the production code matched the amended spec and design, with no missing items and nothing extra. It found five test gaps, a service-worker structure in which a throwing `waitUntil` could replace a real response, and a hover rule that restyled disabled buttons.
    - Claude verified all of them. One `/code-review` finding (a cheap extra lookup per poll) was judged no change.
  - **The fixes.** The user again chose a direct fix: "Fix it yourself, then review it following the process". Claude wrote the tests first and saw 5 fail.
    - While fixing the service worker, the new test failed for a test-environment reason: Node's `Request` rejects relative URLs, while a worker resolves them against its own location. Claude fixed the fake context, not the production code.
    - Claude first wrote the mutation checks with `git checkout` to restore files, then noticed that this would wipe its own uncommitted fixes. It switched to a script that restores each file from an in-memory copy.
    - Every mutation failed its test.
  - **Review of these fixes with the same step.** `/code-review` reported 2 low findings. The spec sub-agent tested `sw.js` in a real Chromium service worker: the relative `Request` resolved correctly, the no-cache refresh revalidated even under `max-age=3600`, a 404 passed through, and the offline page appeared with the server stopped. It re-introduced about 20 broken behaviors, and each made a test fail. Its only findings were two nits: the refresh test did not pin the cache name, and a note was misdated. Claude fixed these together with the install request, which was not yet no-cache. The new install test failed first.
- **Automated end-to-end check before the manual test (2026-10-13).** The user asked: "Can we test automatically first? I can store the DeepSeek key somewhere".
  - Claude explained that it will not read or submit a real third-party API key, even from a file. Instead it proposed two layers:
    - a fully automated run with a local OpenAI-compatible stand-in model;
    - a later real-model run in which the user pastes the key into Settings once, and Claude drives the rest.
  - Claude wrote the stand-in, built the image, ran the smoke test, and drove the whole flow in the browser pane against real public feeds. The steps were first run, settings, three kinds of source, generate, digest, no new content, history and delete, narrow dark theme, Simplified Chinese with the saved snapshot kept, and offline and recovery. Every step passed (see the test report).
  - **What went wrong along the way:**
    - The review worktree under `/private/tmp` had lost its `.git` file to macOS temporary-file cleanup. All work was committed, so Claude pruned the worktree and recreated it.
    - The browser pane's accessibility listing showed the nav links without names, and service-worker registration failed when the pane opened the URL directly. Claude checked both rather than reporting them as bugs. The links' accessible names are covered by the jsdom tests. The worker registered normally when the pane attached through a launch configuration.
- **Real model run, visual check, and a manual-test fix (2026-10-13).**
  - **The real model run.** The user first reported "The key is filled in", but the container's settings still pointed at the stand-in. The logs showed a successful connection test and no save. Claude told the user what it saw instead of assuming success. After the user saved, Claude generated a real digest through the UI.
  - **The visual check.** The user asked: "Check it visually first". Claude reviewed screenshots of every screen and found two issues.
    - Settings' Save button was below the fold, which was the cause of the missed save.
    - Single-item topics leave a third of the row empty.
  - **The user's decision:** "Fix item 2 yourself; file item 1 as an issue". Claude wrote the failing tests first, made the save bar sticky, and checked it in screenshots. The first version let text in other columns show beside the bar, so Claude extended the background across the row.
- **Ready-count wording, a date-dependent test, and merge approval (2026-10-14).**
  - The user asked: "Why does the progress bar show 14 items for 3 sources?" Claude read the run's data and explained that 14 = 10 + 4 summarized items, while 2 YouTube videos went to Creator updates.
  - The user then said: "Change the completion text, and then the merge is approved." They also raised a new need: the main screen should show the latest digest instead of sending users to History. That need is handled as a separate change after this merge.
  - Claude changed the text test-first. While running the full suite, it found a pre-existing date-dependent test failure. Following `diagnosing-bugs`, it reproduced the failure on the committed code, confirmed the cause (fixture dates against the 7-day first-add window), and pinned the clock. A shifted-clock probe found no other such test.

## 2026-10-15 — Documenting the pre-commit hook setup (Claude Code, Opus 5.5)

- Prompt (faithful excerpt): "`.githooks/pre-commit` ... only runs when `git config core.hooksPath .githooks` is set ... Add a short setup step to README.md ... and a one-line note in AGENTS.md ... telling developers and agents to run `git config core.hooksPath .githooks` after cloning ... do not change the hook itself ... small change: lean path."
- Problem: the requested relative path conflicted with commit `72cb2b0`, which enables the hook with an absolute path so that worktrees on branches created before the hook still run it. Claude checked `redesign-ui-ux` (since merged in #26): its branch has no `.githooks/pre-commit`, so with a relative path a worktree on it would skip the hook silently. Because worktrees share the clone's `.git/config`, the command is needed once per clone, not once per worktree.
- Adjustment: Claude asked before editing. The user chose the absolute path `git config core.hooksPath "$PWD/.githooks"`, and a direct commit instead of an OpenSpec change, since a developer setup note has no product requirement to put in a spec delta.
- Outcome: setup step added to the README development setup section and a one-line note to the `AGENTS.md` Commands section. The hook is unchanged.

## 2026-10-14 to 2026-10-15 — Technical spec (Claude Code, Opus 5.5, with an independent review subagent)

- Prompts (verbatim, with translations):
  - "I will merge after CI passes; first open the issue, then write the technical spec".
  - The user shared the course's project description, the spec template, and an editable copy: "Here are CS146S Final Project Description and CS146S Aut26 Technical Spec template and a copy of Technical Spec template, which you can edit directly".
  - "Are these success metrics required by the template?", then "OK, write it into the doc with this table".
  - After the doc check: "Change it as suggested, and pin the table header too".
  - After merging #26: "Have the review agent look over the PDF; are there any problems?", then "Do items 1–5 as you proposed, remove the code formatting for item 6, and do the cleanup too", and "Tighten the row heights too, then do a final check".
- Outcome: a two-page spec in the template's order (Architecture, API Design, Technical Stack, Business Context Summary, Agent Readiness), submitted on Gradescope on 2026-10-15. `docs/technical-spec.md` matches the submitted document word for word; the figure is `assets/catchup-architecture.png`, rendered from `assets/catchup-architecture.html`; the submitted PDF is in the project root.
- Process:
  - Claude drafted the text in Markdown and checked each claim against the code. The success-metric targets were Claude's proposal; the user confirmed them unchanged.
  - An independent subagent that had not seen the drafting reviewed three times: once before the template rewrite, once on the template version, and once on the exported PDF. Claude verified each finding against the code or the PDF before changing anything.
  - Round 2 had 13 findings: 10 fixed, 2 partly adopted, 1 rejected, and 1 left to the user (the user kept the "A week of 10+ sources" wording). The most serious one was a wrong claim: the model client makes up to 3 attempts, not 3 retries (`llm/client.py`, `range(3)`).
  - Round 3 found no blockers. Its main finding was that the figure's labels were too small to read in print at 75% width, so the figure and both tables were widened to the full text width.
- Problems and adjustments:
  - The built-in browser was not signed in, and Claude did not sign in for the user; it edited the doc as an anonymous editor. Text went in through a pasted HTML fragment with inline styles that match the template. The first pastes needed fixes: zero list margins, no heading indent, black code text, and left-aligned table cells.
  - A cross-origin hand-off of the figure from a local page into the Docs tab was blocked by the permission classifier, and Claude did not work around it. Anonymous editors cannot upload images ("You must sign in to upload images"), so the user inserted the figure and Claude resized it.
  - Fitting two pages in Docs' own layout took several rounds, because Chrome's preview underestimated the length. Claude reserved the figure's height with a same-height placeholder and used a 9.5 pt body, 1.52/1.9 cm margins, and wording trims. One fact, "one run at a time", now appears only in the figure and the API table.
  - Three times, text meant for a dialog or input box went into the document because the box did not have focus: "[F]" at the end, "9.5" before the figure, and a phrase in front of a heading. Each was caught, either from the screen or by comparing the exported text's length, and undone or replaced. Afterwards Claude checked which element had focus, the dialog's field values, and the document length before every edit.
  - A direct edit in the doc had brought back "retried up to 3 times". Claude flagged it with the code reference instead of reverting it, and the user approved the fix.
  - Claude's replies drifted into English after long English tool output and subagent reports. The user pointed it out twice ("Why are the replies in English again?" and "You used English again.").
  - The user saw a "red" table column. It was Claude's own selection, shown as a collaborator highlight; the exported HTML confirmed that the cells have no background colour.

## 2026-10-16 — `show-latest-digest-on-home` (#27): research, proposals, and plan (Claude Code, Opus 5.5, with two Explore subagents)

- Prompts (translated from Chinese):
  - "It's merged; start the research for #27."
  - After the two proposals: "Where did Generate go in Proposal 1?"
  - "Choose Proposal 1, use Latest for the navigation, and do #25 separately."
- Research:
  - Claude read the Generate, DigestView, History, App, and AppShell code and the three related specs itself.
  - Two read-only Explore subagents covered the backend digest and run endpoints, and the layout CSS and frontend tests.
  - Claude spot-checked their key claims against the code before writing `research.md`: list ordering, `/active` returning `null`, the SPA fallback, the grid rules, the status region, and the test names and lines.
  - The research found that the main screen never loads digest content, that the reading layout is an unexported component with its own `h1`, that the two screens use different grid splits, and that there is no latest-digest endpoint.
- Proposals: (1) `/` becomes the latest digest under a compact run bar; (2) Generate stays, with the digest embedded below. The user's question showed that Proposal 1 had not said where Generate goes. Claude answered with a text mock-up of the run bar in each state, and noted that generating from other screens still means going back to `/`.
- Plan:
  - `proposal.md`, the spec deltas (`user-interface`: one requirement added and four modified; `digest-history`: one added), the final `design.md` (D1–D8), and a `tasks.md` in five groups, with failing-first tests named in each task.
  - The two lessons from the redesign became verification items: the test count must not drop when `Generate.test.tsx` moves, and the status region must not remount.
  - `openspec validate --strict` passes. D-017 and a requirements-changes row record the decision.
- Problems / adjustment: the first proposal summary described the run bar only in prose, which left the user unsure where Generate went. Claude now includes a layout sketch whenever a proposal moves or removes a control.

## 2026-10-15 to 2026-10-16 — Latest digest on Home (Factory Droid, GPT-6 Sol)

- Prompt (faithful excerpt): "Implement OpenSpec change show-latest-digest-on-home using the openspec-apply-change skill. Work through ... tasks.md in order, completing each task test-first with the tdd skill: write the task's verification items as failing tests and watch them fail, then implement until they pass. ... Commit after each task group. Do not push, tag, or open a PR."
- Outcome: Added the one-request latest digest endpoint, shared digest reading article, Home layout and in-place digest replacement, Latest navigation and documentation. Four implementation group commits and a final checks/report commit. Full results and omitted live checks are in `test-report-show-latest-digest-on-home.md`.
- Problems / adjustment: The new API tests initially returned 422 as expected; frontend dependencies were missing and installed from the lockfile. During the page rename, obsolete last-digest link/date tests were replaced with no-link and in-place article checks, while the existing run-state tests were retained. The style audit alone did not inspect the new run-bar selectors, so a failing CSS rule test was added before styling. No external provider or feed was contacted in tests, and no code was pushed.
- Review fixes (2026-10-16): Claude Code asked Droid to implement review tasks 6.1–6.9 in order, reproduce bugs first, use `tdd` for tests and styling, commit each task, and leave planning artifacts untouched. After Droid stopped because a purely structural refactor could not have a failing behavior test, Claude Code amended 6.7 (commit c5c9fbd) to use the existing Home tests as its safety net and asked Droid to continue. Regression tests reproduced stale alerts, duplicate first-digest actions, mismatched error text, and an overlapping-fetch race before fixes. Stronger success tests required the article to load; a Home/History comparison checked identical reading markup. The shared run-state refactor kept 49 Home tests green. A CSS test failed before the redundant and double rules were removed. The backend timestamp-order test passed immediately because the API already sorted correctly. Removing `.hero-last` made the style audit fail against an archived prototype; Droid documented the prototype-only exception rather than restoring dead app CSS. Final checks: 362 backend tests (96% coverage), 152 frontend tests, build, style audit, strict OpenSpec validation, and local Docker build passed. Live browser and real-run checks remain for review; no push, tag, or PR was made.
- Review fixes, round 2 (2026-10-16): Claude Code's review found the first-run regression and stale alert races; Droid reproduced and fixed them, strengthened mutation-sensitive tests, separated startup errors, and passed 362 backend tests, 159 frontend tests (58 axe scans), build, style audit, strict validation, and local Docker build.
- Review fixes, round 3 (2026-10-16): Claude Code asked Droid to fix the higher-id error race and empty queued-source labels, then refactor and recheck; failing-first tests reproduced both bugs, and 362 backend tests, 162 frontend tests (58 axe scans), build, style audit, strict validation, and Docker build passed.

## 2026-10-16 — `show-latest-digest-on-home` (#27): review of the Droid run and three fix rounds (Claude Code, Opus 5.5, with one spec-review subagent; Factory Droid session `21b6d3aa`)

- Process: the fixed review step (D-016) ran after every Droid run.
  - `/code-review` on the run's diff.
  - An independent spec subagent that had not seen the design discussion. The same agent was resumed each round, so it could check earlier findings.
  - Claude verified every finding with a probe test, a mutation, or the code before anything changed.
  - Live checks ran on a local review instance with a stub model and public feeds.
- Round 1 (groups 1–5):
  - 9 findings were confirmed and none rejected. Examples: a stale startup error re-announced after the swap, a leftover "View digest" in the first-digest card, three success tests that passed in the fetch-error state, an in-flight swap dropped by a new run, and a spec scenario that ignored the back link.
  - Live checks passed: the in-place swap kept focus, made no `focus()` calls and no scroll, and announced once; the 1440/900/420 px layouts were fine.
  - Claude asked four questions. The user replied "As you recommend" (translated). Claude amended design D3/D5/D7 and the "Same digest in both places" scenario, and added task group 6.
- Prompt to Droid (faithful excerpt): "Implement 6.1-6.9 in order with the openspec-apply-change skill: diagnosing-bugs for 6.1-6.4 and tdd for 6.5-6.8, always writing the failing test first. Check off each task only after its verification passes. … If a task is blocked or the plan looks wrong, stop and report instead of improvising."
- Problem: Droid stopped at 6.7, a pure refactor that the plan had put under `tdd`'s red-first rule. Droid was right, and the plan was Claude's error.
  - Adjustment: Claude marked 6.7 as `tdd`'s refactor step, with the existing tests as its safety net (commit c5c9fbd), and resumed Droid.
  - Later plans label refactor tasks explicitly (7.6, 8.3).
- Round 2 (group 6):
  - The 6.7 refactor had changed first-run behavior while all 49 Home tests passed; a probe test showed it.
  - The spec subagent's mutations showed that one 6.4 test could not detect the regression it named.
  - Also found: a stale-alert race, the no-digest success card left without coverage, and a lost second startup error.
  - Droid's log entry attributed Claude's prompts to the user. Claude corrected it.
  - The user replied "As you recommend" (translated) → group 7.
- Round 3 (group 7): mutations confirmed each fix, and four low items remained. The user chose "As you recommend, one more small round" (translated) → group 8.
- Round 4 (group 8):
  - Mutations and failing-first runs confirmed both fixes. A probe of zero-check runs in both layouts found no regression.
  - One optional item remains: a mutable Set held in `useState`. Both reviewers rated it low, and it was left as is.
  - Live checks passed: no empty "Sources" label while checking, and a real run swapped No. 2 for No. 3 in place.
- Lessons:
  - Before a refactor, check that its safety net still covers the code being moved. Here, 6.5 had weakened it.
  - A verification claim counts only if the test fails under a mutation of the fix. The spec subagent now mutation-tests the claims.

## 2026-10-16 — `improve-single-item-topics` (#25): research, proposals, and plan (Claude Code, Opus 5.5, with two Explore subagents)

- Prompts (translated from Chinese):
  - "Delete the remote branch, then start the research for #25."
  - "Start the proposals."
  - "Choose Proposal 1, do G separately, start the plan."
- Research:
  - Claude read the reading-layout CSS, `DigestArticle`, the width-class tests, and the specs itself.
  - Two read-only Explore subagents covered the grouping pipeline, and the redesign's design records, prototypes, and test report. Claude spot-checked their key citations against the files.
  - Claude also measured the two real Chinese digests in the user's local e2e instance at 1440 px, read-only through the built-in browser.
  - The measurement changed the problem statement. The empty right third is not limited to single-item topics: every long item that is not followed by a short item leaves it, and nearly every real summary is over the 140-character cut-off. As a result, 14 of 16 rows in one digest ended 302 px short of the edge.
- Proposals:
  - (1) the item title beside its summary, one row per item
  - (2) long items across the full width, with two text columns
  - Option G: a grouping prompt for fewer, broader topics
  - Each came with a layout sketch, since both move content. While checking the numbers, Claude corrected the narrow-window widths (190 px just above 900 px).
- Plan:
  - `proposal.md`, a `user-interface` delta (the "Digest reading layout" requirement modified, and "Single-item topic" and "Narrow window" scenarios added), the final `design.md` (D1–D6), and a `tasks.md` in three groups with failing-first tests.
  - The user's choices were recorded as D-018. Option G became issue #32.
- Problem / adjustment: the first draft of the spec capped summary lines at "about 50 characters of mixed text". Pure English lines at that width hold about 75 characters, so the rule would have failed on English digests. Claude split the rule: at most 40 Chinese or 80 Latin characters per line at 1440 px.

## 2026-10-16 — `improve-single-item-topics` implementation (Factory Droid, GPT-6 Sol; session `92a71026`)

- Prompt (faithful excerpt): "Implement OpenSpec change improve-single-item-topics using the openspec-apply-change skill. Work through ... tasks.md in order, completing each task test-first with the tdd skill: write the task's verification items as failing tests and watch them fail, then implement until they pass. Check off each task only after its verification passes. ... Commit after each task group. Do not push, tag, or open a PR."
- Outcome: Removed length-based item classes, made every item a full-width subgrid row with its heading beside its summary on wide windows, and documented two archived prototype-only selectors. The first version **did not preserve one-column stacking below 900 px**: its wide child placements overrode the narrow reset, causing overlap at 420 and 900 px; review task 4.1 fixes this. The DOM/CSS tests and style audit failed before their corresponding initial fixes. Three task-group commits; **362 backend tests** at **96% coverage**, **164 frontend tests** with **58 axe scans**, build, style audit, strict OpenSpec validation, and local Docker build passed, but did not catch the overlap. See `test-report-improve-single-item-topics.md` for commands and omitted manual measurements.
- Problems / adjustment: Installed locked dependencies in this new worktree. The prototype audit rejected the removed classes until they were explicitly allow-listed with reasons. A console-based axe counting probe printed no markers under Vitest output capture, so a temporary test-helper probe counted scans in a temp directory; the helper was restored before committing. Tests used no external feed or provider; the Docker build resolved base-image metadata but did not push an image.
- Review fixes, round 1: Claude Code's review found the narrow overlap in a browser (420 and 900 px). Droid then wrote a block-aware CSS test that failed against the old rules, moved the side-by-side rules above 1100 px, retained removed-rule guards, simplified the item map, and reran 362 backend tests (96% coverage), 164 frontend tests (58 axe scans), build, audit, validation, and Docker build; an intermediate Docker build failed only while the temporary scan-counting probe remained in its context.

## 2026-10-16 — `improve-single-item-topics` (#25): review and one fix round (Claude Code, Opus 5.5, with one spec-review subagent; Factory Droid session `92a71026`)

- **Process.** The fixed review step (D-016) ran after each Droid run:
  - `/code-review` on the run's diff.
  - An independent spec subagent. It rendered the real markup with the app CSS in headless Chrome and mutation-tested the CSS assertions.
  - Live checks on a read-only review build. A small proxy served the branch build and forwarded only GET requests to the user's local e2e instance, so the real Chinese digests No. 3 and No. 4 could be measured without changing them. The English stub digests came from a local data copy.
- **Round 1 (groups 1–3).**
  - The wide layout worked: every summary ended at x = 1312 at 1440 px, 580 px wide, with at most 35 CJK and 75 Latin characters per line.
  - At 420 and 900 px, however, every item's title was painted over its summary. Both reviewers found this independently.
    - Cause: the narrow reset `.items > .item > *` had lower specificity than the wide placements, and container queries add none.
    - The CSS test had only checked that the reset's text existed, so it passed.
  - The live check also showed that titles wrapped to 4–5 lines in the 191 px heading column just above 900 px.
  - The user decided: "Move the breakpoint to 1100 px; fix it together with the spec results" (translated).
  - Claude amended D1 and D4: all side-by-side rules moved into one `@container (width > 1100px)` block, so no reset is needed. Claude also amended the spec delta (a "Medium window" scenario), D-018, and the requirements row, and added task group 4.
- **Prompt to Droid** (faithful excerpt): "Read those passages and group 4's notes first. Then implement 4.1-4.4 in order: diagnosing-bugs for 4.1, tdd for 4.2, and 4.3 as a refactor step with no red test. … If something is blocked or the plan looks wrong, stop and report."
- **Round 2 (group 4).**
  - Live checks at 1440, 1101, 1100, 1000, 900, and 420 px passed: no overlap, and every summary ends at the content edge.
  - Mutations confirmed that the new block-aware CSS test catches the cascade conflict.
  - Remaining issues:
    - Claude fixed three wording errors in the plan: the 900 px boundary in the spec, a broken list in the proposal, and a usage-log line that credited the test, not the review, with finding the overlap.
    - Two low test gaps (no guard against a heading/summary rule, and a guard that reads only `layout.css`) went to issue #33. The user replied "Approve the merge; record the two test gaps as an issue" (translated).
- **Lessons:**
  - A CSS assertion that matches rule text cannot show that a rule wins the cascade. Responsive layouts need a rendered check, or a structure that avoids competing rules.
  - Service workers on review builds cache old CSS. Claude unregistered them before each live check.

## 2026-10-16 — `fix-new-source-check-outcome` (#31): research and lean plan (Claude Code, Opus 5.5, with one Explore subagent)

- Prompts (translated from Chinese):
  - "Start the research for #31."
  - After the research: "Use opsx."
- **Research.**
  - Claude read the confirm, collection, and runner code itself.
  - A read-only Explore subagent covered the UI labels, the API shapes, the specs, the tests, and the docs. Claude spot-checked its key citations.
  - The research found three things:
    - the run's check counts only entries it sees for the first time, while the run digests every pending item
    - the run JSON carries only the status
    - an existing end-to-end test, `test_core_flow.py:77-84`, asserts the contradictory pair: 2 items, and "no new items"
- **Lean plan.** The user chose the `/opsx:propose` path (the `openspec-propose` skill). Before writing, Claude asked two questions, because the answer changes what users see. The user chose:
  - "New items" means the run includes something from that source.
  - The labels stay as they are, with no count.
- **Artifacts.**
  - `proposal.md`.
  - A `content-collection` delta: the redefined outcomes, and four new scenarios.
  - A short `design.md`: the outcome is finalized in the runner after item selection.
  - A two-group `tasks.md` with failing-first runner tests.
  - D-019 and a requirements row record the decision.
- **Problem / adjustment.** The `/opsx:propose` command maps to the `openspec-propose` skill; the first attempt to invoke it under the command's name failed.

## 2026-10-16 — `fix-new-source-check-outcome` implementation (Factory Droid, GPT-6 Sol; session `ec0f2c13`)

- Prompt (faithful excerpt): "Implement OpenSpec change fix-new-source-check-outcome using the openspec-apply-change skill. Work through ... tasks.md in order, completing each task test-first with the tdd skill: write the task's verification items as failing tests and watch them fail, then implement until they pass. Check off each task only after its verification passes. Do not edit proposal.md, design.md, or the spec deltas. Commit after each task group. Do not push, tag, or open a PR."
- Outcome: Reproduced nine outcome mismatches with failing tests, then finalized each successful source's status and item count after selection and before summarizing; failed checks stay failed. First-run, carry-over, waiting, skipped Short, Creator-update, empty-run, multi-source, and timing cases are covered. Group 1 committed separately. Full backend coverage, frontend tests/build, strict validation, and a local Docker build passed; actual numbers and the unperformed manual check are in `test-report-fix-new-source-check-outcome.md`.
- Problems / adjustment: The first red run revealed a test indexing typo; corrected it before implementation. Parallel summary calls initially made the before-summary observation test record twice; guarded the observation with a lock. Installed locked dependencies in the new worktree (`uv run` and `npm ci`). Tests did not use a live feed or provider; no remote publication was performed.
- Review fixes, round 1: Reproduced both deleted-source races before replacing ORM row mutations with missing-row-tolerant updates; strengthened the held-episode test and proved it fails without finalization.

## 2026-10-16 — `fix-new-source-check-outcome` (#31): review and one fix round (Claude Code, Opus 5.5, with one spec-review subagent; Factory Droid session `ec0f2c13`)

- **Process.** The fixed review step (D-016) ran after each Droid run:
  - `/code-review` on the run's diff.
  - An independent spec subagent, which mutation-tested the runner change in a scratch copy and probed a source deletion with an SQLAlchemy hook.
  - Live checks on a fresh local instance from the branch: a stub model and public feeds added through the API.
- **Round 1 (groups 1–2).**
  - Live checks passed:
    - A newly added Python Insider reported "New items" on its first run, with its item in that digest, and "No new items" on the next.
    - Adding Rust Blog showed "Rust Blog · New items" in the run bar next to its item.
  - Spec subagent findings:
    - Deleting a source between item selection and the outcome update failed the whole run, with `AttributeError` or `StaleDataError`.
    - The held-podcast test passed even without the fix.
    - Droid's log entry named the Claude Code session id instead of its own.
    - A coverage count was off by one.
  - Claude's own finding (a source added mid-run gets items but no outcome) was judged consistent with the new meaning and needed no change.
  - The user replied "As you recommend, one more small round" (translated). Claude added a D1 bullet on deleted sources and task group 3.
- **Prompt to Droid** (faithful excerpt): "Read those first. Then implement 3.1-3.3 in order: diagnosing-bugs for 3.1, tdd for 3.2. Write the failing test first where a task asks for one. … If something is blocked or the plan looks wrong, stop and report."
- **Round 2 (group 3).**
  - The fix uses bulk `UPDATE` by id, so a deleted row is skipped.
  - The subagent's deletion probe passes, and the two new tests failed against the previous runner.
  - Two defensive guards survive mutation, but they are equivalent mutants.
  - On the restarted instance:
    - adding Ruby News gave "New items" with its item in the digest
    - deleting a source during a run no longer failed the run
  - The user approved the merge: "Approve auto-merge, and delete the remote branch after merging" (translated).
- **Lesson.** A stub that already produces the expected outcome makes a regression test vacuous. The test should set up the opposite of what the fix produces, as task 3.2 did.

## 2026-10-16 — `guard-digest-item-layout-css` (#33): lean plan (Claude Code, Opus 5.5)

- Prompt (translated from Chinese): "Move #16 to Done and close it, then start #33."
- **Housekeeping.** Claude closed #16 (the technical spec, submitted on 2026-10-15) with a note pointing to the final text and the PDF, and moved it to Done.
- **Path.** #33 only adds tests, so Claude used the lean path (`/opsx:propose`, the `openspec-propose` skill) with `skip_specs: true` and no design document.
- **Before writing,** Claude checked every owned style file for item-child rules and vertical borders, so that the guards would pass on today's CSS.
- **Plan.**
  - The placement guard and a new vertical-rule guard now read `base.css`, `layout.css`, and `components.css`, the style-audit `OWNED` list.
  - Each guard's red step is a named, temporary CSS mutation. These include the two mutations that the #25 spec subagent found passing every test.

## 2026-10-16 — `guard-digest-item-layout-css` implementation (Factory Droid, GPT-6 Sol; session `2ca2b998`)

- Prompt (faithful excerpt): "Implement OpenSpec change guard-digest-item-layout-css using the openspec-apply-change skill. Work through ... tasks.md in order with the tdd skill. These guards must pass on today's CSS, so each red step is the named temporary CSS mutation in the task: apply it, watch the test fail, revert it, watch it pass, and never commit a mutation. Name each mutation and its result in the commit message. Check off each task only after its verification passes. Do not edit proposal.md. Commit after the task group. Do not push, tag, or open a PR."
- Outcome: Extended the placement guard to all three owned CSS files with file-and-selector diagnostics and added a vertical-border guard. All six named CSS mutations failed their guard and passed again after reversal. Full frontend checks passed: 165 tests in 13 files, TypeScript/Vite build (41 modules), and style coverage (0 uncovered prototype selectors). The red/green table and check results are in `test-report-guard-digest-item-layout-css.md`.
- Problems / adjustment: The fresh worktree lacked frontend dependencies, so installed them from the lockfile with `npm ci` (0 reported vulnerabilities). Kept all mutations temporary; no CSS or runtime files changed in the final diff. No browser geometry check was performed.
- Review fixes, round 1: After review exposed selector and shorthand gaps, broadened both guards, rechecked all six original and six new red/green mutations plus three green-only edits, and reran the full frontend and style checks.

## 2026-10-16 — `guard-digest-item-layout-css` (#33): review and one fix round (Claude Code, Opus 5.5, with one spec-review subagent; Factory Droid session `2ca2b998`)

- **Process.** After each Droid run, Claude ran `/code-review` and an independent spec subagent. The subagent verified every named mutation in a scratch copy and tried its own. No browser check was needed, because the change only adds tests.
- **Round 1 (group 1).**
  - The guards matched the plan's exact list and caught all six named mutations.
  - Both reviewers found that they matched exact selector strings, a few property names, and only classes at the start of a selector. As a result, `p.summary`, `grid-area`, `border-left-style`, `.items>.item`, and `.topic .item` slipped through, and `.item:hover .badge` caused a false positive.
  - Droid's log entry again named the Claude Code session id instead of its own (as in #31).
  - The user replied "As you recommend, one more small round" (translated). Claude amended the proposal: match the rightmost compound of each selector, including `:is()` and `:where()`, and whole property families. Claude also added task group 2.
- **Prompt to Droid** (faithful excerpt): "Each red step is a named temporary CSS mutation: apply it, watch the test fail, revert it, watch it pass. Also check the listed false-positive edits stay green, and never commit a mutation. Record every mutation and its result in the commit message."
- **Round 2 (group 2).**
  - All 12 violation mutations failed, and the 3 false-positive edits stayed green. The subagent reproduced the 15-row table.
  - The remaining low cases (logical border properties, nested pseudo-classes, and a few universal or attribute selectors) were recorded as known limits in the test report.
  - The user replied "As you recommend; approve auto-merge, and delete the remote branch after merging" (translated).
- **Lesson.** Droid reads Claude Code's session id from its environment when it writes its log entry. Future prompts should give Droid its own session id, or Claude should correct the entry at review.

## 2026-10-17 to 2026-10-18 — User testing feedback, issues, and the `add-browser-tab-icon` (#37) lean plan (Claude Code, Opus 5.5)

- **Context.** Claude rebuilt the local e2e container from `main` (e2e8aa4) so the user could try the merged changes. The data volume and the instance secret were reused, and the secret was never printed or written.
- **Feedback** (prompts translated from Chinese, with screenshots):
  - "The part in the red box doesn't feel necessary; record it for now" (the run bar's per-source list)
  - "We need an icon, record it too" (the tab showed a globe)
  - "Is Bilibili supported now?"
  - "This site isn't supported either, I don't know why" (`spaces.ac.cn`)
  - "Twitter accounts don't work"
  - "Oh, that's the second version's extension work, right?"
- **Investigation.** Claude answered each from the code or by reproduction:
  - The tab icon: `index.html` declares no `<link rel="icon">`, and `/favicon.ico` falls back to HTML.
  - `spaces.ac.cn`: the home page answers HTTP 403, while `/feed` works; discovery never probes `/feed` after a failed page fetch.
  - X: deliberately unsupported since 2026-10-02, and tied to the future browser extension.
  - Bilibili: no support, and RSSHub is the only workaround.
  - The items were kept in a local list until the user finished testing.
- **Decisions** (the user's choices to three questions):
  - The run bar lists only sources that need attention.
  - The tab reuses the existing icon.
  - The fixes are three lean changes done in turn.
- **Issues opened:** #37 (tab icon), #38 (run bar), #39 (page refused, together with #23), #40 (Bilibili), #41 (X).
- **#37 lean plan.**
  - The `openspec-propose` skill was not loaded in this session, so Claude followed the project's `.claude/skills/openspec-propose/SKILL.md` by hand.
  - It wrote a `local-deployment` delta (a browser-tab icon in "Installable as an app"), a proposal, and three test-first tasks.
  - Task 1.3 tells Droid to log its own `session_id`, not `CLAUDE_CODE_*`. This answers the wrong session id found in #31 and #33.

## 2026-10-18 — `add-browser-tab-icon` implementation (Factory Droid, GPT-6 Sol; session `09928c2f`)

- Prompt (faithful excerpt): "Implement OpenSpec change add-browser-tab-icon using the openspec-apply-change skill. Work through ... tasks.md in order, completing each task test-first with the tdd skill: write the task's verification items as failing tests and watch them fail, then implement until they pass. Check off each task only after its verification passes. Do not edit proposal.md or the spec deltas. Commit after the task group. Do not push, tag, or open a PR."
- Outcome: Added a failing HTML/asset test, then declared the existing SVG and 192 × 192 PNG as browser-tab icons. The focused test first failed with 1 failure and 3 passes; afterward the full frontend suite passed (166 tests in 13 files), as did the TypeScript/Vite build (41 modules), built-HTML link assertions, and strict OpenSpec validation. See `test-report-add-browser-tab-icon.md` for commands and the unperformed browser check.
- Problems / adjustment: This fresh worktree lacked frontend dependencies; `npm ci` installed the locked packages. A supplemental exact-string built-HTML assertion expected `>` instead of Vite's preserved `/>`; the attribute-aware assertion passed on rerun. No app-in-browser visual check was performed. No icon artwork, manifest, service worker, or backend fallback was changed.

## 2026-10-18 — `add-browser-tab-icon` (#37): review (Claude Code, Opus 5.5, with one spec-review subagent; Factory Droid session `09928c2f`)

- **Process.**
  - `/code-review` of the diff.
  - An independent spec subagent, which ran 16 mutations of the new test in a scratch copy: 14 failed, and the 2 harmless edits passed.
  - A live check of the branch build, served read-only against the local instance: both `<link rel="icon">` tags are present, and `/icon.svg` and `/icon-192.png` come back as `image/svg+xml` and `image/png`.
- **Findings.**
  - Nothing blocks the merge.
  - Two low items are left for a follow-up issue on icon polish: the offline page (`public/offline.html`) has no icon, and the service worker does not cache the icon files; and the icon's bars are about 0.6 px wide at 16 px.
  - Droid left out its session id, as the plan allowed when unknown. Claude added `09928c2f` from the `droid exec` output: Droid cannot read the id it is about to report, so Claude fills it in at review from now on.
- The user replied "As you recommend; approve auto-merge, and delete the remote branch after merging" (translated).

## 2026-10-18 — `improve-feed-discovery-errors` (#39, #23): lean plan (Claude Code, Opus 5.5)

- Prompts (translated from Chinese): "What are #39 and #23?", then "Start, write the lean plan first."
- **Investigation.** Claude traced both issues to `discover`:
  - A failed page fetch propagates before any probing (#39).
  - The declared-feed loop turns HTTP failures into `not_a_feed` (#23).
  - It also traced why no status reaches the user: `_fetch_error` passes only `retry_after`, and the Sources page maps each code to one fixed message.
- **Plan** (the `openspec-propose` skill, now loaded):
  - A `source-management` delta that modifies "Preview a source from a pasted URL" and "Explain unsupported and duplicate sources", with three new scenarios.
  - A short design. D1: probing after an HTTP page failure. D2: a new `feed_unavailable` code, and the precedence rules for mixed failures. D3: `http_status` in the error payload. D4: a table of messages.
  - Four test-first task groups.
- **Adjustment.** The Droid task now says to leave the session id out of its log entry; Claude adds it at review, because Droid cannot read the id it is about to report (seen in #37).

## 2026-10-18 — `improve-feed-discovery-errors` implementation (Factory Droid, GPT-6 Sol)

- Prompt (faithful excerpt): "Implement OpenSpec change improve-feed-discovery-errors using the openspec-apply-change skill. Work through openspec/changes/improve-feed-discovery-errors/tasks.md in order, completing each task test-first with the tdd skill: write the task's verification items as failing tests and watch them fail, then implement until they pass. Check off each task only after its verification passes. Do not edit proposal.md, design.md, or the spec deltas. Commit after each task group. Do not push, tag, or open a PR. If a task is blocked or the plan looks wrong, stop and report instead of improvising."
- Outcome: On HTTP page errors, discovery probes the existing bounded same-origin feed locations and retains the page error if none succeeds. Declared HTTP-failed feeds and confirm-time HTTP feed failures report `feed_unavailable`. The API includes `http_status`, and the Sources page explains actual statuses. Three implementation group commits; final checks passed: **384 backend tests** at **96%** statement coverage, **173 frontend tests**, frontend build, strict OpenSpec validation, and local Docker build. See `test-report-improve-feed-discovery-errors.md`.
- Problems / adjustment: Installed locked backend dependencies on the first `uv run` and frontend dependencies with `npm ci` after Vitest was missing. The first discovery rerun caught a mistaken assertion of eight root-path probes; the existing probe list deduplicates that path to seven, so the expectation was corrected and the suite passed. No live `spaces.ac.cn` check was performed; no key, external feed, or hosted service was used in tests. No push, tag, or PR.

## 2026-10-18 — `improve-feed-discovery-errors` fix round 1 (Factory Droid, GPT-6 Sol)

- Prompt (faithful excerpt): "Fix round 1 for OpenSpec change improve-feed-discovery-errors, in this worktree on branch improve-feed-discovery-errors. Review of your first run found confirmed bugs and test gaps. The plan was amended in commit 873720c: design.md D1-D4 and Risks, two new scenarios in specs/source-management/spec.md, and task group 5 in tasks.md. Use the openspec-apply-change skill and work through tasks 5.1-5.7 in order. Use the diagnosing-bugs skill for 5.1-5.2 and tdd for the rest: write each check first and watch it fail. Check off each task only after its verification passes. Do not edit proposal.md, design.md, or the spec deltas. Commit after each pair of test and fix tasks (5.1-5.2, 5.3-5.4, 5.5-5.6) and after 5.7. Do not push. If a task is blocked or the plan looks wrong, stop and report instead of improvising."
- Outcome: Reproduced declared-feed timeout misclassification and Apple feed probing, then corrected declared-candidate error precedence and isolated Apple lookup feed failures. Limited API `http_status` and Sources-page status messages to HTTP errors (400+). Four commits including this report; **402 backend tests** at **96%** statement coverage (1,850/1,923), **182 frontend tests**, frontend build, strict OpenSpec validation, and local Docker build passed. See `test-report-improve-feed-discovery-errors.md`.
- Problems / adjustment: A first Apple regression test failed on an unmocked probe rather than the expected behavior; supplied a mocked fallback and disabled the all-called assertion for the feed route that must not be requested. Discovery red run: 9 failures; API: 2; frontend: 3. Cases that were already correct are recorded separately in the test report. Corrected the first-run report's coverage arithmetic. The live `spaces.ac.cn` preview was not tested, and nothing was pushed.
