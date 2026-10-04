# Decision Log

Status values: **proposed** (recommended, awaiting user confirmation), **accepted**, **superseded**.

## D-001 Development workflow: OpenSpec + RePPIT + Factory Droid — accepted (2026-10-01)

- Decision: Manage requirements with OpenSpec. For each change, Claude Code researches, writes two proposals, and plans (RePPIT skills). Factory Droid implements `tasks.md`, and Claude Code reviews.
- Alternatives: Claude Code alone; Droid alone; plain issues without specs.
- Reasons: Specs give both humans and coding agents the same written context, which the course grades directly. Splitting planning/review from implementation across two tools from different model vendors gives an independent review. The user has 3 months of Factory Plus.
- Consequences: Plans must be committed before Droid runs (`droid exec -w` starts a worktree from the current commit). The user approves at two gates: proposal choice and plan.
- Supersedes: `docs/handoff.md` §9, which said OpenSpec/RePPIT were not the established CatchUp workflow.

## D-002 Single project instruction file — accepted (2026-10-01)

- Decision: `AGENTS.md` holds the project context; `CLAUDE.md` is a symlink to it.
- Alternatives: two separately maintained files; `CLAUDE.md` with an `@AGENTS.md` import.
- Reasons: Droid reads `AGENTS.md` and Claude Code reads `CLAUDE.md`. One file prevents drift between the tools.

## D-003 Keep the course brief out of the public repository — accepted (2026-10-01)

- Decision: `CS146S Final Project Description.pdf` and `docs/course-requirements.pdf` stay local and are listed in `.gitignore`.
- Reasons: The repository will be public (open-source project); the brief is course staff material.

## D-004 First model adapter: OpenAI-compatible Chat Completions — accepted (2026-10-02)

- Decision: Implement an OpenAI-compatible adapter first (configurable base URL, model, key). Develop and test against DeepSeek, which the user uses. Other adapters (e.g. Anthropic native) come later behind the same interface.
- Reasons: DeepSeek exposes an OpenAI-compatible API. The same adapter also covers OpenAI, OpenRouter, and local Ollama, so "user picks a supported model" is met early.
- Consequence: In cloud-model mode, collected content is sent to the configured provider (here DeepSeek). Setup docs must say so.

## D-005 Public GitHub repository from the start — accepted (2026-10-02)

- Decision: Public repo `Zhuoang2/catchup`. Development happens in the open; the license is MIT (D-008).
- Pre-publish check: Removed the Google Doc URL from `docs/handoff.md` and `docs/proposal.md`. Course brief PDFs are gitignored (D-003). No credentials found in tracked files.

## D-006 Tech stack: FastAPI + React — accepted (2026-10-02)

- Decision: Python backend (FastAPI, SQLite via SQLAlchemy) exposing a JSON API; React + Vite + TypeScript frontend, built to static files and served by FastAPI so deployment is a single container.
- Alternatives: FastAPI + HTMX (one language, simplest, but endpoints return HTML fragments, so there is less API design and UI prototyping to show, and a future browser extension would need a separate JSON API); Next.js full-stack TypeScript (one language, but weaker libraries for feed parsing, article extraction, and transcripts).
- Reasons: The hardest part is backend collection (feeds, time boundaries, dedupe, failures), where Python libraries (feedparser, trafilatura) are strongest. The course grades API design and UI prototyping, and a JSON API is reusable by the planned browser extension.
- Cost: Two languages and two test setups. Implementation is split between Factory Droid and Claude Code.

## D-007 Split between RePPIT and OpenSpec commands — accepted (2026-10-02)

- Decision: Full RePPIT (research → two proposals → plan) for new features and substantial changes; `/opsx:propose` for small changes; Droid implements with `/opsx-apply`; Claude Code reviews and runs `openspec archive` after the user approves. About 6–8 full RePPIT changes for the course.
- Context: `openspec init` installs its own `propose`/`explore` skills, which overlap with RePPIT's proposal and plan steps. Without a rule, an agent could switch between the two for the same request.
- Reasons: RePPIT adds a research step with code references and a two-option user choice; OpenSpec adds living specs, validation, and archive history. The lean `/opsx:propose` path keeps small changes cheap, so process overhead stays proportionate for a solo 10-week project.

## D-008 License: MIT — accepted (2026-10-04)

- Decision: Release CatchUp under the MIT License, with copyright held by Zhuoang Tao.
- Alternatives: Apache-2.0 (adds an explicit patent grant and more notice requirements); GPL-family (requires derivatives to stay open).
- Reasons: The user chose MIT. It is the simplest permissive license and fits a self-hosted tool that others may adapt.

## D-009 Project board: GitHub Projects with repository issues — accepted (2026-10-04)

- Decision: The backlog is tracked as issues in `Zhuoang2/catchup`, shown on a GitHub Projects board linked to the repository.
- Alternatives: Linear, Jira, Trello (all accepted by the course brief).
- Reasons: The board sits next to the code, pull requests, and CI. PRs can close issues automatically, and the process evidence for the course stays in one place.
