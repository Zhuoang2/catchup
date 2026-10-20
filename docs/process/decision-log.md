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

## D-010 Protect `main` with required CI checks — accepted (2026-10-04)

- Decision: Branch protection on `main` requires the `backend` and `frontend` CI checks to pass before a pull request can merge. Force pushes and branch deletion are blocked.
- Settings: up-to-date branches are not required (`strict: false`), no review approval is required (solo project), and admins are not forced through the rule (`enforce_admins: false`), so small documentation commits can still go straight to `main`.
- Reason: Without required checks, `gh pr merge --auto` merged PR #19 immediately instead of waiting for CI (see `ai-usage-log.md`, 2026-10-04). With required checks, auto-merge waits for green CI.

## D-011 Local deployment only; no hosted demo — accepted (2026-10-04)

- Decision: CatchUp is delivered as a self-hosted open-source project. Users run it locally, from source or as a Docker image published by CI. The course demo runs on the developer's machine. There is no cloud-hosted instance.
- Evidence: On the course forum, a student asked whether the final project must be web-hosted or whether a locally deployed open-source project is fine. Course staff (Mihail Eric) answered: "Locally deployed is completely fine." The only stated restriction is substantial complexity.
- Alternatives: a hosted demo instance (needs access control, a separate spending-capped model key, and runs into cloud-IP blocking by YouTube and Reddit); a temporary tunnel from the local machine (kept as a fallback if a shareable link is ever needed).
- Consequences:
  - Issue #7 drops the hosted demo and access control. It becomes packaging and release automation (Docker image, GHCR publishing).
  - #13 (clean-environment install) carries the "deployment" evidence.
  - Local runs keep the home network, which avoids datacenter-IP blocking.

## D-012 Auto-merge allowed; `docker` added to required checks — accepted (2026-10-05)

- Decision: The repository allows auto-merge, and branch protection on `main` now requires `backend`, `frontend`, and `docker` (the image build plus `scripts/docker-smoke.sh`).
- Reasons:
  - With required checks in place, `gh pr merge --auto` waits for green CI instead of merging at once (compare the PR #19 slip in `ai-usage-log.md`).
  - Requiring `docker` means no merge can break the published image.
- First use: PR #20. Auto-merge was enabled after all six check runs on its head (`d97b79e`) had already succeeded, so it merged immediately, correctly (`b5fec1a`).

## D-013 Podcasts and YouTube use transcripts only; captions are opt-in; no speech-to-text — accepted (2026-10-05)

- **Decision** (change `add-podcast-and-video-sources`, #5 and #6):
  - Podcast episodes are summarized only from transcripts their feeds publish (`<podcast:transcript>`).
  - YouTube videos are summarized only from captions in the video's original language. CatchUp fetches them locally only when the user turns caption fetching on: off by default, with the YouTube Terms of Service conflict stated.
  - Items without a transcript appear once, unsummarized, under "Creator updates":
    - podcasts after a configurable wait (default 7 days)
    - YouTube after a caption wait (default 24 hours) or at once for other failures
  - Long texts are summarized in full, with a single-call budget derived from the model's `context_window`.
- **Alternatives:**
  - Summarizing show notes and descriptions: rejected, because it would claim to cover content that was not processed.
  - The official YouTube Data API: captions can be downloaded only for videos the caller can edit.
  - A third-party transcript service (suggested on #6): it needs a paid account and sends data to a third party.
  - Speech-to-text of podcast audio through a user-supplied key, with ffmpeg in the image (Proposal 2): larger change, and not committed (`docs/handoff.md`). It remains a possible follow-up.
  - Downloading YouTube audio with yt-dlp: the Terms of Service forbid downloading, and it needs PO tokens.
- **Consequences:**
  - Coverage depends on publishers: about 4% of indexed podcast episodes carry transcripts.
  - YouTube RSS itself is intermittently unavailable (404 for all channels for 40+ minutes during testing).
  - Track choice relies on private fields of `youtube-transcript-api`, which is pinned `<1.3`.

## D-014 Local web app, installable as a PWA; no native desktop packaging — accepted (2026-10-05)

- **Decision.** CatchUp stays a self-hosted web application that the user runs locally (D-006, D-011) and opens in a browser. It is made installable as a Progressive Web App:
  - an app manifest (name, icons, theme color)
  - an optional offline page that says CatchUp is not running when the backend is down

  Installed, it opens in its own window with a Dock/Start-menu icon. Delivery stays one Docker image, or a run from source. The next UI work focuses on UI/UX design rather than packaging.
- **Alternatives:**
  - Plain web page only: the same app without install support. The PWA adds little code and gives an app-like window.
  - A native desktop app (Tauri or Electron, bundling the Python backend): it would remove the Docker requirement, but adds multi-platform builds, macOS signing and notarization, and auto-update, plus a second release line next to Docker. The course grades the development process, not packaging, and the risk before the 2026-12-10 demo is high. Kept as a possible stretch goal.
- **Consequences:**
  - The backend must still be started first; a PWA does not remove the Docker or source setup.
  - Install works in Chrome and Edge, and in Safari on macOS via "Add to Dock". Firefox desktop has no install, but works as a web page.
  - `localhost` counts as a secure context, so local installs work.
  - The tech spec (#16) describes the architecture as a local web app plus PWA.

## D-015 UI built as a hand-written CSS design system ported from the C7 prototype; network-first service worker with an offline page only — accepted (2026-10-06)

- **Decision** (change `redesign-ui-ux`, #24): the new interface ports the reviewed C7 prototype CSS into owned stylesheets (tokens, base, layout, components) and small React components, with no runtime UI dependencies.
  - The theme follows the system, and fonts are system stacks with CJK fallbacks.
  - The PWA is a manifest, icons, and a minimal service worker that serves an offline page only when a navigation fails. App code and API responses are never cached.
  - The edition number shown on digests is the digest id.
- **Alternatives:** CSS Modules with Radix UI primitives and `vite-plugin-pwa` (Workbox precache and an update prompt). It was rejected because:
  - The prototype's measured contrast, focus, and grid results would need re-verification after translation.
  - A precache adds stale-shell risk for an app that cannot work without its server.
  - It brings about 7 new dependencies.
  - A modal dialog replaces the reviewed inline delete confirmation.
- **Consequences:**
  - Accessibility details are owned, and checked by axe scans and a token contrast test.
  - Saved digests gain `language` and per-item `source_kind` (migration `0003`) so that the UI can mark language and kinds after settings or sources change.
- **Amendment (2026-10-06, before implementation):** the error color moved from `#a33a00` / `#ff9a62` to `#a34200` / `#ffa65e` (light / dark) so that error, warn, and the brand accent differ by at least 20° in hue (they were 17.3° / 15.1° apart from the accent). Error text stays at ≥ 5.1:1. A state may have no primary action (No new content). Alternative considered: keep the reviewed colors and lower the accent–error threshold to 15°; rejected because the threshold would be chosen after the fact, and the user had asked for error to be clearly separate from the brand red.
- **Amendment (2026-10-07, after the implementation review):** `GET /api/digests` also returns topic titles, the language, and a Creator-updates-only flag, so History needs one request. Alternative considered: keep the list endpoint unchanged and load each digest's detail per row with per-row failures; rejected because it stays N+1 and gets slower as history grows. While a run is in progress, Generate stays a disabled primary button as in the prototype. Digest languages are mapped to BCP 47 tags, and values with no known tag (such as "Same as original") get no `lang`.
- **Amendment (2026-10-07, after the final review of the whole change):**
  - With a model configured but no sources, Generate offers "Add sources" as the primary action and shows Generate as unavailable with the reason. Alternative considered: keep Generate enabled; rejected because the run can only end in "No new content".
  - Feed URLs are shown in full and wrap. Alternative considered: the 2-line clamp from the design review; rejected because the spec asks for the full URL, a clamp hides information, and a `title` tooltip is not available on touch or to keyboard users.
  - Each screen has its own document title.
  - A failed run is announced once, through the status region.
  - The cached offline page refreshes itself after successful navigations.

## D-016 Test-first implementation and a diagnose-first bug path, using the `tdd` and `diagnosing-bugs` skills — accepted (2026-10-07)

- **Decision:** two shared skills from `mattpocock/skills` (MIT) are installed in the repository: `tdd` and `diagnosing-bugs`. They live in `.agents/skills/`, are symlinked into `.claude/skills/`, and are pinned by hash in `skills-lock.json`. `AGENTS.md` makes them part of the workflow:
  - Droid completes each `tasks.md` task test-first: a failing test for the task's spec scenarios and verification items, then the implementation, one slice at a time.
  - Bugs, and review findings whose cause is unknown, are reproduced with a failing check before any fix, then fixed with a regression test.
- **Adaptation:** `tdd` asks the agent to confirm the test seams with the user before writing tests. Droid runs unattended, so the seams named in each task's verification count as agreed. Planning therefore has to name the seams, and a task without a testable seam is a reason to stop. `diagnosing-bugs` asks to show ranked hypotheses to the user; unattended runs report them in the final report and commit message instead.
- **Why:** Droid works alone in a worktree, and its results are seen only at review. In `redesign-ui-ux` the review found Generate tests that had been lost and fixes whose cause had not been reproduced; writing the test first and reproducing first move those problems earlier.
- **Alternatives:**
  - Keep the current flow, where tests are written alongside the code and each task has a verification list. Rejected: nothing makes the test exist before the code.
  - Copy the pictured flow exactly (`/opsx:propose` for every change). Rejected: substantial changes keep the RePPIT research and two-proposal steps (2026-10-01), which the course grades as evidence.
- **Consequences:** Droid runs take longer and use more credits. The first trial is the next small change, for example #23. The current `redesign-ui-ux` fix round was already done without these skills.
- **Review:** before installing, Claude read every file in both skills. They contain instructions only; the bundled `hitl-loop.template.sh` only prompts a human and prints the answers. The installer's own assessment reported no alerts.
- **Amendment (2026-10-07): a fixed review step after every Droid run.** The fix round of `redesign-ui-ux` had been re-checked only functionally, with no independent code review. Every Droid run, including fix rounds, now gets two reviews of its diff: Claude Code's built-in `/code-review` for bugs, and an independent sub-agent that checks the diff against the OpenSpec change, quoting the spec line for each finding (missing or partial, not asked for, implemented wrongly, verification claimed but not tested). Claude Code verifies each finding before any change.
  - **Alternative considered:** install Matt Pocock's `code-review` skill (a Standards axis and a Spec axis in parallel sub-agents). Rejected for now, for four reasons:
    - Its name collides with the built-in `/code-review`.
    - Its Standards axis needs a coding-standards file that the repository does not have, so it would reduce to a generic code-smell list.
    - It requires a separate setup step (`docs/agents/issue-tracker.md`).
    - The project's review sub-agent already checked against the spec. The missing piece was running the review on every round.
  - Its three spec questions were adopted into the sub-agent brief.

## D-017 The main screen shows the latest digest, with a compact run bar; navigation item "Latest" — accepted (2026-10-16)

- **Decision.** `/` shows the newest saved digest in the existing reading layout. A run bar above it holds Generate, the source count, and the current run's progress, outcomes, and result.
  - When a run saves a digest, the new digest replaces the shown one in place, without moving focus.
  - With no digest saved yet, `/` keeps the Generate guidance and rail.
  - The first navigation item is renamed "Latest". A new `GET /api/digests/latest` returns the newest digest, or `null`.
  - Planned as OpenSpec change `show-latest-digest-on-home` (issue #27).
- **Why.** Reading the digest is CatchUp's main activity. The user asked that the main screen show it instead of sending people to History after each run (issue #27, after the redesign's manual test).
- **Alternatives:**
  - Keep Generate as the main screen and embed the latest digest below it. Rejected:
    - Reading would stay below the hero, the cards, and the rail.
    - Two grids would be mixed on one page.
    - The whole reading layout would need heading-level variants.
  - Reuse the first entry of `GET /api/digests` and then the detail request, with no new endpoint. Rejected: two requests, and the list has no limit.
  - Navigation labels "Today" or "Front page". The user chose "Latest".
- **Consequences:**
  - "View digest" disappears from the finished-run state, which now offers no primary action.
  - The main screen shows no side rail while a digest is shown; the source count moves into the run bar.
  - The single-item topic layout (#25) becomes more visible. It stays a separate change, planned next.

## D-018 Each digest item is a row with its title beside its summary; one width for every item — accepted (2026-10-16)

- **Decision.** On wide windows, each item in a topic is one row:
  - its source line and linked title in page columns 4–6
  - its summary in columns 7–12, ending at the content's right edge
  - The summary keeps the former long-item measure: 580 px at 1440 px, about 35 CJK or 75 Latin characters per line.
  - The long/short item classes and their 140-character threshold are removed.
  - Planned as OpenSpec change `improve-single-item-topics` (issue #25).
- **Why.** Long items spanned 6 of the 9 item columns, and a long item after a long item restarted the row. Nearly every real summary counted as long, so in a real Chinese digest 14 of 16 rows ended 302 px short of the content edge. Since D-017, that digest is the main screen.
- **Alternatives:**
  - Long items across all 9 item columns, with the summary in two text columns (Proposal 2). Rejected:
    - It splits 2–4 sentence summaries and key-point lists across columns.
    - It still leaves a gap after a short item.
    - It keeps the 140-character rule.
  - A 4 : 8 split for single-item topics (suggested in #25). Rejected: about 47 CJK characters per line, and it does not fix rows of consecutive long items.
  - Fewer, broader topics through the grouping prompt (Option G). Split out to issue #32: once the layout fills every row, it is a digest-quality question.
- **Consequences:**
  - No vertical rule between an item's title and its summary.
  - The topic column stays 3 columns wide.
  - Short items take a full row of their own.
  - At 900 px and below, the layout is unchanged. Items stack (source line, title, summary) at 1100 px and below. This was decided after review, when titles wrapped to 4–5 lines in a 191 px heading column at 901 px.

## D-019 A run's per-source outcome means "this run includes something from this source" — accepted (2026-10-16)

- **Decision.** A run reports `new_items` for a source when it includes at least one of that source's items, either summarized or under Creator updates. Where the item came from does not matter:
  - an entry first seen in this check
  - an entry recorded when the source was added
  - an item carried over from an earlier run
- **Not counted:** items waiting for a transcript or captions, deferred items, and skipped Shorts. The outcome is set in the runner once the run has chosen its items, before summarizing. The labels "New items" and "No new items" stay. Planned as OpenSpec change `fix-new-source-check-outcome` (issue #31), on the lean path (`/opsx:propose`).
- **Why.** The outcome described only what the feed check discovered, while the run digests every pending item. A newly added source therefore said "No new items" next to its own items in the digest, found on a local instance during the #27 review. Carried-over items, late transcripts, and skipped Shorts showed the same mismatch.
- **Alternatives:**
  - "The source still has pending items." Rejected: a podcast waiting for its transcript would show "New items" on every run while nothing from it appears.
  - Fix only the first run after adding a source. Rejected: the other mismatches would remain.
  - Show counts such as "3 new items". Rejected for now: a larger change to the API, the UI, and the tests.
- **Consequences:**
  - During collecting, a source with only carried-over items can briefly show "No new items" before its final outcome.
  - A run that fails after choosing its items keeps `new_items` for those sources.

## D-020 Gather bounded context for website items during the run; the summary judges relevance and cites what it used — accepted (2026-10-19)

- **Decision.** For each pending website item, a context pass reads, once:
  - up to 8 related linked pages (the rules drop tag, navigation, share, and login pages, as well as x.com, images, and PDFs);
  - the author's own replies in the post's comments.

  The pass runs after the sources are checked. It is bounded per page, per item, and per run (60 fetches); it honors robots.txt; and it never fails the run. The summary call receives the context as labeled sections, uses only what relates, and returns the references it used. The digest shows them as "Also read" links taken from stored data. Planned as OpenSpec change `add-linked-pages-and-author-replies` (issue #48), a full RePPIT change.
- **Why.** Short posts and announcements carry their point in linked pages, and authors add context in replies. Both were found in user testing on 2026-10-19 (F7, F8). The user chose this proposal with one change: "more than three links", with a user-facing depth setting later (#54).
- **Alternatives:**
  - Model-picked links at summary time (Proposal 2). Rejected: an extra call per item, fetches inside the summarizing stage, nondeterministic selection, and re-fetching after a failed run.
  - Reusing the item's article fetch for comments. Rejected for simplicity.
- **Consequences:**
  - Runs fetch more and cost more tokens.
  - Only server-rendered, WordPress-style comments and comment feeds are read.
  - Existing items get no context.
  - **Amended after review (2026-10-19).** When context arrives for an item that already has a summary, the summary is cleared and redone with the context (user: "As you recommend, one more fix round", translated). Link rules match whole path segments, and are applied to the final URL after redirects. In a second round, an item that the per-run limit cuts off keeps the context it already gathered, because a successful run summarizes every pending item. The first round had rolled such items back (user: "As you recommend, one more fix round", translated).

## D-021 The summary call chooses up to three important images, shown from their source sites — accepted (2026-10-19)

- **Decision.** Parsing keeps up to 8 image candidates per website item or YouTube video, with no avatars, icons, or tracking pixels. The summary call chooses at most 3 that show something the summary relies on, each with a short alt text, or none. The choice is stored with the summary, and snapshotted into the digest. The reading layout loads the images from their sites, lazily and with no referrer. A Settings toggle, "Show images from source sites" (default on), turns this off. Planned as OpenSpec change `add-item-images` (issue #49), a full RePPIT change, after #48.
- **Why.** Charts, screenshots, and diagrams carry information that text summaries lose (user testing, F9). The user decided:
  - the model chooses;
  - more than one image when several matter;
  - try loading from the source site first.
- **Alternatives:**
  - One image-selection call for the whole digest, after grouping. Rejected: it judges from summaries only, and adds a run stage.
  - Storing image copies. Rejected for now, at the user's request.
  - `og:image`. Left out: the page is not kept after extraction, and it is usually the feed's lead image or the site icon.
- **Consequences:**
  - Opening a digest contacts image hosts. This is documented in Settings and the README.
  - Digests can show up to 3 images per item, with no cap per digest yet.

