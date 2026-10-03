# AI Tool Usage Log

Real usage records for the technical spec, alpha reflection, and final report. Each entry: date, tool/model, purpose, prompt (verbatim or faithful excerpt), outcome, problems, adjustment.

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
- Cost reported by Droid for the fix run: 41 turns, ~2 minutes, 371,518 Factory credits. It is unclear whether `droid exec -s` reports per-call or cumulative session credits.

## 2026-10-03 — Model settings implementation (Factory Droid, GPT-6 Sol)

- Purpose: Implement tasks 2.1–2.4 and the carried-over test sandbox fix.
- Prompt (user, excerpt): "Implement ONLY task groups 2 and 3 (tasks 2.1-2.4 and 3.1-3.4) ... Replace it with an autouse fixture ... tests make no real network calls ... never read a real API key, and never write outside pytest temp dirs. Check off each task only after its verification passes. Commit after group 2 and again after group 3."
- Outcome: The autouse fixture redirects app data to per-test temp dirs, removes the instance secret, and rejects unmocked DNS/connect calls. Added Fernet protection, a model client, settings APIs and a language picker UI.
- What failed / adjustment: The first frontend run lacked dependencies (`npm ci` fixed it). Vitest 4 did not automatically clean up DOM trees between tests (three queries failed), so explicit Testing Library cleanup was added. OpenAI 3 uses httpx2, so a test-only transport bridge sends its requests through respx's httpx router without network calls.
