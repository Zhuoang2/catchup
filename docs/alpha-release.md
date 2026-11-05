# CatchUp: Alpha Release and Task Backlog

Zhuoang Tao · CS146S Autumn 2026 · 2026-11-05

## Alpha version

CatchUp is an open-source, self-hosted personal digest. Users add the sites, feeds, podcasts, YouTube channels, and X accounts they follow; **Generate digest** collects everything new since each source's last successful check and writes a topic-grouped digest that links to the originals.

**End to end.** Set an OpenAI-compatible model and key (DeepSeek is tested) → paste a URL, preview the feed, confirm → **Generate digest**. CatchUp checks every source, reads a bounded set of linked pages and author replies, summarizes each item once, groups the summaries into topics, and saves the digest. **Latest** shows it and **History** keeps older ones. An optional Chrome/Edge extension follows the current site or X account, or saves the current page for the next run.

**Version and checks.** The alpha is `main` at `f832bb4` (2026-11-03); the last release tag is `v0.1.0` (2026-10-04), and the GHCR `edge` image tracks `main`. To run it, see the README: "Run with Docker" or "Development setup", and "Browser extension". The tests need no network or real model key: 885 backend (97% statement coverage), 263 frontend, and 114 extension tests. The CI checks `backend`, `frontend`, and `docker` are required on `main` (D-010, D-012).

**Feature status.** No screen is a placeholder: features not built yet are absent from the UI and tracked as issues.

| Feature | Status | Notes |
|---|---|---|
| Model settings | Functional | OpenAI-compatible only (D-004); key encrypted. Other adapters (#12) not started |
| Websites, blogs, Bluesky, Mastodon, Reddit (RSS/Atom) | Functional | Reddit ends 2026-11-13, when Reddit stops RSS |
| Podcasts | Functional | Only with a published transcript; no speech-to-text (D-013) |
| YouTube channels | Functional | Best effort: captions opt-in (YouTube's terms); feeds sometimes down |
| X accounts | Functional | User's own pay-per-use API token; 200 reads per run by default (D-025) |
| Digest run, topics, Creator updates | Functional | Topics too fine-grained (#32); quality not yet evaluated (#10) |
| Linked pages and author replies | Partial | Slow, with a misleading progress total (#64); pages saved mid-pass lack context (#70) |
| Images from source sites | Partial | Some picks unclear; alt text not shown (#65) |
| Latest, History, digest language | Functional | |
| Browser extension | Partial | Chrome/Edge, loaded unpacked; may save sponsor text (#62) |
| Docker, Compose, installable PWA | Functional | Local only (D-011); clean-install test pending (#13) |
| Security: local hosts only, cross-site writes and framing refused | Functional | No login; DNS-rebinding fix open (#68) |
| Accessibility: AA contrast, keyboard, axe tests | Partial | Focus and announcements lost on in-place changes (#72); Save errors far from Save (#71) |
| Bookmarks (#8), top-N items (#9), link depth (#54), Bilibili (#40) | Not started | Backlog |

## Demo

Screenshots of the alpha (`f832bb4`) on a local instance.

| | |
|---|---|
| ![Latest digest](../assets/alpha/home-latest.png)<br>**Latest:** the newest digest under the run bar. | ![Run in progress](../assets/alpha/run-progress.png)<br>**A run:** stage, progress, and per-source outcomes. |
| ![Digest with topics](../assets/alpha/digest-topics.png)<br>**A digest:** topics, cited items, "Also read" links, an image. | ![Sources preview](../assets/alpha/sources-preview.png)<br>**Sources:** a pasted URL is previewed before it is saved. |
| ![Settings](../assets/alpha/settings.png)<br>**Settings:** model, digest, YouTube, extension, X accounts. | ![History](../assets/alpha/history.png)<br>**History:** saved digests with their topic titles. |
| ![Extension popup](../assets/alpha/extension-popup.png)<br>**Extension:** follow this site, or add this page. | |

## Backlog

**System.** GitHub Issues in the public repository `Zhuoang2/catchup`, on the project board https://github.com/users/Zhuoang2/projects/1 (D-009; screenshot below). Every issue, with its description, is public.

- One issue per feature, bug, chore, or course deliverable; labels `type:*`, `area:*`, `accessibility`, and `priority:next`.
- Features and fixes are OpenSpec changes linked to their issues (`add-x-accounts` for #41). The issue moves to In Progress when work starts, and the pull request closes it (PR #77 closed #41).
- Later issues came from my testing (#37–#41, #47–#49), reviews (#44, #60, #62), and a live check and system review on 2026-11-01 (#64–#76).
- No assignees: this is a one-person team.

**Counts (2026-11-04).** The board has 57 items: 23 Todo, 1 In Progress (#17, this deliverable), and 33 Done (29 issues and 4 early pull requests). The repository has 54 issues (24 open), 28 merged pull requests, and 26 archived OpenSpec changes.

**Next tasks**, with priorities proposed for the final release on 2026-12-10 (security and course deliverables first):

| Task | Description | Status | Priority (proposed) |
|---|---|---|---|
| #68 Pin `safe_fetch` connections | DNS rebinding: a followed page's links could make a run read local addresses | Todo | High |
| #13 Clean-environment install test | Follow only the README on a clean machine | Todo | High |
| #10 Summary quality evaluation | Check sampled summaries against their originals (target: 90% faithful) | Todo | High |
| #14 Test with the user's own sources | Run CatchUp on the sources the author follows | Todo | High |
| #18 Final release, report, and demo | Course deliverable, due 2026-12-10 | Todo | High |
| #70 Items saved during the linked-page pass | Delivered in the same run without their context | Todo | Medium |
| #76 Unreachable robots.txt means disallow | Follow RFC 9309 for 5xx and network errors | Todo | Medium |
| #72 Keep focus and announcements | Keyboard focus and screen-reader messages on in-place changes | Todo | Medium |

Other open issues, proposed Medium: #71, #73, #64, #65, #32, #62, #8; Low: #12, #4, #9, #11, #40, #43, #54, #60.

![Project board](../assets/alpha/backlog-board.png)
**The project board** (Status: Todo, In Progress, Done).

## AI/LLM tool integration

| Tool | Role |
|---|---|
| Codex | Product discussion, proposal, hand-off (2026-10-01) |
| Claude Code (Opus 5.5) | Research, two proposals and a plan per change (RePPIT skills writing OpenSpec changes), reviews, live checks; sub-agents for research, fact-checks, and independent reviews |
| Factory Droid (GPT-6 Sol where reported) | Implements each `tasks.md` test-first in its own git worktree |
| `/code-review` and a spec sub-agent | A bug review and a spec review with mutation tests after every Droid run (D-016) |
| Design plugin | Critique and WCAG review of the UI prototype (2026-10-06) |
| OpenSpec; `tdd`, `diagnosing-bugs` skills; GitHub Actions | Specs and validation; test-first and reproduce-first rules; required CI |

**How the process changed.** I decide; agents research, plan, implement, and review. Context is written once for people and agents: `AGENTS.md`, read by both Claude Code and Droid (D-002); OpenSpec specs with 10 capabilities, 101 requirements, and 305 scenarios; and a `tasks.md` per change that names each task's test. I choose between proposals, approve each plan (D-001), and approve every merge. In about five weeks this produced 26 OpenSpec changes and 28 merged pull requests. On 2026-11-03 I wrote, "I'm going to sleep. Arrange tonight's tasks yourself, for example fix the issues that are open now" (translated). Claude Code planned five lean changes, had sub-agents implement them because Droid's login had expired, and reviewed them (PRs #78–#82).

**How prompts changed** (real excerpts):

- First Droid hand-off (2026-10-02): "Implement ONLY task group 1 … If a task is blocked or the plan looks wrong, stop and report instead of improvising."
- After tests wrote a real database file (2026-10-03), notes became checks: "Rules for every task, treated as verification criteria (not just notes): tests make no real network calls …"
- Test-first since D-016 (2026-10-07): "write the task's checks as failing tests and watch them fail, then implement until they pass."

**Successes.**

- **Pitfalls in the prompt.** Groups 4–7 of the core flow ran in fresh Droid sessions, with known pitfalls and earlier review findings written into each prompt. None needed required fixes, and all four cost about 1.20M Factory credits, against about 1.94M for groups 1–3 and their fixes in one resumed session (2026-10-03).
- **Security bugs caught in review.** The stored API key could follow a changed provider address through DNS rebinding, a flaw in Claude's own design text (2026-10-03). A plain form on any site could start a paid digest run (#59, D-022).
- **Plan review and research.** A fresh sub-agent's review of the podcast and YouTube plan led to 17 fixes; one item it could not verify, once checked live, would have made Substack newsletters permanent podcasts (2026-10-05). Research found that Reddit stops RSS on 2026-11-13, so the Reddit extractor (#2) was dropped before any code (2026-10-04).
- **UI prototyping.** Five HTML prototype directions and their variants led to the C7 design. The Design plugin reported 12 major design issues and 15 WCAG 2.1 AA issues; the fixes went into the prototype, re-verified by measurement, before the port (2026-10-06).

**Challenges and adjustments.**

- **Mocked tests check the contract we imagined.** 147 mocked tests passed, but the first real DeepSeek run failed: 512-token summary budgets met a thinking mode that is on by default (2026-10-03). An assumption the plan marked "unverified" picked Arabic auto-dubbed captions for an English video (2026-10-05). Every change now gets a live check (D-023).
- **Fix rounds piled up.** I worried that "one patch is patching another patch" (2026-10-21, translated). A meta-review of about 75 fix-round items found 18 real defects, 6 errors in Claude's plans, about 45 test-only pins from mutation testing, and 2 churn. The D-023 stop rules followed: classify findings, one Droid fix round by default, small leftovers in the review commit, and a fresh-eyes check before each Droid run.
- **Plan errors.** Droid stopped twice before coding the redesign because the plan contradicted itself, for example a 20° hue test that the planned colors failed (2026-10-06). Numeric checks are now computed before hand-off, and "stop and report" stays in every prompt.
- **Tests that cannot fail.** A CSS test matched rule text while titles overlapped summaries at 420 and 900 px (#25), and a podcast test passed without its fix (#31). A verification claim now counts only if its test fails under a named mutation, and layouts get a browser check.
- **CI assumptions.** `gh pr merge --auto` merged PR #19 at once because `main` required no checks; required checks followed (D-010).

**Unexpected insights.**

- Real defects came from live checks and reasoning, not from more mocked tests: of the 18 above, most were "found by live checks and by reasoning about the code" (D-023), and my own testing led to #47–#49.
- Many defects start in the plan, not in the generated code. Fresh-eyes checks of plans found 12 false assumptions for the extension (D-024) and 15 issues for X accounts (2026-10-24).
- Written specs make context portable. Fresh sessions that read the OpenSpec files cost less than one long session, and Claude Code sub-agents could stand in for Droid under the same `AGENTS.md` rules (2026-11-03).
