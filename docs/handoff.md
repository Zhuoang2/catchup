# CatchUp project hand-off

Updated: 2026-10-01 (America/Los_Angeles). Purpose: hand the finished product discussion and the proposal to Claude Code to continue technical design and implementation.

This is a snapshot of the hand-off as of 2026-10-01, translated from the original Chinese on 2026-10-15. Later decisions are recorded in `AGENTS.md` and `docs/process/decision-log.md`, and they take precedence over this file.

## 1. Project status and materials

- Name decided: **CatchUp: An Open-Source, AI-Powered Personal Digest**.
- Course: Stanford CS146S, Fall 2026. Proposal author: Zhuoang Tao.
- Done: product discussion, scope narrowing, the English proposal and its language polishing, limited competitor research, the workflow figure.
- Not yet implemented: application code, data model, source adapters, model connection, tests, deployment, project repository, and project board. When this folder was checked it held only the proposal PDF; the hand-off materials have now been added, and no application has been initialized.
- The proposal's submission status is unverified; the file existing does not mean it was submitted.
- Outside this folder there are other course exercises; do not mistake them for CatchUp code.

| Material | Purpose |
| --- | --- |
| `../CLAUDE.md` | Short project entry point for Claude Code |
| `proposal.md` | Snapshot of the Google Doc's text, read at hand-off |
| `../CS146S Aut26 Final Project Proposal Zhuoang Tao.pdf` | The user's original two-page PDF; keep it, do not overwrite |
| `course-requirements.pdf` | Copy of the original course requirements |
| `../assets/catchup-workflow.png` | English workflow figure with no title or footnote, top and bottom margins cropped tight |

Google Doc: the link is kept out of the public repository; it is in the user's own Google Drive.
Syncing it again later needs the matching account permissions. This hand-off does not depend on a Google Docs connector.
The original discussion memory on this machine is in the parent folder at `../work/agent-memory.md` (relative to this project root). It contains unrelated tool records and outdated ideas, so this hand-off extracts the relevant parts instead of copying the whole file.
The user's latest explicit instructions take priority; when materials conflict, point out the difference. The sections below separate confirmed content from suggestions and do not treat undecided options as commitments.

## 2. Confirmed product positioning

For people who regularly follow several information sources: collect new content and produce a digest organized by topic, with links to the originals, to help users decide what is worth reading, watching, or listening to in depth.
Topics are not limited to AI. Students, developers, and readers of industry news can all use it.
The final plan is open source and self-deployed by the user, who configures their own model API and a supported model; the first version is aimed at users who can follow a setup guide.
First build a local / self-hosted web application used through the browser; consider a browser extension later.
When a cloud model is used, content is sent to that model service; "local deployment" does not mean "all content is processed only locally".

## 3. Core flow and scope of the first version

1. The user configures a supported model API, their own credentials, and a model. It is not fixed to one particular model; the exact compatible interface is not chosen yet.
2. Paste a source URL, detect and preview its name / address / recent content, and save it after confirmation. Duplicate or unsupported sources should be explained.
3. The user clicks Generate Digest manually.
4. Collect the new content between **the last successful request and this request**; distinguish a failed check from a successful check with no updates, and avoid including anything twice.
5. Summarize the content, organize it by topic, and keep the source names and links to the originals.
6. Save the digest for later viewing. After the core flow works, add favorites, likes, and feedback.

Sources: selected public websites / blogs, and podcasts and long videos that have accessible captions or transcripts.
Do new-article / new-episode / new-video discovery well first; do not promise that any website can be scraped.
A single article link and subscribing to its source's future updates are different operations; when a single article is detected, make the scope of what is followed clear.
"Has captions or a transcript" is the precondition for audio and video in the first version; without processing the visuals, do not claim to have summarized visual content.

## 4. Scope explicitly deferred

- Automatic scheduled scans, automatic daily pushes, real-time monitoring: not in the first version. The early "automatic daily report" discussion has been replaced by the manually triggered approach.
- Browser extension: later, for adding sources conveniently or reading pages the user authorizes.
- Logged-in / paid content: evaluate site by site later. Suggested approach: use pages in the user's already logged-in browser with their authorization to extract content; do not read the user's saved passwords, and do not upload session cookies for general-purpose login.
- Meaningful changes to existing pages: later, support selected course / event pages; not required for the first version.
- Transcribing audio and video that lack a transcript, and full external agent integration: not promised, and must not automatically grow into the MVP.
- Favorites, likes, and feedback are wanted features scheduled after the core flow; they are not removed.
- Summary quality criteria and the detailed UI will be refined once a working prototype exists; real evaluation is still needed.

## 5. Open questions to settle during implementation

These are open items and must not be written into implementation commitments as decided requirements:

- Technology stack, database, process / background-job model, installation and deployment method.
- The first supported websites, the RSS / page adaptation strategy, the podcast / video platforms, and how transcripts are obtained.
- The first model providers, interface protocol, and how a model is chosen; a model API does not mean automatically controlling a whole AI agent.
- How far back the first generation looks; how history is backfilled when a new source is first added.
- The exact definition of a successful request, re-checking and retries when some sources fail, time zones and time boundaries, and handling of missing or unreliable publication times.
- Saving a successful checkpoint per source is a suggestion, not yet formally chosen. A global success time must not hide content that a failed source did not collect.
- Large volumes of content after a long absence: batches, length, API cost, and progress indication.
- Deploying for personal use or as a shared instance, and how a demo site isolates credentials and data.
- Quality-evaluation samples and concrete criteria; interaction details for favorites / feedback.

Prefer simple approaches that fit the course timeline; there is no need to add multi-agent systems, microservices, or extensions just to look substantial.
Do not ask the user again to re-decide confirmed questions such as the project topic, whether it is open source, or whether it is manually triggered.

## 6. Course requirements (checked against the original brief)

Teams of 1–2 people complete a substantial software application that solves a real problem. The core also includes using AI across the whole development lifecycle and providing evidence of it; showing only that the product calls a model is not enough.
The original brief states that all deadlines below are Thursdays at 11:59 pm; the year comes from this course's Fall 2026 context.

| Date | Deliverable |
| --- | --- |
| 2026-10-01 | Two-page proposal |
| 2026-10-15 | Two-page Technical Spec: architecture, API, technical stack, business context |
| 2026-11-05 | Alpha, project task board / backlog, short reflection on AI tool use |
| 2026-12-10 | Final demo, code, deployed application, 4+ page report, about a 5-minute presentation |

Keep real requirement changes, prompt examples, design decisions, code reviews, testing / coverage, and AI success and failure cases. Use version control, code review, and a project board, and record team responsibilities (also needed for a one-person team).
Grading: Context Communication 18; AI Integration Evidence 10; System Design & Functionality 30; Testing & QA 15; Collaboration & Process 10; Reflection 12; Documentation/Repo/Demo 5.
The proposal guidance also asks for an AI Tool Usage Plan; the current draft covers UI/UX, code / refactoring, automated testing, review / QA, and CI/CD / deployment.
There is no requirement to create an entirely new category or to commercialize; the course text does not define "substantial" by the number of sources or features.

## 7. Competitor references and limits of verification

Similar products already exist, so do not claim "the first to combine website tracking with AI summaries".
These are design references, not requirements to copy one by one, and the scraping reliability and summary quality of these products have not all been verified.

- Readless (https://www.readless.app/): tried the public demo's concise / detailed / combined views and categories; saw topic overviews, per-item details, reading time, and source citations. Demo data only.
- Visualping (https://visualping.io/): entered a public blog, previewed the actually loaded page, and chose the "new articles" watch condition; no monitor was created and no account was registered. The idea of previewing and confirming what to watch is worth borrowing.
- Inoreader: public material covers feeds, page changes, and AI reports; the logged-in core reading flow was not tested. Help page for adding sources: https://www.inoreader.com/help/basic/feeds-sources/how-do-i-add-a-feed
- Readwise Reader (https://readwise.io/read): viewed the public introduction and the login page; history, favorites, and private-content flows were not tested.

Directions chosen: preview and confirm sources, organize by topic, keep citations of the originals. Detailed interactions can keep drawing on these during implementation; a full competitor study is not needed again before starting.

## 8. Recommended order for taking over (implementation suggestions, not yet done)

1. Read this file, the proposal, and the course brief; restate the scope briefly and list only the key open items that affect the first usable version.
2. Propose one recommended technical approach and its trade-offs, and plan milestones that can be delivered by the course deadlines; record the key decisions and open items in project files.
3. First build a small, real end-to-end flow: configure a model → add one supported source → collect new content → generate a digest with citations → save it and reopen it.
4. Add tests for source types, time boundaries, repeated requests, partial failure, and recovery; then add audio and video with transcripts, favorites, and feedback.
5. Check summary quality with real sources, verify installation in a clean environment, and prepare the deployment demo and the course's process evidence.

Recommended acceptance scenarios: no new content does not regenerate old items; failures and "no updates" are shown separately; retries neither miss nor duplicate items; history survives an application restart; summary facts can be traced back to the source; missing captions are clearly reported as unsupported.
These are acceptance suggestions still to be implemented; no code or test yet shows that they pass.

## 9. Limits of the tool migration

This hand-off migrates files, requirements, and design background. The Codex conversation context, tool connections, login state, personal skills, and API keys do not transfer just because the folder is copied.
The Claude Code login used to develop CatchUp and the API credentials CatchUp uses at runtime to call a model are two separate configurations.
On this machine, `claude --version` was verified to return 2.1.283; the Claude login and remaining quota were not verified.
There is no need to install all of Codex's skills before starting. The OpenSpec/RePPIT records in the course root folder are not CatchUp's established technical workflow.
Personal global rules stay in the user's existing `~/.codex/AGENTS.md` and are not duplicated in project files. The first prompt can ask Claude to read the original file on the same machine; when switching machines, migrate that single source yourself.
