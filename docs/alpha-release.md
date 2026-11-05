# CatchUp: Alpha Release and Task Backlog

Zhuoang Tao · CS146S Autumn 2026 · 2026-11-05

*#n is an issue or pull request in https://github.com/Zhuoang2/catchup; dates point to entries in `docs/process/ai-usage-log.md`.*

## Alpha version

CatchUp is an open-source personal digest that runs on the user's own computer. Users add the sites, feeds, podcasts, YouTube channels, and X accounts they follow and connect their own AI model account; **Generate digest** collects everything new since the last check, summarizes and groups it by topic, and links each summary to its original.

The alpha is commit `f832bb4` on the main branch (2026-11-03); the README explains setup. Its tests need no network or model account: 885 backend tests exercise 97% of the backend code, plus 263 web-app and 114 extension tests, and the backend, web-app, and Docker checks must pass before a change merges.

No screen is a placeholder; unbuilt features are absent from the app and tracked as issues.

| Feature | Status | Notes |
|---|---|---|
| Model settings | Functional | OpenAI-compatible services (DeepSeek tested); key stored encrypted. Other kinds of model service not started (#12) |
| Sources: sites and blogs with feeds, Bluesky, Mastodon, Reddit, podcasts, YouTube, X accounts | Functional | Podcasts need a published transcript; YouTube captions are off by default (per YouTube's Terms of Service; see README); X needs the user's own pay-per-use API key; Reddit ends its feeds on 2026-11-13 (TechCrunch, 2026-09-30) |
| Digest run with progress, topics, Latest and History | Functional | Topics are often too fine-grained (#32); summary quality not yet measured (#10) |
| Reading linked pages and author replies | Partial | Slow, and its progress count overstates the work (#64) |
| Images from source sites | Partial | Some chosen images mean little without the article (#65) |
| Browser extension | Partial | Chrome and Edge, installed by hand; on short pages it can save sponsor text (#62) |
| Local install and security | Partial | No user accounts; by default it answers only requests addressed to localhost and refuses changes sent from other websites. One known gap (#68); clean-machine install test pending (#13) |
| Accessibility | Partial | Contrast and automated accessibility checks pass; keyboard focus is lost on some screen updates (#72) |
| Bookmarks (#8), top-N items (#9), link depth (#54), Bilibili (#40) | Not started | |

## Demo

Screenshots of `f832bb4` on a local test instance with English digests.

| | |
|---|---|
| ![Latest digest](../assets/alpha/home-latest.png)<br>**Latest:** the newest digest under the Generate bar, with its six topics and the first summaries. | ![Run in progress](../assets/alpha/run-progress.png)<br>**A first run:** the stages, items summarized so far, and a result for each source. |
| ![Sources preview](../assets/alpha/sources-preview.png)<br>**Sources:** a pasted address is previewed before it is saved, above two saved sources. | ![Extension popup](../assets/alpha/extension-popup.png)<br>**Extension:** follow this site, or add this page to the next digest (popup and page captured separately). |

## Backlog

The backlog is the public issue list (https://github.com/Zhuoang2/catchup/issues), organized on a GitHub Projects board that is private for now, shown below with each task's title, status, and priority. Most issues have type and area labels; each feature or fix has a written plan linked to its issue, and its pull request closes the issue.

On 2026-11-04 the board has 57 items: 23 Todo, 1 In Progress (#17, this document), and 33 Done. The 24 open issues are 6 High, 10 Medium, and 8 Low priority. No assignees are used (one-person team). The next tasks:

| Issue | Task | Status | Priority |
|---|---|---|---|
| #68 | Stop a followed page from making CatchUp read the user's local network (security) | Todo | High |
| #13 | Install on a clean machine using only the README | Todo | High |
| #10 | Measure summary quality on real sources (target: 90% faithful) | Todo | High |
| #14 | Run CatchUp on the sources the author follows, and record the results | Todo | High |
| #18 | Final release, report, and demo, due 2026-12-10 | Todo | High |
| #70 | Pages saved while a run reads linked pages are summarized without their linked pages | Todo | Medium |

![Project board](../assets/alpha/backlog-board.png)
**The project board** (table view): the 24 open tasks by priority, with Title, Status, linked pull requests, Priority (column "P…"), and Labels.

## AI tool integration

| Tool | Role |
|---|---|
| Codex | Product discussion and the proposal (2026-10-01) |
| Claude Code (Opus 5.5) | Research, plans, HTML prototypes of the interface with a design and accessibility review, code reviews, checks in the running app; helper agents for research and independent reviews |
| Factory Droid (GPT-6 Sol where reported) | Writes the code and tests for each plan, in a separate copy of the repository |
| OpenSpec, GitHub Actions | Written requirements and task lists; automatic checks on every pull request |

**How the process works.** Context is written once for people and agents: one instruction file for both coding tools (`AGENTS.md`), OpenSpec specs (101 requirements, 305 example scenarios), and a task list per change that names each task's test. New features get research and two proposals for me to choose from (11 of 26 changes), small fixes a one-step plan; I approve plans and merges, or authorize an overnight queue in advance. Since 2026-10-07 the rules require a bug review (`/code-review`) and a spec review by another helper agent after every Droid run. In about five weeks (2026-10-01 to 2026-11-03) this produced 26 changes and 28 merged pull requests; every one of the 455 commits on `main` (merges aside) was co-written by Droid or Claude Code, while I chose, approved, and tested.

**How prompts changed** (real excerpts):

- After a review found that the tests wrote a database file into the project folder (2026-10-02), the rules became checks (2026-10-03): "Rules for every task, treated as verification criteria (not just notes): tests make no real network calls …"
- Test-first since 2026-10-07, after the redesign review found lost tests and fixes whose cause was never reproduced; the 2026-10-20 prompt for #59: "write the task's checks as failing tests and watch them fail, then implement until they pass."

**Successes.**

- **Security bugs caught in review and research.** A review found that a malicious web page could make CatchUp send the stored model key to the page's own server, a flaw in Claude's own design (2026-10-03). Extension research found that any website could start a run that spends the user's model credit (#59).
- **Independent plan review.** A helper agent that had not seen the planning reported 20 possible problems in the podcast and YouTube plan, and 17 were fixed. A second-round item it could not verify, tested on live feeds, showed that some Substack newsletters would have become podcasts for good (2026-10-05).
- **Overnight work.** On 2026-11-03 I wrote, "I'm going to sleep. Arrange tonight's tasks yourself, for example fix the issues that are open now" (translated). Helper agents planned four of five small fixes and, because Droid's login had expired, implemented all five; Claude Code planned the fifth and reviewed them all (PRs #78–#82).

**Challenges and adjustments.**

- **Passing tests did not prove the behavior.** 147 tests with a simulated model passed, yet the first real DeepSeek run returned 4 of 11 summaries empty: summaries had a short length limit, and DeepSeek's documentation says its step-by-step "thinking" mode is on by default (2026-10-03). A layout test that only checked that a style rule existed passed while titles overlapped summaries (#25). Now a new check must fail before its fix, an existing check must fail when the code is deliberately broken, and a check in the running app is required. It is not always on time: the real-model run for #66 and #67 came only after their merge (2026-11-04: one run, 50 items, 10 topics, the new error handling was not needed).
- **Fix rounds piled up.** I worried that "one patch is patching another patch" (2026-10-21, translated). A review of about 75 fix-round items found 18 real defects, 6 errors in Claude's plans, about 45 extra tests added only to catch deliberately broken code, and 2 needless changes. Stop rules followed: sort findings first, one fix round by default, and a fresh agent checks each task list before implementation.
- **Plan errors.** On the redesign, Droid stopped twice before writing code because the plan contradicted itself, such as a color test that the planned colors failed (2026-10-06). Plan numbers are now checked before hand-off; the prompt's "stop and report instead of improvising" kept these errors cheap.

**Unexpected insights.**

- Most of the 18 real defects were "found by live checks and by reasoning about the code", not by more simulated tests.
- Several of the costliest defects started in the plan, not in the generated code: the model-key leak above, and 12 false assumptions that a fresh agent found in the extension plan before any code was written.
