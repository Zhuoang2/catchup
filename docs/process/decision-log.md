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
  - **Amended after review (2026-10-19).** Duplicates are exact URL matches, because some hosts tell images apart only by the query string. Feed alt text and captions are quoted in the prompt as data, and the model writes alt text in the language of the summary. Four limits of the filters are recorded, not changed (user: "As you recommend, one more fix round", translated). Images whose URL is only in `data-src` or `srcset` are not supported, because feedparser's sanitizer removes those attributes. The user chose to record this rather than parse each feed a second time.

## D-022 Refuse write requests that a browser sends from another origin — accepted (2026-10-20)

- **Decision.** The server refuses a `POST`, `PUT`, `PATCH`, or `DELETE` when its `Origin` header does not match the request's `Host` (host and port), or is `null`, or when `Sec-Fetch-Site` is `cross-site` or `same-site`. It answers 403 `cross_site_request`, and does nothing. Requests with neither header (tools) and `GET` requests are unchanged. The FastAPI floor rises to 0.132, whose strict content-type check keeps JSON routes closed to simple requests. Planned as OpenSpec change `refuse-cross-site-writes` (issue #59), a lean change.
- **Why.** During the research for the browser extension (#58), Claude found that a plain form on any web page could start a digest run, because `POST /api/digest-runs` takes no body and the server checked only `Host`. That spends the user's model tokens. The user chose to fix this first (user: "As you recommend, choose Proposal 1, fix the security issue first", translated).
- **Alternatives:**
  - A CSRF token. Rejected: CatchUp has no sessions or cookies, and every request would change.
  - A required custom header. Rejected: every write in the frontend would change, and it would block the future extension's requests until CORS exists.
  - CORS configuration. Rejected: it controls reading responses, not whether a simple request is sent.
  - Requiring JSON on `POST /api/digest-runs` alone. Rejected: it fixes one route, and leaves future bodiless routes open.
- **Consequences:**
  - A page on another local port, such as `http://localhost:3000`, can no longer change CatchUp's data.
  - A reverse proxy must pass the browser's `Host` header, which `CATCHUP_ALLOWED_HOSTS` already assumes.
  - The browser extension (#58) will add an exception for requests with a valid extension token, at the same decision point.

## D-023 Classify review findings, and stop fix rounds early — accepted (2026-10-21)

- **Decision.** Fix rounds follow the stop rules now in `AGENTS.md`, under "Fix rounds and when to stop". It amends D-016's review step:
  - classify every finding first, into a real defect, a plan error, a test-only gap, or churn;
  - one Droid fix round by default;
  - small leftovers go into Claude Code's review commit;
  - a fresh-eyes check of each task group before Droid runs;
  - re-derive rather than re-patch code that a round already patched;
  - the Docker smoke script and the live check are required.
- **Why.** The user worried that fix rounds were "one patch patching another patch" (2026-10-21, translated). An independent meta-review then classified about 75 fix-round items across #48, #49, and #52:
  - 18 were real defects, mostly found by live checks and by reasoning about the code;
  - 6 corrected errors in Claude's own plans, plus 1 task dropped for a false library assumption;
  - about 45 were test-only pins driven by mutation testing, at 8–15 test lines per source line;
  - 2 were churn.

  Only one plan error changed behavior: #48's budget rollback. It left vestigial flags in `context/gather.py`. The second rounds of #49 and #52 changed no behavior. Mutation testing was most useful for finding tests that could not fail, and it missed #49's broken Docker smoke script.
- **Alternatives:**
  - Keep re-reviewing until no survivors remain. Rejected: mutation testing always finds another marginal survivor, so rounds never end.
  - Drop mutation testing. Rejected: it found tests that could not fail, such as the swallowed respx errors in #48, a long-transcript test in #49 that passed with the wrong prompt, and the host-order test in #59.
- **Consequences:**
  - Claude Code may now commit small test and doc fixes directly in its review commit. That is a change from "Droid implements, Claude reviews", and the user approved it.
  - The layering left by #48 (budget signals, vestigial flags), a quadratic lookup in `context/comments.py`, and the repeated poll steps in `Home.test.tsx` go to a low-priority cleanup issue, #60.
  - #59 was the first change handled this way: no second Droid round. Claude added three review tests, and skipped two proposed items as patch on patch.

## D-024 A click-to-capture browser extension for Chrome and Edge — accepted (2026-10-21)

- **Decision.** A Manifest V3 extension for Chrome and Edge, in `extension/`, with a popup and no background worker. It offers:
  - **"Follow this site"**, through the existing preview and confirm;
  - **"Add this page to my next digest"**, which reads the active tab only on the user's click: the page as rendered, and on an X post, the author's own visible replies;
  - **"Open CatchUp"**.

  Saved pages wait under a built-in "Saved from browser" source, a fourth kind that is never checked. The next manual run summarizes them under the page's site name. The server never fetches the saved page itself.

  The extension authenticates with a token that is shown once in Settings, and revoked by "Disconnect". The token is accepted only on the extension's routes, as the one exception to D-022.

  Planned as OpenSpec change `add-browser-extension` (issue #58), a full RePPIT change.
- **Why.**
  - Users want to follow the site they are reading in one click.
  - They want content behind a login: F5 and F8, and an X post with the author's replies (#41).
  - The server cannot read such content, by design.
  - The user chose Proposal 1 on 2026-10-20 ("As you recommend, choose Proposal 1, fix the security issue first", translated). On 2026-10-21 they chose Chrome and Edge, a popup, copying a token, and X with the author's own replies.
- **Alternatives:**
  - **The extension as a logged-in collector of followed accounts** (Proposal 2). Rejected:
    - X's automation rules list scripting the website among suspension risks, and its terms prohibit scraping;
    - it needs broad host permissions;
    - it depends on the browser being open.
  - **The X API** for following accounts. Kept as a separate option (#41): pay-per-use, $0.005 per post read.
  - **A side panel**, a pairing code, and a background service worker. The user chose otherwise, or they are unnecessary.
  - **Recognizing the extension by its `Origin`.** Rejected: the value is undocumented, and any extension can send one.
- **Consequences:**
  - A new package, `extension/`, with its own CI job. It is not part of the Docker image.
  - Migration `0006_captures`.
  - Saving X pages is at the user's own risk, and the README says so.
  - Firefox, Safari, and Web Store publishing come later.
  - A fresh-eyes check (D-023) before Droid's run found 12 false assumptions in the first plan, all corrected. For example: extractor functions lose their module scope when Chrome injects them; jsdom has no `innerText`; the new Settings section would have submitted the model form.


## D-025 Follow X accounts through the X API, with the user's own app-only token — accepted (2026-10-24)

- **Decision.** CatchUp follows X accounts as a fifth source kind, "X account".
  - It reads them only through the official X API, with an app-only Bearer token from the user's own X developer account.
  - The token is stored encrypted like the model key. It is asked for in place the first time an account is followed: on the Sources page, or in the extension, which may save it only when none is saved. Settings manages it.
  - Each run reads each account's posts since the last read. Retweets and the creator's replies to other people are left out; the creator's replies in their own thread are kept as author replies.
  - At most `CATCHUP_X_READS_PER_RUN` posts are read per run (default 200, about $1). Posts that do not fit wait for the next run, and the run reports the reads and the accounts waiting.
  - A delivered post's text is cleared.

  Planned as OpenSpec change `add-x-accounts` (issue #41), a full RePPIT change.
- **Why.**
  - After the manual check of #58, the user said that adding single posts has little value, because they can read them directly; following accounts is the need (2026-10-22).
  - Reading X without the API is against its terms, and scripting the site risks the user's own account (D-024).
  - On 2026-10-24 the user chose Proposal 1. They also chose to skip replies to other people, a 200-post limit with waiting posts, and a token prompt in the extension.
- **Alternatives:**
  - **Sign in with X (OAuth 2.0 with PKCE),** through the user's own public-client App, with a following-list picker (Proposal 2). Not chosen for now:
    - a loopback callback is unverified;
    - refresh tokens and expiry add work;
    - the picker costs $0.010 per account listed.
  - **The extension calling the X API itself.** Rejected: posts would be read only on a click, and the extension would need access to `api.x.com`.
  - **Scraping, or a logged-in collector.** Rejected (D-024).
  - **Dropping posts beyond the limit.** Rejected by the user.
- **Consequences:**
  - Migration `0007_x_accounts`, a new X API client, and the extension token's allow-list gains `PUT /api/settings/x`.
  - X API reads are billed to the user's developer account. README advises a spending limit in the X console, and quotes X's Developer Policy on credentials, with the reading that the token belongs to the instance's owner and never leaves their computer.
  - X's field names are settled by a probe that the user runs with their own token, before Droid runs.
  - X's Developer Agreement counts summaries as derived X Content, which must be deleted when access ends, or on request. CatchUp cannot delete single digests, so Settings gains "Delete all X data" (user decision, 2026-10-26).
  - **Fix rounds, and one exception to D-023 (2026-10-28).** Three Droid fix rounds followed the review of the first run; the third came from an independent review of the whole change, which the user asked for. After the review of round 3, the user chose to have Claude make two small behavior fixes in its review commit, about 5 source lines with tests and named mutations, instead of a fourth Droid round: `safe_fetch` mapping an unparsable redirect target to `invalid_url`, and a failed run showing only its X reads. After the user's live check and a system review (2026-11-01), the user again chose review-commit fixes for small items in this change: the billing note's layout, the danger button's background, `secure_delete` on every connection, the hook's token patterns, and the token error's field.

## D-026 Save the model settings after a successful Test connection — accepted (2026-11-06)

- **Decision.** In Settings, a successful **Test connection** saves the configuration that was tested: the base URL, the key when one was entered, and the selected model, or the first listed model when the selected one is not listed. The page sends the existing `PUT /api/settings/model` after the test.
  - While the base URL and key fields match the saved configuration, choosing another model saves it right away. Saves run one at a time, in order.
  - Digest and YouTube settings still need **Save**, which keeps saving all fields.

  Planned as the lean OpenSpec change `save-model-after-test` (issue #85).
- **Why.**
  - On 2026-11-04 the user tested a key on a fresh instance and left Settings without saving, so Home still asked them to set up the model.
  - A successful test reads like the setup is done, and **Save** sits at the bottom of the page.
  - The user suggested saving automatically after a test (2026-11-04) and approved the plan (2026-11-06).
- **Alternatives:**
  - **Keep explicit saving.** Show "Not saved yet" next to the test result, or add a Save button in the model group. This is smaller, but the user preferred automatic saving.
  - **A `save` flag on `POST /api/settings/model/test`.** Rejected: it duplicates the save rules in the test endpoint and makes a read-only request write.
  - **Never save on a model choice.** Rejected: it brings back the same trap for anyone who changes the fallback model.
  - **Save a model choice with whatever the fields hold.** Rejected: after a failed test of an edited key or address, the menu still lists the last good provider's models, so the choice would store an untested key or address.
- **Consequences:**
  - Testing a new key replaces the saved key. The key field's hint and the success message say so.
  - Test errors that are not tied to a field move from the bottom of the page into the Model provider group. Errors from **Save** stay where they are (#71).
  - No backend or API change.

## D-027 Connect only to addresses that pass the address check — accepted (2026-11-09)

- **Decision.** `safe_fetch` checks the address again when it opens a connection, and connects only to the address it has just checked. A subclass of `httpcore.SyncBackend` resolves the host, applies the same address rule as the check before each request, and opens the connection to each checked answer in turn. `safe_fetch` installs it in the connection pool of its `httpx` transport. The check before each request and redirect hop stays.

  Planned as the lean OpenSpec change `pin-fetch-connections` (issue #68).
- **Why.**
  - `httpx` resolved the host a second time when it connected, and nothing checked that answer. A host whose DNS answer changes after the check (DNS rebinding) could therefore reach the user's machine or local network.
  - The first design accepted this as a residual risk (2026-10-03). Since D-020, each run follows up to 8 links from every new item, so any followed author can trigger these requests, and the answer is sent to the model provider.
  - A system review on 2026-11-01 confirmed the gap with a probe. The user chose #68 as the next issue on 2026-11-09.
- **Alternatives:**
  - **Pin the connection to the answers of the first check.** This saves one DNS lookup, but `safe_fetch` would have to pass per-host state to the pool. Rejected: more state, and no security gain over checking at connect time.
  - **Rewrite the URL to the IP and set the host name by hand.** Rejected: the stored response URL would show the IP, IPv6 literals need brackets, and every `respx` route in the tests would change.
  - **Patch `socket.getaddrinfo` during a request.** Rejected: it is global for the process, and fetches run in several threads.
- **Consequences:**
  - One more DNS lookup for each new connection.
  - The wiring uses a private attribute of `httpx` 0.28 (`HTTPTransport._pool._network_backend`). A test fails if connections stop going through the backend, and `uv.lock` pins the checked versions. On the user's decision at review (2026-11-12), `safe_fetch` also fails closed at runtime: if the pool has no network backend to replace, it raises instead of connecting without the check.
  - The existing `respx` tests intercept before the network backend, so new tests patch `socket.create_connection` instead.

## D-028 Python 3.12 minimum, a separate Compose file for source builds, and release v0.2.0 — accepted (2026-11-13)

- **Decision.**
  - The minimum Python is 3.12, the version CI and the image use, in `requires-python` and in the README.
  - `compose.yaml` keeps only the published image. A new `compose.build.yaml` builds from source under the local name `catchup:local`, and the README turns it on with `COMPOSE_FILE=compose.yaml:compose.build.yaml` in `.env`.
  - The README builds the frontend before starting the backend.
  - The README gets backup and restore blocks that each work on their own, including a restore on a new machine.
  - Version 0.2.0. After the merge, and with the user's confirmation, Claude Code tags `v0.2.0`, so the release workflow makes `latest` current.

  Planned as the lean OpenSpec change `fix-install-guide` (issue #13).
- **Why.**
  - A clean-install test by a fresh agent that followed only the README (2026-11-13) found three problems:
    - `uv run pytest` cannot collect tests on Python 3.11, the stated minimum;
    - `docker compose up -d` starts v0.1.0, 456 commits behind `main`, and a source build was tagged locally as the published `latest`;
    - the restore commands failed on their own.
  - The user chose Claude's recommendation on each point (2026-11-13).
- **Alternatives:**
  - **Keep Python 3.11.** This means rewriting one test line and adding a 3.11 CI job. Rejected: CI would be slower, the image never runs 3.11, and uv fetches 3.12 automatically.
  - **Default to the `edge` image.** Rejected: a release makes `latest` current, and `latest` stays the stable choice.
  - **Serve a frontend that is built after startup.** This needs a code change. Rejected: it adds a check on every request for a development-only case. The README's order solves it.
  - **An image-name variable, or an automatically loaded `compose.override.yaml`.** Rejected (design D4): a missing variable falls back silently to the published name, and an override file would turn on source builds for everyone.
- **Consequences:**
  - Docker users who build from source add one line to `.env`. Without it, `docker compose up -d --build` silently keeps running their previous build.
  - `uv.lock` drops `tomli`, which only Python 3.11 needed.
  - The release is an outward-facing step, so the user confirms it after the merge.
- **Amended after review (2026-11-14).** A clean-install re-run and a spec review of the first implementation found that uv picks the newest allowed Python, not 3.12, and that the backup and restore commands could lose data. The user approved Claude's fixes:
  - `backend/.python-version` pins the backend to Python 3.12, the version CI tests. Rejected alternative: an upper bound in `requires-python`.
  - Secrets come from `openssl`, are written once with `set -C`, and are never empty.
  - Backups are timestamped files, written through a `.partial` file, so no backup overwrites another. Rejected alternative: one fixed path, with a rename before each restore.
  - Restores check the whole archive in the image before stopping or emptying anything: they read the gzip stream to its end and apply the extraction's own filter. Each block stops at its first error. Rejected alternative: a plain `r|gz` stream check, which a fresh-eyes probe showed passes some truncated archives.
  - The source-build override sets `pull_policy: never`. Rejected alternative: `pull_policy: build`, which rebuilds on every command.
- **Amended after the review of fix round 1 (2026-11-14).** A second clean-install re-run found that a rebuild with no source changes breaks the backup on Docker's containerd image store, and that running the blocks from a subdirectory of the checkout switches a source build to the published image. The user approved a second and last Droid round:
  - The backup and restore blocks are re-derived from five invariants instead of being patched again. Each block runs only where `compose.yaml` and `.env` are in the current directory, uses the image name Compose used (`{{.Config.Image}}`), and finishes every check before it stops or changes anything. Rejected alternative: `docker compose up -d --force-recreate` inside each block, which restarts CatchUp an extra time only to make the container's image ID valid again.
  - Existing source-build users upgrade in this order: back up, `git pull`, add the `COMPOSE_FILE` line, build. Adding the line before `git pull` makes every Compose command fail.

## D-029 Keep focus and announcements when pages change in place, and show Save results at Save — accepted (2026-11-15)

- **Decision.**
  - **Settings Save results.** Settings shows every Save result in the save bar, next to Save. Errors without a field are shown there as an alert. A field error marks its field, and the save bar names the field. A missing model marks the Model select.
  - **Busy controls.** While a run is in progress, Generate / Try again use `aria-disabled` instead of `disabled`. So do the popup's buttons while they work.
  - **Focus targets.** When an action removes the focused control, focus moves to a named target.
  - **Status regions.** Result messages use status regions that stay on the page.

  Planned as the lean OpenSpec change `fix-focus-and-result-messages` (issues #71 and #72).
- **Why.**
  - A system review on 2026-11-01 found that Save errors without a field appear at the bottom of Settings, below two other groups (#71).
  - It also found that focus falls to the page in several places, and that some status messages are created together with their region, so screen readers may miss them (#72).
  - Claude checked both against `main` at `2f456cd` on 2026-11-15.
- **Alternatives:**
  - **Keep `disabled`, and put focus back after the run.** Rejected: focus is lost for the whole run, and nothing tells a screen-reader user why the button does not work.
  - **Show every Save error only in the save bar.** Rejected: field errors must stay linked to their inputs (user-interface, "Keyboard and screen-reader support").
  - **Move focus to the first invalid field after Save.** Rejected for now: the Model select is disabled until a test, so it cannot take focus, and Test connection does not move focus either.
  - **One shared live region for the whole app.** Rejected: messages belong next to the control that produced them, and Settings already keeps one region per group.
- **Consequences:**
  - A busy button must ignore clicks itself, so each handler checks the flag.
  - Empty status regions need a CSS rule so that they take no space in grid and flex layouts.

## D-030 An unreadable robots.txt refuses its site for the run, and a run summarizes only items recorded before its linked-page pass — accepted (2026-11-16)

- **Decision.**
  - **robots.txt.** When a site's robots.txt cannot be read because of a server error (HTTP 5xx), a network error, or another failure without a 4xx answer, the linked-page pass fetches no page from that site for the rest of the run. 401 and 403 still refuse the site. Other 4xx answers, including 404 and 429, still mean "no robots.txt", and every page is allowed.
  - **Late items.** A run records the highest item id just before its linked-page pass. It summarizes, and lists under Creator updates, only pending items up to that id. Items recorded later, such as a page saved with the extension or the entries of a source confirmed during the pass, wait for the next run, which also gathers their context.

  Planned as the lean OpenSpec change `fix-robots-errors-and-late-items` (issues #76 and #70).
- **Why.**
  - A system review on 2026-11-01 found that an unreachable robots.txt allowed every path (#76). RFC 9309, section 2.3.1.4, requires complete disallow in that case. The user decided on 2026-11-01 to follow the RFC.
  - The same review found that an item recorded during the pass was delivered in that run without its context, and was never gathered again (#70). Claude reproduced it with a probe on `main` at `3b3713e` on 2026-11-16.
- **Alternatives:**
  - **Disallow only for 5xx and network errors, and keep "allow" for redirect and size failures.** Rejected: telling them apart needs the user-facing error messages, and the RFC permits disallow for those cases.
  - **Retry robots.txt once before disallowing.** Rejected: a 503 with a short `Retry-After` is already retried once, and the next run reads robots.txt again.
  - **Summarize only items whose context was gathered.** Rejected: items that the per-run fetch limit left unreached must still be summarized in that run.
  - **Refuse saves and source confirms while a run is active.** Rejected: the pass can take minutes (#64).
  - **`AUTOINCREMENT` on item ids, so a deleted id is never reused.** Rejected for now: it needs a table rebuild migration for a rare case (design, Risks).
- **Consequences:**
  - When a site's robots.txt fails for a moment, that run's items from it are summarized without its linked pages.
  - A run whose only pending items arrived during its pass ends with "no new content". The items appear in the next run.

## D-031 Check robots.txt for every request of a context fetch, compare origins after normalizing, and signal the fetch budget one way — accepted (2026-11-16)

- **Decision.**
  - **Redirects.** Every request of a context fetch, including each redirect target, is checked against the robots.txt of its own origin before it is sent. A refused target is not requested, and the fetch counts as refused. `safe_fetch` takes an optional per-request check for this; only the linked-page pass uses it.
  - **Origins.** robots.txt is cached per origin after lowercasing the host and dropping the scheme's default port, so `https://SITE.example`, `https://site.example:443`, and `https://site.example` share one read. Scheme and non-default ports stay separate.
  - **Budget.** Running out of the per-run fetch budget raises one `BudgetExhausted` error, a `FetchError` with today's code and message. The linked-page pass catches it once per item, and drops its sentinel, its translations, and two flags that no longer change the outcome.
  - **Comments.** `author_replies` fetches the comment feed through a function, called only when the page has no comment markup, and uses a set for comment-node lookups. It catches `lxml.etree.ParserError`, for the page and for each feed entry; the `html.ParserError` it named does not exist.

  Planned as the lean OpenSpec change `refactor-context-fetch-budget-and-robots` (issue #90, and parts 1 and 2 of #60).
- **Why.**
  - The review of `fix-robots-errors-and-late-items` found on 2026-11-16 that redirects into a refused origin were still fetched, and that the cache key depended on how the URL was written (#90). The spec was narrowed to what the code did, and the fix was left for this change.
  - The fix changes the same code that #60 asked to clean up: three budget signals translated back and forth, two vestigial flags, and a duplicated comment-markup parse. Doing both at once touches `gather.fetch` and `safe_fetch` once.
  - Planning probes found that an empty post page makes `author_replies` raise `AttributeError` instead of falling back to the comment feed, and that one unparseable feed entry loses all of an item's replies.
- **Alternatives:**
  - **Follow redirects in the linked-page pass instead of in `safe_fetch`.** Rejected: it repeats the redirect limit, address checks, and retry that `safe_fetch` owns.
  - **Check robots.txt for the final URL only.** Rejected: the target would already be requested.
  - **Key the cache by host alone.** Rejected: HTTP, HTTPS, and other ports can serve different robots.txt files (RFC 9309, section 2.3).
  - **Keep the `EXHAUSTED` sentinel, and only delete the flags.** Rejected: the sentinel is what forces the translations.
  - **Fix #90 alone, and leave #60 for later.** Rejected: the same lines would be patched twice (D-023).
- **Consequences:**
  - A redirect to a new site costs one robots.txt request from the per-run budget.
  - "Linked pages read" now also counts a request that failed or was refused on the last budget unit, and, once the budget is used up, links of the same item that need no request (refused by cached rules, or blocked before any request).
  - When a post page cannot be parsed, the comment feed is tried.

## D-032 A source check reads past items as keys and links, and loads full rows only for episodes it may update — accepted (2026-11-17)

- **Decision.**
  - **Source checks.** `check_source` reads only `identity_key` and `link` for the source's past items. For podcast sources it also loads, as full rows, the pending episodes whose transcript is still `to_fetch`, `waiting`, or empty, because only those can be updated by the check.
  - **Pins.** A new test covers a website source upgraded to a podcast, whose pending item has no transcript status yet. Three rules that no test protected get one test each: the caption pass clears an earlier summary, a new summary resets the `used` flags of context rows, and a waiting episode that turns into a text post drops its earlier summary.
  - **Frontend tests.** `watchPollTimer()` returns `advancePoll(ms)`, which waits for the poll timer and advances fake time; the 19 poll steps in `Home.test.tsx` use it.

  Planned as the lean OpenSpec change `finish-fix-round-cleanup` (the rest of issue #60).
- **Why.**
  - A delivered transcript can be about 170,000 characters, and every source check loaded all of the source's past items in full, only to build key and link sets (#60, comment of 2026-11-01).
  - On `main` at `6ee13dd`, removing any of the three rules passed the full backend suite (Claude's probe, 2026-11-16).
  - #60 part 3 asked for one poll helper.
- **Alternatives:**
  - **`load_only` or `defer` on the full query.** Rejected: partial objects still enter the session, and the update branch would load the deferred columns lazily, one row at a time.
  - **Keep full rows for podcast sources only.** Rejected: delivered episodes have the longest texts.
  - **A helper that also starts the poll watch.** Rejected: the spy must be set before `render`, and the wait happens later.
- **Consequences:**
  - A source check's memory no longer grows with the text of the source's history.
  - Nothing a user sees changes.

## D-033 Show only the preview of the address in the field, and never show images on local addresses — accepted (2026-11-17)

- **Decision.**
  - **Sources page.** While a preview loads, Preview and "Save and preview" stay focusable but are announced as unavailable and do nothing, and the status region says "Loading the preview…". A request counter drops every answer that arrives after the address field changed, so Confirm saves only a preview of the address the field shows.
  - **Popup.** "Follow this site" and "Follow this account" get the same busy state and progress message. A preview that answers after the popup's content changed, for example after the page was saved, is ignored.
  - **Image addresses.** One public-address rule serves CatchUp's own fetches and image addresses. An image is not kept when its host is a non-public IP address, a numeric form that a browser reads as an IPv4 address (unless it is a public address in plain dotted form), `localhost` or a name under it, a name without a dot, a name under `localdomain`, `local`, `internal`, `intranet`, `private`, `corp`, `home`, `home.arpa`, or `lan`, or anything other than a plain ASCII name. An address with a backslash is not kept either, because browsers read it as `/` and may request another host than Python's parser reports. Names are not looked up.
  - **Stored images.** Saved digests return only images that pass the same check, so digests saved before the rule are covered without rewriting rows.

  Planned as the lean OpenSpec change `fix-source-preview-and-image-hosts` (issue #73, and the security comment on #65).
- **Why.**
  - A probe in the system review of 2026-11-01 showed a slower answer for an earlier address replacing a newer preview, and Confirm saving it (#73).
  - `filter_image_urls` kept any `http` or `https` image with a host, so a digest could make the reader's browser request `http://192.168.1.1/…` or `http://localhost:631/…` (#65, comment of 2026-11-02). The reader's browser parses hosts with the WHATWG rules, which read forms such as `2130706433` and `0x7f.1` as IPv4 addresses.
- **Alternatives:**
  - **Compare each answer's address with the field.** Rejected: an address changed and typed back would accept a dropped answer, and the server may normalize the address.
  - **Abort the request.** Rejected for now: the API client takes no signal, and aborting does not stop the server's work.
  - **Normalize hosts as a browser does, then check them.** Rejected: more code that must match browsers exactly, for hosts real feeds do not use.
  - **Resolve image hosts during collection.** Rejected: the reader's browser may resolve them differently and later, and lookups would add traffic to every check.
  - **Serve images through CatchUp.** Rejected for this change: it changes the privacy model and needs a new endpoint. It is the only way to catch public names that resolve to local addresses.
  - **Rewrite stored rows with a migration.** Rejected: the read-time filter covers them without changing data.
- **Consequences:**
  - A public-looking name that resolves to a local address is still shown. The README says so.
  - A few public images are dropped: non-punycode IDN hosts, public IPv4 addresses in numeric shorthand, and single-label names.
  - An item collected before the update can show fewer images than its summary chose.

## D-034 One page extractor that reads only what the page shows, and takes Readability's strict first attempt — accepted (2026-11-20)

- **Decision.**
  - **One extractor.** The browser extension reads an ordinary page with one injected function, `extractPage()`, instead of `readable.ts` and `generic.ts`.
  - **Only what the page shows.** It works on a copy of the page without the elements the browser does not show. An element is left out when its computed `display` is `none`, which includes `hidden` and stylesheet rules. For computed `visibility: hidden` or `collapse`, the element's own text is left out. The live page is never changed.
  - **Main text.** The main text comes from Readability's first, strict attempt (`charThreshold: 1`), with its link-density limit raised (`linkDensityModifier: 0.3`, from 0.2 to 0.5 for low-weight blocks). Readability's longest attempt is never used. Without a usable Readability result, the page's `article`, `main`, `[role="main"]`, or `body` is read.
  - **Title link.** A link outside navigation, headers, footers, asides, and forms, whose text is the page's title (also without a leading "Label:" or a trailing site name), and which points to another page, is saved first. Each link address is saved once.
  - **Date.** The date falls back to `time[datetime]` in the main text, then in the page's `article` or `main`.
  - **Popup.** It keeps one chain. An X post page uses `extractX`. Every other page, and an X page that does not match, gets `readability.js` and then `extractPage`.

  Planned as the lean OpenSpec change `merge-extension-page-extractors` (issue #62).
- **Why.**
  - On short pages, Readability returns its longest attempt when none reaches 500 characters, and that attempt can be a sponsor banner or a sidebar. Probes on simonwillison.net's page layout with shortened bodies saved only the "Sponsored by" banner, or the sidebar's tags and "Sponsor me" promo, instead of the post (#62).
  - Readability's chosen block on a real release note leaves out the title row, so the link to the release was lost.
  - `generic.ts` read hidden menus. Readability itself checks only inline styles and the `hidden` and `aria-hidden` attributes.
  - The two files' 39 shared lines had drifted. For example, real blog.python.org posts were saved without the date that their `<time datetime>` shows.
- **Alternatives:**
  - **Keep the second, looser parse and tune its thresholds.** Rejected: two fix rounds did this, and the cause remained.
  - **The strict attempt without the link-density modifier,** as probed in #62. Rejected: a short link post kept only its date line, and a release note without a body kept only its date line.
  - **The page's main region without Readability.** Rejected: pages without `article` or `main`, such as simonwillison.net, would save the banner, the sidebar, and the footer.
  - **`checkVisibility()`.** Rejected: jsdom does not have it, so the tests could not run the real path.
  - **A title-link rule by containment or length ratio.** Rejected:
    - containment matched the label link `Release` before the title link;
    - a ratio fails for short release names.
  - **Mapping Readability's chosen block back to the page and adding its sibling rows.** Rejected: it depends on Readability's internal choice and needs more code.
- **Consequences:**
  - On the 11 real pages checked, the saved text is unchanged.
  - The release link is now saved, Python posts get their date, and duplicate links are merged.
  - What is hidden can depend on the window width, through media queries.
  - When `readability.js` cannot run, the fallback can still include a sponsor block on pages without `article` or `main`.
  - A block whose link density passes the raised limit is still dropped.
  - **After review (2026-11-20):**
    - a hidden link with element children loses its address, and a page without a title gets no title link;
    - the short-page rule covers a longer block that is an `aside` or that the page marks as a sponsor block, banner, or sidebar by its class or id. README keeps a narrower known limit for sponsor blocks the page does not mark;
    - a page whose body is hidden is reported as unreadable.

## D-035 Stop for the user only at plan approval and merge approval — accepted (2026-11-19)

- **Decision.**
  - After the user approves a plan, Claude Code runs Droid, reviews every run, and starts fix rounds for confirmed (a) and (b) items inside the approved plan and within D-023's limits, without asking each time. It still stops for anything that changes scope, spec, or design, for a Droid login failure, and when D-023's limits are reached.
  - Claude's own fixes stay within D-023: test or doc fixes of about 30 lines in total go into its review commit before the merge-ready report. Larger ones, and any behaviour change Claude would make itself, however small, are decision points in that report.
  - The merge-ready report lists, as numbered steps, exactly what merge approval will do: apply the decisions the reply settles, archive on the branch, push, and open a PR with `Closes #N` (`Part of #N` for an issue that stays open). Auto-merge, and a comment on an issue that stays open, happen only when the user's own words ask for them. After the merge, Claude confirms it with `gh pr view`, moves the board item, removes this change's worktrees, branches, and images by their exact names, and lists the next board items. Port 8800 is still rebuilt only when the user asks.
  - The steps are written in the new "Shipping" section of `AGENTS.md`. The user's personal Claude Code skills `/reppit-apply` and `/ship` read it.
- **Why.**
  - A review of the user's Claude Code sessions from 2026-10-05 to 2026-11-17 found the same go-aheads in almost every change: "commit the plan, then start Droid" (17 times), "as you suggest, one more (small) round" (12), "approve auto-merge, and delete the remote branch after the merge" (8), "check whether it is merged, then wrap up" (7), and "is it merged yet?" (4, three of them on one day). The user almost never said no.
  - Each one cost a round trip, and the cleanup after a merge had to be described again every time.
- **Alternatives:**
  - **Keep asking at every step.** Rejected: the answer was nearly always the same.
  - **Merge without asking.** Rejected: the user approves each PR.
  - **Put the steps only in the skills.** Rejected: the board IDs, the Docker rules, and port 8800 belong to this project, and Droid and other sessions read `AGENTS.md`.
- **Consequences:**
  - Fix rounds within D-023's limits no longer produce a question; the user sees them in the merge-ready report.
  - The user still approves every plan and every merge, and decides every rebuild of port 8800.

## D-036 Read linked pages for up to 4 items at once, and count only what the run can still read — accepted (2026-11-20)

- **Decision.**
  - **Stage durations.** Each run stores how many seconds its source checks, caption pass, context pass, summaries, and grouping took, saved as each stage ends. The run API returns them. The screen does not show them.
  - **Sources total.** A run stores the number of sources it will check when it starts. The run bar shows the linked-page line from the start of the context pass, even when a source was deleted during the checks.
  - **Linked-page total.** The total is the pages read so far, plus those the run can still read within the remaining per-run limit. It counts one robots.txt request for each site not asked yet, and nothing for a page a known robots.txt refuses. Pages the limit, the 16,000-character cap, or a deleted item rules out leave the total, so the pass ends with the number read equal to the total.
  - **Several items at once.** The context pass gathers context for up to 4 items at the same time, each in its own thread and session, with the items started in plan order. Within an item, the order and the caps are unchanged. Host spacing keeps a lock per host. The budget unit is taken under a lock. robots.txt is read under a lock per origin.
  - **Held items.** When a source's check finds no new entries, but the source has pending items that are ready for the run, the check shows "New items" as soon as it is saved.

  Planned as the lean OpenSpec change `improve-context-pass-speed-and-progress` (issue #64). It was first numbered D-035, which the Shipping section took in PR #96.
- **Why.**
  - A run over 50 items took about 4 min 20 s. The bar read "Linked pages read: 6 of 178", and the run read 39 pages (#64).
  - The total counted every candidate link. robots.txt requests take units from the same limit of 60, and links that the limit or the cap stops were never counted as read.
  - Pages were read one at a time, and `HostSpacer` held one lock for every host while it slept.
  - `sources_total` was counted live, so a source added during a run hid the linked-page line (comment of 2026-11-02 on #64).
- **Alternatives:**
  - **Log stage durations.** Rejected: the app's own INFO log lines reach no handler, and a stored run can be compared later.
  - **Total as `done + min(units left, reads left)`.** Rejected: robots.txt requests use about a third of the limit, so that total would fall from 60 to 39 during a run like the one in #64.
  - **Count robots.txt requests as linked pages, or show them on a second line.** Rejected: robots.txt is not a linked page, and users do not need a second number.
  - **Read one item's links in parallel, or use one flat queue of URLs.** Rejected: the 16,000-character cap and the body order need the earlier pages' text, and parallel reads would spend units on pages the cap drops.
  - **Async I/O.** Rejected: the connect-time address check is built on httpx's sync backend.
  - **Write to the database only on the runner thread.** Rejected: progress must be committed before the next request, and SQLite in WAL mode already serves several writer threads.
  - **A setting for the number of items or the depth.** Deferred to #54.
- **Consequences:**
  - Up to 3 items that start while the limit is nearly used up can end as `none` instead of staying unread. This matters only when the run then fails before its save, because a successful run delivers every pending item.
  - When the limit runs out, which items got context depends on how fast pages answer.
  - Two requests to one host can be open at the same time when the first takes longer than 1 second. Requests still start at least 1 second apart.
  - The total can move by a few pages after a redirect, or while several reads are in progress. It equals the number read when the pass ends.

## D-037 Add Anthropic as a second model provider, through the official SDK — accepted (2026-11-22)

- **Decision.**
  - **Provider choice.** The model configuration gets a provider, `openai_compatible` (the default, and every existing configuration) or `anthropic`, stored in a new `model_config.provider` column (migration `0009_model_provider`). One configuration stays active at a time. Changing the provider, like changing the base URL, needs the API key again, and clears the recorded context window.
  - **Second client.** A new `AnthropicModelClient` calls Anthropic's Messages API through the official `anthropic` Python SDK, pinned `>=1.13,<2`, behind the existing client surface (`list_models`, `chat_json`, `usage_totals`, `close`). A provider factory picks the client. The OpenAI-compatible client, the prompts, and the summary and grouping stages do not change.
  - **Requests.** The prompts' system text goes to `system`. No sampling parameters or prefill are sent. Every call allows at least 16,000 output tokens and streams its answer.
  - **JSON.** Answers are parsed as a JSON object, or a JSON object in one fenced block, and retried as today when they are not.
  - **Errors.** 529 and stream errors that report overload or an internal error are temporary. A spend-limit 429 counts as insufficient balance. A refusal is not retried.
  - **Fallback models.** For `claude-fable-5-2`, `claude-fable-5-1`, `claude-opus-5-5`, `claude-opus-5`, and `claude-sonnet-5-5`, every call asks for Anthropic's server-side fallback model.
  - **Model list.** It comes from Anthropic, without retired models, with `claude-opus-5-5` first when listed.
  - **Settings** gets a Provider select. Choosing a provider fills in its default address.

  Planned as the lean OpenSpec change `add-anthropic-provider` (issue #12). The JSON method, the fallback models, the default model, the SDK version, and one configuration rather than one per provider were the user's choices at plan approval (design U1–U6); the user chose the recommendation for each.
- **Why.**
  - D-004 planned an Anthropic-native adapter behind the same interface (#12).
  - The `claude-api` reference that Claude Code uses says to call Claude through the official SDK, not through OpenAI-compatible shims. It also says to stream long requests, and to opt into server-side fallbacks by default for the listed models.
  - Thinking cannot be turned off on `claude-opus-5-5`, and it counts toward `max_tokens`, so the 4,096-token summary limit could leave answers empty.
  - Keeping the client surface lets the stages and their 15 test fakes stay as they are.
- **Alternatives:**
  - **Raw HTTP through `httpx2`.** Rejected unless the user prefers no new package: it would re-implement streaming and typed errors.
  - **LiteLLM, or Anthropic's OpenAI-compatible endpoint.** Rejected: a large dependency, and the reference rules out shims.
  - **Structured outputs (`output_config.format`).** Offered as the user's alternative. A shared all-optional schema would have to follow every key the prompts ask for (including #65's planned image changes). Models without support would fail every call. The schema cannot be checked against the real API before review.
  - **Infer the provider from the base URL.** Rejected: proxy addresses would be misread.
  - **One saved key per provider.** Offered as the user's alternative. It needs a new table and more Settings states.
  - **A shared base class for both clients.** Rejected: it would change the tested OpenAI client, whose retry rules differ.
- **Consequences:**
  - A new dependency, `anthropic`, with `docstring-parser`, is added to the lockfile before implementation. Docker builds download them.
  - The default model `claude-opus-5-5` always thinks, at effort `medium`. A per-provider setting is #4. The client keeps all request options in one place, and the model list reports each model's effort and thinking support.
  - A refused request rescued by a fallback model is billed at that model's rates.
  - Downgrading the database turns Anthropic configurations into OpenAI-compatible ones, which then need a new test.
  - If #40 also adds migration `0009`, the second change to merge renumbers its migration.

## D-038 Follow Bilibili uploaders through an RSSHub the user runs, and never request Bilibili from CatchUp — accepted (2026-11-22)

- **Decision.**
  - **A new source kind, "Bilibili uploader".** A pasted `space.bilibili.com/<mid>` address, or the configured RSSHub's `/bilibili/user/video/<mid>` address, is recognized before discovery. It is read through RSSHub's JSON Feed and saved as `bilibili:uploader:<mid>`.
  - **The RSSHub address is the environment setting `CATCHUP_RSSHUB_URL`.** Its origin is the only one whose requests may reach a private or loopback address, and only on the first hop of an uploader request.
  - **CatchUp never requests `bilibili.com`, `b23.tv`, `hdslb.com` or `bilivideo.com`,** with subdomains, for any source, before DNS.
  - **Videos are summarized only from the subtitles RSSHub attaches** as `data:` URLs, which are decoded locally. Without subtitles, a video waits the caption wait (24 hours), and then goes to Creator updates as "no subtitles from RSSHub". Bilibili videos get no linked pages and no image candidates.
  - **An optional `compose.rsshub.yaml`** runs `diygod/rsshub:latest` next to CatchUp. `compose.yaml` does not change.

  Planned as the OpenSpec change `add-bilibili-sources` (issue #40). The user chose Proposal 1 on 2026-11-22.
- **Why.**
  - Bilibili publishes no feeds and no API for following other people's uploads. The Open Platform covers only accounts linked to the developer (developer service agreement, sections 1.1 and 4.2, updated 2025-05-28).
  - D-013 allows video summaries only from transcripts or subtitles. Subtitles come back only to a logged-in session, according to yt-dlp's and RSSHub's code.
  - Bilibili's user agreement (updated 2025-04-30, effective 2025-05-07) forbids getting the platform's content or data "by any means (including … any automated program, script or software) and for any reason" without Bilibili's prior written permission (section 5.6(3), translated from Chinese). Section 1.2 limits the services to non-commercial use. It has no personal or research exception, and says nothing about keeping derived summaries or deleting data after use.
  - In January 2026 a law firm acting for Bilibili made the main public documentation of these web APIs shut down. The letter named the APIs' access-control and security-authentication mechanisms.
  - Through RSSHub, CatchUp's code and network traffic contain no Bilibili signing, cookies or anti-bot steps, and RSSHub's maintainers keep up with Bilibili's changes.
- **Alternatives:**
  - **A native kind that calls Bilibili's web API (Proposal 2).** Rejected: CatchUp would make the requests that section 5.6(3) forbids, the public repository would carry WBI signing and visitor-cookie code, and subtitles would need the user's session cookie stored in CatchUp, against `docs/handoff.md` §4.
  - **Close #40 with a README note about RSSHub.** Not chosen by the user.
  - **A Settings field for the RSSHub address.** Rejected: any user of the web interface could then point CatchUp at a private address.
  - **Summaries from video descriptions.** Rejected by D-013.
  - **Speech-to-text of the audio.** Not committed by D-013, and it would mean downloading audio.
- **Consequences:**
  - The terms risk stays with the user's RSSHub, which makes the automated requests. The README and the Sources preview say so.
  - Subtitles need the user's own logged-in Bilibili cookie in RSSHub's settings (`.env.rsshub`), which CatchUp never sees. Without it, every video goes to Creator updates.
  - A website feed whose entries link to Bilibili pages no longer reads those pages.
  - No migration: `sources.kind` is free text.

## D-039 Draw the CatchUp mark on a 16 × 16 grid so the tab icon stays sharp — accepted (2026-11-22)

- **Decision (option A; B and C were the alternatives).**
  - **A. One mark on a 16 × 16 grid.** At 16 px the dark square runs from 2 px to 14 px, and the two bars are rows 6 and 9, from 5 px to 11 px across. The SVG and the 192, 512, and 1024 px PNGs follow the same grid, and the maskable icon keeps its box. `make-icons.py` stays the only source. The offline page's inline copy is updated.
  - No new icon files or declarations. Chrome keeps taking the SVG for the tab, and the extension's build copies the new 192 px PNG.

  Planned as the lean OpenSpec change `improve-small-icon-legibility` (issue #43, part 2).
- **Why.**
  - The bars are 38/1024 high, about 0.6 px at 16 px, and the square's edges fall between pixels. Rendered at 16 px in headless Chrome 157, the icon mixes 12 colors, and the bars show as gray lines (#43, found in the review of #37).
  - Drawn on the grid, the 16 px render has exactly the two mark colors. 192 px is 12 × 16 px, so the extension's toolbar icon file averages cleanly to 16 px; whether the toolbar's own scaling keeps it sharp was not checked.
- **Alternatives:**
  - **B. Redraw only the tab SVG.** Possible: the app icons stay unchanged, but the extension's toolbar icon stays blurred, and the tab icon and the app icon differ slightly.
  - **C. A bolder small mark** (2 px bars at 16 px, 1 px margin). Possible: easiest to read, but heavier than the C7 prototype's thin rules, with a thin light edge on dark tabs.
  - **Add a 32 px PNG with `sizes="32x32"` next to the SVG.** Rejected: Chromium scores an icon without `sizes` as high as an ideal size, sorts candidates stably, and stops once nothing scores higher (`components/favicon/core/favicon_handler.cc`), so the tab would keep the SVG.
  - **Replace the SVG with 16 px and 32 px PNGs or a `favicon.ico`.** Rejected: more files, and no gain over a grid-drawn SVG.
  - **Rename the icon so stored tab icons refresh at once.** Rejected: Chrome refreshes a page's stored icon on any reload (`components/favicon/content/content_favicon_driver.cc`).
- **Consequences:**
  - Under A, the installed app and the Safari touch icon get slightly thicker bars and a larger square once the browser updates them.
  - Chrome may show the old tab icon until CatchUp is reloaded once.
  - The maskable icon's corners stay slightly outside the 40% safe circle, as before.

## D-040 Show each digest image's text as a visible caption, and keep formula and small images out of the candidates — accepted (2026-11-22)

- **Decision.**
  - **Captions.** Each chosen image shows its text as a caption under it, in the digest's language. The image itself has an empty `alt`, so assistive technology reads the text once, as the figure's caption. An image without text is not shown. A failed image is hidden with its caption. Digests saved earlier show their stored text as the caption.
  - **Candidates.** An image is not kept when its address is a rendered formula (`latex.php`, `latex.codecogs.com`, or a QuickLaTeX cache file), or when the entry states its width or height as under 100 px. An image with no stated size is kept. This replaces the 1×1 rule. Candidates stored earlier are filtered again before the summary call, and saved digests do not show formula images.
  - **Prompt.** The summary call chooses an image only when a reader who has not read the item can understand it from the image and its caption, usually one, and at most 3. The caption says what the image shows and why it matters.

  Planned as the lean OpenSpec change `improve-digest-image-captions` (issue #65, the part left after D-033).
- **Why.** In the user's live check of #41 (2026-11-01), Simon Willison's benchmark drawings showed with no visible explanation, because the text the summary wrote was only the `alt` attribute, and Terence Tao's posts offered formula images such as `{T}` from `s0.wp.com/latex.php` as candidates (#65).
- **Alternatives:**
  - **A hard limit of one image, or a setting for the number.** Offered to the user as options (design D1); the user chose the recommendation. The setting needs a migration and edits the Settings page.
  - **Two texts per image, a short `alt` and a caption.** Rejected: more output, a new stored field, and mostly the same words.
  - **Keep `alt` and hide the caption from assistive technology.** Rejected: visible text that screen reader users cannot reach.
  - **Measure images that state no size.** Rejected: candidates must not fetch images.
  - **Match `latex` anywhere, or the `class="latex"` attribute.** Rejected: drops unrelated images, and X posts, captures, and stored candidates have no class.
  - **Rewrite stored candidates with a migration.** Rejected: filtering when they are read covers them, as in D-033.
- **Consequences:**
  - Captions in digests saved earlier describe the image but may not say why it matters.
  - `Image from <source>` is shown as a caption when neither the model nor the page gave a text.
  - Sizes written with units or in `style`, and pages saved from the browser, which send no sizes, get only the address rules.
  - A summary reused from an earlier run keeps its earlier choice; its formula images are hidden when the digest is served.

## D-041 Let the user lower or turn off the model's reasoning, per provider — accepted (2026-11-25)

- **Decision** (the user chose option A for U1–U3 of the design at plan approval).
  - **Setting.** The saved model configuration gets a Reasoning choice, stored in a new `model_config.reasoning` column (migration `0011_model_reasoning`, planned as `0010_model_reasoning` and renumbered at the merge because #54's `0010_link_depth` merged first): Provider default (every existing configuration), Low, or Off. Off is offered for OpenAI-compatible providers only. Changing the provider resets it to Provider default.
  - **Requests.** Provider default sends nothing, as today. For OpenAI-compatible providers, Low sends `reasoning_effort: "low"` and Off sends `reasoning_effort: "none"`; for Anthropic, Low sends `output_config.effort: "low"`, also with the fallback models. No call sends `thinking`, and the output limits do not change.
  - **Refusals.** When Reasoning is not Provider default and the provider answers HTTP 400 or 422, the run fails at once with a message that says to choose Provider default, and the main screen offers Check settings.
  - **Settings** gets a Reasoning select after Model, saved like a model choice.

  Planned as the lean OpenSpec change `add-reasoning-setting` (issue #4).
- **Why.** DeepSeek thinks at effort "high" by default, and `claude-opus-5-5` always thinks. CatchUp raised its output limits so that this works (design D3 of `add-core-digest-flow`, D-037), but the user cannot lower the cost and waiting time it adds to short summaries (#4).
- **Alternatives:**
  - **Also Medium and High.** Offered to the user (design U1). Medium is the default of DeepSeek (where it means High) and of `claude-opus-5-5`, and High can use up the Anthropic output limit before an answer.
  - **Off for Anthropic.** Rejected: `thinking: {"type": "disabled"}` returns HTTP 400 on `claude-opus-5-5` and the Fable models, and `claude-sonnet-5-5` needs another value.
  - **DeepSeek's `thinking` object.** Rejected: `reasoning_effort: "none"` already turns thinking off on DeepSeek, and `thinking` is a field other OpenAI-compatible servers do not know.
  - **Offer only the levels each model supports, from Anthropic's model list.** Rejected: OpenAI-compatible servers report no such data, and the page keeps only the saved model's id.
  - **Repeat a refused call without the setting.** Offered to the user (design U2): exact, but one more call per refusal and a second retry path.
  - **Store the choice with the Digest preferences, or in an environment variable.** Rejected: it depends on the provider, and the issue asks for a setting next to the model.
- **Consequences:**
  - Some models refuse a choice, for example Gemini 3 and 4 refuse Off, and Anthropic's Sonnet 4.5 and Haiku 4.5 refuse any effort. The run then fails with the Reasoning message.
  - With the setting on, a 400 for another reason also fails the run with that message.
  - Less reasoning can make summaries and topics less careful. Items already summarized are not summarized again.

## D-042 Let the user choose how many linked pages a run reads: Off, Shallow, or Normal — accepted (2026-11-25)

- **Decision** (the user chose the recommendation for U1–U3 of the design at plan approval).
  - **A "Linked pages" choice in Settings → Digest,** stored in `app_settings.link_depth` (migration `0010_link_depth`), read once when a run starts.
    - **Normal** (the default, and every instance that saved no choice) is today's behavior: up to `CATCHUP_LINKS_PER_ITEM` links per item (default 8), and author replies.
    - **Shallow** reads up to 3 links per item, or `CATCHUP_LINKS_PER_ITEM` when that is lower, and author replies.
    - **Off** sends no context request, robots.txt included. Replies saved with a page from the browser, or kept from an X thread, are still used. Other items stay not gathered, so a later run that still finds them pending reads them at its own level.
  - Every level keeps the per-run limit, the 3,000- and 16,000-character caps, robots.txt, and `CATCHUP_AUTHOR_REPLIES`. The environment settings keep their meaning: they set Normal.
  - Each option names its pages per item with the server's numbers, and a note says that each page adds run time and up to 3,000 characters to the item's summary request, and names the per-run limit.
  - No Deep level in this change: #54 stays open for it, and the PR says "Part of #54".

  Planned as the lean OpenSpec change `add-link-depth-setting` (issue #54). If #4 (D-041) is merged first, this entry stays after it; this change's migration is renumbered if #4 also takes `0010`.
- **Why.** When the user chose #48's design (2026-10-19), they asked for a later choice between deep and shallow reading (#54). Only environment settings change the numbers today, which needs a restart. D-020 and D-036 both deferred the choice to #54.
- **Alternatives:**
  - **A Deep level without a model** (twice Normal's links and per-run limit, 6,000 characters per page, 32,000 per item). Offered to the user (design U1 B): it reads more of long pages, but the #48 sample's typical entry has no related links beyond Normal's 8, and it doubles run time and context size.
  - **#48's model-picked links as Deep** (design U1 C). Rejected for this change: an extra model call per item with links, a nondeterministic selection, and new link rules for whole pages. It needs its own research.
  - **Environment settings as upper limits for every level, or removed** (design U2). Rejected: upper limits only matter with a Deep level, and removing them breaks instances that set them.
  - **Off covering linked pages only, still reading author replies** (design U3). Offered to the user; rejected as the recommendation because Off would still request post pages.
  - **Off as no context pass at all, or marking Off items as having no context.** Rejected: saved replies would be lost, or the items would never be gathered later.
  - **Numbers written into the Settings page.** Rejected: wrong when the server's settings differ.
- **Consequences:**
  - Runs at Shallow make smaller summary requests; in large runs the per-run limit, not the level, bounds the number of requests.
  - A page saved from the browser with saved replies is marked gathered at Off, so its links are not read later.
  - Token savings are not measured before the merge; the user can compare runs at Shallow and Normal on their own instance.

## D-043 Ask the grouping call for fewer, broader topics, within a limit that grows with the item count — accepted (2026-11-25)

- **Decision** (the user chose the recommendation for D1, D2, and D7 of the design at plan approval).
  - **Instructions.** The grouping call asks the model:
    - to put items about the same subject (one company, product, event, or field) in one topic, even when they come from different sources;
    - to prefer fewer, broader topics within the topic limit;
    - to give an item a topic of its own only when it fits no other topic;
    - to title each topic with the shared subject, and to write an overview of 1–2 sentences about what its items cover together, without repeating each item's summary.

    The call that combines batch topics asks the same for final topics, and is told how many items each batch topic holds.
  - **Limit.** The limit for `n` items is `⌈√(2n)⌉`, at most `n` and 12: 1 item, 1 topic; 7 items, 4; 30 items, 8; 61 or more, 12. A batch call uses its own items' limit, and the combining call the limit for all the items.
  - **Guidance only.** A grouping with more topics than the limit is saved as the model answered. Nothing is dropped, moved, or merged, and no extra call is made.

  Planned as the lean OpenSpec change `improve-topic-grouping` (issue #32). It was planned in parallel with D-041 (#4) and D-042 (#54). If those merge first, their entries go before this one.
- **Why.** A real digest grouped 7 items into 6 topics (2026-10-13). The grouping instruction had said only "Group the supplied items by topic" since 2026-10-03, with no guidance on merging or topic count (#32, the second cause named in #25).
- **Alternatives:**
  - **One more combining call when the answer exceeds the limit** (design D1 B). Offered to the user. It adds a call and its wait to every run where the model ignores the limit.
  - **Fold extra topics into "Other" in code.** Rejected: unrelated items lose their titles and overviews.
  - **Treat too many topics as an invalid answer.** Rejected: after the retries, everything falls back to one "Other" topic.
  - **`⌈n/3⌉`, at least 2** (design D2). Offered to the user. Closer to the issue's "2–5 topics for up to 15 items", but it forces 4–6 unrelated items into 2 topics.
  - **Wording only, or a fixed range.** Rejected: no concrete target, or a range that is wrong for both 1 and 200 items.
  - **A Settings choice for the number of topics.** Rejected for now: it needs a migration and edits the Settings page, which #4 and #54 edit in parallel.
- **Consequences:**
  - Whether the model follows the limit is known only from the user's own runs (design D7). The tests show that the instructions and limits reach the model, and that any answer is saved as before.
  - Topics may become broad, such as one "AI" topic for model, chip, and policy news.
  - The input of the combining call stays unbounded on small context windows, as before. The item counts add about 12 characters per batch topic.
