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

## 2026-10-02 — Core flow group 1 implementation (Factory Droid, GPT-6 Sol)

- Purpose: Implement only tasks 1.1–1.5, the application scaffold, migration, UI routes, static serving, documentation, and CI.
- Prompt (user, excerpt): "Implement ONLY task group 1 (tasks 1.1 to 1.5) of OpenSpec change add-core-digest-flow using the openspec-apply-change skill. ... Work through tasks 1.1-1.5 in order and check off each task in tasks.md only after its verification passes. Do not start group 2. ... Commit when group 1 is done."
- Outcome: Backend health/error tests, SQLite/Alembic startup test, frontend navigation test/build, SPA/API isolation test, development setup, and CI. Four backend and one frontend tests pass locally. No real key or live network is needed for the tests.
- What failed: A first static fallback route shadowed a test-added API endpoint (one backend test failed). Changed the fallback to serve only 404 responses outside `/api`, then all four tests passed. The initial `npm ci` reported two moderate Vitest dev-dependency advisories; upgrading to patched Vitest 4.1.11 cleared `npm audit` while tests and build still passed.
- Adjustment: Checked each task's stated verification before updating its checkbox. Left application features in later groups unimplemented.

## 2026-10-02 — Group 1 review fixes (Factory Droid, GPT-6 Sol)

- Purpose: Correct issues found in review of the scaffold before starting group 2.
- Prompt (user, excerpt): "Code review of your group 1 commit 0da6d26 found issues. Fix them on branch add-core-digest-flow, still within group 1 (do not start group 2): ... Tests must never touch a real data dir ... Change to openai>=3,<4 ... Move AppError ... make digest_runs.digest_id a plain nullable integer ... [optional] Upgrade [Vite and TypeScript] only if npm test, npm run build and npm audit stay clean."
- Outcome: Test applications use a temporary data directory; a sentinel-directory test detects accidental writes to the configured location. OpenAI 3 is locked, shared errors are independent of the app module, and the digest table cycle is removed. The optional frontend upgrade passed tests, build, and audit.
- What failed / adjustment: No checks failed in this round. Added regression tests for the two database issues, and updated the Node requirement in the README to match Vite 8.
