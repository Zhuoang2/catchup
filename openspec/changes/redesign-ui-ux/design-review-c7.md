# Design review of C7 (Design plugin: design-critique + accessibility-review)

Context for this file: produced on 2026-10-06 by an independent Claude Code subagent that ran the Design plugin skills `design:design-critique` and `design:accessibility-review` against `prototypes/directions/c7.html`. It is kept verbatim as process evidence. The resolution section at the end was added by the planning session after it verified each finding.

---

# Design review: CatchUp, direction C7 · Front page grid

Reviewer: independent design reviewer (design-critique + accessibility-review skills)
Date: 2026-10-06
Prototype: http://localhost:5180/directions/c7.html (C7 = shared/base.css + directions/c.css + c3.css + c3b.css + c7.css, markup shared/render.js, data shared/data.js)
Method: DOM inspection and measurement via javascript_tool at 1440x900 (desktop) and the 420 px "narrow" app frame, light and dark; keyboard Tab testing; screenshots. Prototype chrome (dark top bar) excluded. No repository file was modified. (Measurements were done in the page only: temporary helpers in localStorage were removed afterwards, and one simulated item was injected into the DOM and removed.)

Legend: **[M]** = verified by measurement or DOM inspection. **[J]** = judgment.
Severity: critical / major / minor.

---

## Overall impression

C7 makes a strong first impression: it reads as a real broadsheet. The serif masthead, double rule, and a 3-column topic title beside a 9-column story area give a confident, calm hierarchy. Mixed Chinese and English titles sit together well. Light-theme body and heading contrast is excellent (16:1). The biggest problems:
1. The newspaper chrome takes up much of the window before any reading starts.
2. The asymmetric 6+3 item grid implies a ranking the data does not have, and it breaks with long summaries.
3. A few state-level content contradictions: the rail shows real data on the first-run and empty screens.
4. Three accessibility gaps that would block or confuse keyboard and screen-reader users: the skip link and TOC do not move focus, Chinese content has no `lang`, and run completion is not announced.

No critical blockers for the chosen direction. All issues have contained fixes.

---

## 1. Design critique

### 1a. Usability

| # | Finding | Sev | Where | Evidence | Fix |
|---|---|---|---|---|---|
| U1 | Reading starts far below the fold. Masthead (54 px wordmark, dateline, nav), page head and index strip come before the first topic. | major | digest/* · both themes · desktop and narrow | [M] Desktop 1440x900: first topic top at ~494 px inside the app (55% of the viewport). Narrow 420: header 250 px, nav wraps to 2 rows, first topic at 671 px, first item title at 844 px, so it is below the fold in an 800 px-tall window. | On digest (and ideally all screens), collapse the masthead to a single compact bar (wordmark ~1.5rem plus nav on one line). Keep the big masthead only on Generate/home, if at all. At ≤640 px, drop `.masthead-line` and put the nav in one row (icons + short labels, or a "Menu" disclosure). |
| U2 | The asymmetric item grid breaks with real content. Item 1 spans 6 columns; item 2 is forced into a 3-column (~290 px) slot. When item 2 is a long podcast summary with bullets, it becomes a very tall, narrow column that leaves a large hole under item 1 and pushes item 3 far down. | major | digest/zh · desktop (any topic with ≥2 items) | [M] Simulated by cloning the long podcast item into topic 3 as item 2: the lead item is 123 px tall, the 2nd item is 691 px tall at 290 px wide, and item 3 starts 711 px below the row top. Bullets wrap at ~15 CJK chars per line. Rules: `c7.css .items > .item + .item { grid-column: span 3 }`, `.items > .item:nth-child(n+3) { span 3 }`. | Choose the span from content length, not position (e.g. a `data-size="long"` from points/summary length gets span 9 or 6). Or stack items in a single 6–9-column reading column, and use the 3-column slot only for short items (no `points`). At minimum, `align-items: start` per row plus a masonry fallback is not enough; the long item must never get the narrow slot. |
| U3 | Smaller headlines for item 2+ imply a ranking that the model's grouping does not provide. | minor | digest/* · desktop | [M] `c7.css .items > .item + .item .item-title { font-size: 1.05em }` vs 1.25em for item 1. | Use the same title size for all items in a topic, or base the lead on an explicit signal (e.g. longest transcript summary). |
| U4 | First-run: the only visually strong button is the disabled "Generate digest". The real next step ("Open Settings") is a small secondary button inside the alert. | major | generate/first-run · both · both | [M] Hero `.btn-primary.btn-lg` disabled (grey block 187x53 at narrow); "Open Settings" is `.btn-secondary`. | In first-run, render "Open Settings" as the primary button in the hero (or hide Generate). Show Generate disabled with an `aria-describedby` reason, below the setup prompt. |
| U5 | After success there are two identical black primary buttons: hero "Generate digest" and "View digest". | major | generate/succeeded · both · both | [M] Two `.btn-primary` visible; `.result-head .btn` 156x45 next to the hero lg button. | After a run, demote the hero Generate to secondary (or hide it until the result is dismissed) so "View digest" is the single primary action. |
| U6 | Failed state: "Try again" is the primary action, but the error (rejected API key) cannot be fixed by retrying. "Check settings" is secondary. | minor | generate/failed · both · both | [M] Hero label switches to "Try again" (`render.js generate()`); "Check settings" is `.btn-secondary`. | For configuration errors (key, base URL, balance), make "Check settings" primary and "Try again" secondary. Keep "Try again" primary for transient errors (rate limit, network). |
| U7 | The "Fetch captions locally" switch label is a 588x74 px click area that spans the empty columns. Clicking blank space beside the field turns on the setting that carries a Terms-of-Service risk. | major | settings/* · desktop | [M] `.switch` box 588x74 (stretched as a grid item across columns 4–9 and two rows). | Add `.settings-section > .switch { justify-self: start; align-self: start; }` so the hit area is only the track and label. |
| U8 | The YouTube risk note sits in the far-right margin column (cols 10–12), ~550 px from the toggle it explains, and spans both toggles, so it is unclear which toggle it belongs to. The brief says this note "must stay readable, not hidden". As a margin note it reads as optional aside text. | major | settings/* · desktop | [M] `.risk` at x=1030 vs switch x=426. `c7.css .settings-section > .risk { grid-column: 10 / -1; grid-row: 1 / span 2 }`, font .85em, no background. | Put the risk note directly under "Fetch captions locally" in the field column (as on narrow), keep the warn rule/background, and link it with `aria-describedby`. Keep margin notes only for neutral info such as "Content will be sent to…". |
| U9 | Saved sources rows have no visible type badge (brief requires "Website feed / Podcast / YouTube channel"). The kind is shown only by a small aria-hidden icon. | major | sources/list, preview-*, error · both · both | [M] `.source-icon` contains only `<svg aria-hidden="true">`; no text. | Add the existing `kindBadge()` next to the title, or a visible text label under it. |
| U10 | Delete has no confirmation state in the prototype (the brief requires "Saved digests will remain available."). | minor | sources/list | [M] No confirm markup in `render.js sources()`. | Design an inline confirm row ("Delete The Daily? Saved digests will remain available. [Delete] [Cancel]") and add it as a state. |
| U11 | Feed URLs are truncated with an ellipsis and there is no way to see the full value. | minor | sources/list · desktop at ≤1024 and narrow | [M] `.source-feed` scrollWidth > clientWidth on 3 of 5 rows at 1024; no `title`. | Allow wrapping (`overflow-wrap:anywhere`) on 2 lines max, or show the full URL on hover/focus or in an expandable row. |
| U12 | Skip link and TOC ("In this digest") links scroll but do not move focus, so keyboard users stay at the top. | major | all screens with the shell; digest TOC | [M] Tab to "Skip to content", Enter → activeElement stays `.skip-link`; next Tab goes to the brand link. Cause: `render.js` click handler `e.preventDefault(); …scrollIntoView({behavior:'smooth'})` with no `.focus()`. | After scrolling, call `target.focus({preventScroll:true})` (topics need `tabindex="-1"`). Respect reduced motion (see A11). |
| U13 | Creator-only digest shows an index strip with a single entry and no explanation of why there are no topics. | minor | digest/creator-only · both · desktop | [M] `.toc` renders with only "Creator updates". | Hide the TOC when there is ≤1 section. Add one calm line under the headline: "Nothing could be summarized this time. Here is what your sources published." |
| U14 | The failed state's "3 items of 12 summarized before the error" does not say whether those summaries were kept. | minor | generate/failed | [M] text in `render.js`. | Say what happens: "3 of 12 items were summarized; nothing was saved. They will be included next time." (match the backend behaviour). |

### 1b. Visual hierarchy

- **What draws the eye first:** the "CatchUp" wordmark (54 px Big Caslon), then the date headline (38 px). For a reading app, the first topic title should come second at most. The masthead is brand, not content. [M]
- **Reading flow (desktop digest):** headline → index strip → topic title (left, 23 px) → item headline (right, 20.6 px) → summary. The left-title/right-story pattern works well and scans like FT/Guardian section fronts. [J]

| # | Finding | Sev | Where | Evidence | Fix |
|---|---|---|---|---|---|
| H1 | Duplicate dates and numbers compete. The masthead says "Tuesday, 6 October 2026 · No. 3"; the digest head says "Digest · No. 1 / Monday, 5 October 2026". On Generate, the eyebrow repeats today's date right under the masthead, and "Last digest" appears in both the hero and the rail. | major | digest/*, generate/* · all | [M] `.masthead-line` text plus `.eyebrow` on generate; hero-meta and the rail "Last digest" box on generate. | Remove the date and edition from the masthead (or show it only on Generate). Drop the Generate eyebrow date. Keep "Last digest" in one place (the rail on desktop, the hero on narrow). |
| H2 | The topic overview, the key skim text, is demoted to muted grey at 0.95em in a narrow 278 px column (17–18 CJK chars per line, 5–6 lines). | minor | digest/zh, en · desktop | [M] `c7.css .topic > .topic-overview { font-size:.95em; color: var(--muted) }`; 15.7 px. | Use `--fg` at body size for the overview (newspaper standfirst), or put it under the topic title spanning columns 1–12 before the items. |
| H3 | Empty right third on single-item topics (cols 10–12, ~290 px at 1440) creates a ragged right edge, while 2-item topics fill to the edge. Most topics have one item. | minor | digest/* · desktop | [M] Single item `grid-column: 1 / span 6` of 9; topics 0–1 end at x=1010 of 1312. | Either accept it as the measure limit and make it consistent (all items max 6 cols, nothing in 10–12), or place topic metadata (sources, item count) in cols 10–12. |
| H4 | The Creator updates section is weaker than topics (1 px rule vs 3 px), which suits its secondary role. But at creator-only it is the whole digest and occupies only cols 4–6. | minor | digest/creator-only · desktop | [M] `c7.css .creator { border-top:1px }`; one group 278 px wide. | When creator-only, use the 3 px rule and let groups flow in a 2–3 column list across cols 4–12. |
| H5 | The reason badges use 11.5 px lowercase small caps, so the glyphs look ~8 px tall. They are the only explanation of why an item has no summary. | major | digest/zh, creator-only · both · both | [M] `.reason` font-size 11.5 px, `font-variant: small-caps; text-transform: lowercase` (`c3b.css`). | Render reasons in sentence case at ≥ 13 px (normal caps, e.g. "Caption fetching is off"). Small caps are fine for labels, not for explanatory text. |

### 1c. Consistency

| # | Element | Issue | Sev | Evidence | Fix |
|---|---|---|---|---|---|
| C1 | Status colours | "Failed" (error) and "Possible gap"/"Rate limited" (warn) are nearly the same brown/amber in both themes, so an outright failure looks like a soft warning. | major | [M] Light `--error #8a4b00` / `--warn #8a5300`, soft `#f3e4cf` / `#f6ead2`; Dark `--error #f0b062` / `--warn #f2b65e` (`c3.css` overrides c.css). generate/summarizing, sources/list. | Give error a distinct hue (e.g. a muted brick red different from the brand red, light ~`#a32a1f` on `#f8e1dc`), keep warn amber, and keep the icon and text. |
| C2 | Surfaces | The digest and Settings use rules only (no boxes), but Generate, Sources, History and offline still use bordered cards and filled list boxes. Two visual languages exist in one direction. | minor | [J] `.card` / `.source-list` / `.history-link` keep border + `--surface`; `c7.css` strips boxes only for `.settings-section`. | Convert run/result cards, the add form, source rows and history rows to ruled rows (top rule, no box) to match the broadsheet grid, or consciously keep boxes only for interactive panels (preview, alerts). |
| C3 | Creator groups | Item titles in neighbouring creator groups do not line up (13 px offset) because grid rows stretch inside each group. | minor | [M] `.creator-group` h3 heights 25 px vs 38 px; first link y=1544 vs 1557 (desktop). | `.creator-group { align-content: start; }` |
| C4 | Stepper (narrow) | Steps wrap to 3 rows and each wrapped step keeps its leading connector line, so dashes dangle at the start of rows. | minor | [M] `.stepper` 314 px wide, steps at y=638/670/702; `base.css .step + .step::before`. | At ≤640 px, show the stepper vertically without connectors, or show only "Step 2 of 3 · Summarizing". |
| C5 | Typography / CJK fallback | C7's body and heading stacks fall back to Songti SC / STSong / Noto Serif CJK SC. The brief's required CJK fallbacks (PingFang SC, Hiragino Sans GB, Noto Sans CJK SC, Microsoft YaHei) are not in the reading stacks. Windows has no Songti SC, so Chinese falls to the generic serif (SimSun), which is thin and hard to read at 16.5 px. | major | [M] Computed `font-family`: "Iowan Old Style", "Hoefler Text", Georgia, "Songti SC", STSong, "Noto Serif CJK SC", serif (`c3.css`). `--cjk` defined in base.css is unused by c3/c3b. | Append the brief's list after the serif CJK faces (…"Noto Serif CJK SC", var(--cjk), serif), or decide on sans CJK for body text. Test on Windows and Linux. |
| C6 | Offline page | It is top-aligned, has no masthead or wordmark, and its centered card breaks C7's own "text columns never centered" rule. | minor | [M] `.offline-card` y = page top; `.app .page { align-items:start }` beats `.page-offline { place-items:center }`. | Show the compact masthead, put the message left-aligned in columns 1–8, or fix the specificity so it is vertically centred. |
| C7 | Two primary buttons | Sources preview shows "Preview" and "Confirm source", both black primary. | minor | [M] 2 `.btn-primary` in sources/preview-*. | When a preview is open, make "Preview" secondary. |

### 1d. Content / copy

| # | Finding | Sev | Where | Evidence | Fix |
|---|---|---|---|---|---|
| K1 | The rail shows populated data on screens that are supposed to be empty. First-run shows "Last digest: Monday, 5 October 2026 · 12 items" and "Your sources 5". Empty History shows "Archive 3 digests · 6 items in total". | major | generate/first-run, history/empty · all | [M] `render.js rail()` ignores state. | Use state-aware rail content: first-run → "Getting started" (1. Model, 2. Sources, 3. Generate); empty history → hide Archive or show "0 digests". |
| K2 | The digest header has no time ("Monday, 5 October 2026"). The brief asks for created time (e.g. "5 Oct 2026, 21:48"), and three digests on the same day can only be told apart by "No.". | major | digest/* | [M] `.page-title` = longDate only; `.digest-meta` has no time. | Add the time to the headline or meta: "Monday, 5 October 2026 · 21:48". |
| K3 | Sample data contradicts itself, which makes the review harder and could hide layout bugs. Masthead "No. 3" on every screen including first-run. Generate "Last digest … 12 items · 4 sources" vs History No. 3 "1 item · 1 source". Digest No. 1 created 21:48 vs History No. 1 at 19:48. Lede says "your 5 sources" while runs check 4. | minor | generate/*, history/list, digest/zh | [M] `data.js lastDigest`, `history[]`, `digests.zh.created`. | Make the sample data consistent so each state tells one story. |
| K4 | Preview entry dates are one day early ("30 Sept" for 2026-10-01): date-only ISO strings are parsed as UTC and then shown in local time. | minor | sources/preview-youtube, preview-podcast | [M] data `'2026-10-01'` → shown "30 Sept". | Format date-only values as dates, without timezone conversion (append `T00:00` or use a date-only formatter). The real app must avoid this too. |
| K5 | `text-transform: lowercase` + small caps lowercases proper nouns and dates in the DOM/AX text: "youtube channel", "tuesday, 6 october 2026", "generate digest". Copy/paste and some screen readers get the lowercased text. | minor | all · eyebrow, chips, badges, buttons, section labels | [M] `innerText` returns lowercase (e.g. "youtube channel"); rule in `c3b.css`. | Use `font-variant-caps: all-small-caps` without `text-transform: lowercase`. Write labels in sentence case. |
| K6 | The "Rate limited" chip in run results lacks the brief's "(try later)" guidance; "Possible gap" is explained only in the Sources rail. | minor | generate/succeeded, summarizing | [M] chip text only. | "Rate limited · try later" and a short tooltip/inline note for "Possible gap". |
| K7 | Settings section headings are announced as "1Model provider", "2Digest" (the number glued to the text). | minor | settings/* | [M] h2 textContent. | Make `.step-num` `aria-hidden="true"` and add visually hidden "Step 1: ", or add a separator. |

---

## 2. Accessibility audit (WCAG 2.1 AA)

**Summary:** 15 issues, 0 critical, 7 major, 8 minor.

### Perceivable

| # | Issue | WCAG | Sev | Where | Evidence | Fix |
|---|---|---|---|---|---|---|
| A1 | Chinese content has no language tag. Topic titles, overviews and summaries in Chinese sit inside `<html lang="en">`, so screen readers use the English voice or mispronounce them. | 3.1.2 Language of Parts | major | digest/zh, history/list (topic previews) · all | [M] Only `HTML:en` has a `lang` attribute. | Put `lang="zh-Hans"` on generated text containers (topic title, overview, summary, points) using the digest language setting. Leave item titles in their original language (or `lang` from the feed). |
| A2 | `--subtle` text fails contrast in light theme: source feed URLs, last-check times, the "Your sources" count, history counts, and upcoming stepper steps. | 1.4.3 Contrast (Minimum) | major | sources/list, preview-*, error; history/list; generate/collecting, summarizing · light · both | [M] `#77736a` on `#f4f0e6` = 4.15:1; on surface `#f8f5ed` = 4.34:1 (12.9–15 px text). Dark passes (5.04 / 4.76). | Darken light `--subtle` to ≥ `#6b675f` (≈4.9:1 on bg). Use `--muted` for informative text like feed URL and last-check time. |
| A3 | Placeholder text fails contrast, and it carries information: the saved key "•••• 3f9a" is shown only as a placeholder. | 1.4.3 | major | settings/saved, tested, error · both · both (also the URL field hint) | [M] Default `::placeholder` `#757575` = 3.96:1 on dark bg `#161513`; ≈4.0:1 on light bg. | Show the saved state as real text ("Saved key ending 3f9a" with a Replace button), and style `::placeholder` with `--muted`. |
| A4 | The "off" switch is almost invisible in light theme: the track and the white thumb have no 3:1 boundary against the page. | 1.4.11 Non-text Contrast | major | settings/first-run, error ("Fetch captions locally" off) · light · both | [M] Track `--disabled #dcd9d0` vs bg `#f4f0e6` = 1.24:1; thumb `#fff` vs track = 1.41:1. Dark passes via the thumb (12.8:1). | Give the off track a 1 px `--muted` border or a darker fill (≥3:1 vs bg, e.g. `#8c877c`), and keep the thumb high-contrast. |
| A5 | The source type is conveyed only by an `aria-hidden` icon in saved source rows and item meta. | 1.1.1 / 1.3.1 | minor | sources/list; digest item-meta | [M] `.source-icon svg[aria-hidden]`. Item meta also has an icon only. | Add visible text (see U9) or a visually hidden label ("Podcast"). |
| A6 | The progress bar has no accessible name. | 1.3.1 / 4.1.2 | minor | generate/collecting, summarizing | [M] `<progress value="5" max="12">` with no `aria-label`/`labelledby`. | `aria-labelledby` → the `.progress-label` id. |
| A7 | Field errors and hints are not programmatically linked to their inputs. The Sources URL input in the error state is not marked invalid at all, so there is no visual or programmatic error on the field. | 3.3.1 Error Identification / 1.3.1 | major | sources/error; settings/error · all | [M] `#url` has no `aria-invalid`/`aria-describedby`; `#key` has `aria-invalid="true"` but no `aria-describedby`; hints are not linked. | Add `aria-invalid="true"` + `aria-describedby="<error id> <hint id>"` on the input; give the error an id. |
| A8 | Reflow at 320 CSS px: the source preview card scrolls horizontally because the action buttons do not wrap. | 1.4.10 Reflow | minor | sources/preview-* · width 320 (above 420 it is fine) | [M] `.app` scrollWidth 342 vs 320; `.actions` = 198 + 84 + gap (nowrap buttons). Digest at 320: no overflow. | `.actions { flex-wrap: wrap; }`. |

### Operable

| # | Issue | WCAG | Sev | Where | Evidence | Fix |
|---|---|---|---|---|---|---|
| A9 | The skip link does not move focus, so the bypass mechanism fails for keyboard users. TOC links have the same problem. | 2.4.1 Bypass Blocks / 2.4.3 Focus Order | major | all shell screens; digest TOC | [M] See U12: after Enter on "Skip to content", focus stays on it and the next Tab goes to "CatchUp". | `main.focus()` / `section.focus()` after scrolling (`tabindex="-1"` on targets). |
| A10 | Focus indicator: works well. Every focusable element showed a 2 px accent outline with 2 px offset (inputs −1 px). No issues found. | 2.4.7 | pass | settings/saved dark; settings/first-run light | [M] Tab sequence: skip link → brand → 4 nav → Base URL → API key → Test connection → Model → Language → 2 switches → Save. Outline `#e0796d` (6.19:1 dark) / `#8a1c14` (8.18:1 light). | — |
| A11 | JS smooth scrolling ignores reduced motion: `scrollIntoView({behavior:'smooth'})` overrides the CSS `scroll-behavior: auto` in the reduce media query. | 2.3.3 (AAA) / brief requirement | minor | digest TOC, skip link | [M] `render.js` handler. | Use `behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'`. |
| A12 | Target sizes: TOC links are 21 px tall and "← All digests" is 89x21. They pass the spacing exception but are below the 24 px practice (2.5.8 in WCAG 2.2). 2.5.5 (44 px) is AAA in 2.1. | 2.5.5 (AAA) / 2.5.8 (2.2 AA) | minor | digest/* | [M] `.toc a` h=21; nav links 34–36 px tall; Delete 65x34; buttons ≥ 34 px. | Add `padding-block: .15rem` to TOC links and the back link. |

### Understandable

| # | Issue | WCAG | Sev | Where | Evidence | Fix |
|---|---|---|---|---|---|---|
| A13 | The risk note for the caption toggle is not associated with the switch. | 3.3.2 Labels or Instructions / 1.3.1 | minor | settings/* | [M] `.risk` has no id; the switch input has no `aria-describedby`. | `aria-describedby` on the switch input → the risk note id (and move it next to the toggle, U8). |

### Robust

| # | Issue | WCAG | Sev | Where | Evidence | Fix |
|---|---|---|---|---|---|---|
| A14 | Run completion and "no new content" are not announced. The live region (`aria-live` on `.run-card`) is replaced by a new `.result-card` with no live role. Also, the live region wraps the whole card, so every update would read the stepper and all source rows. | 4.1.3 Status Messages | major | generate/collecting → succeeded / no-new-content | [M] `.run-card[aria-live=polite]`; `.result-card` has neither `role` nor `aria-live`. (Failed uses `role=alert`, which is OK.) | Keep one persistent, visually hidden `role="status"` region outside the swapped content. Write short messages to it: "Summarizing, 5 of 12", "Digest ready: 12 items", "No new content". Remove `aria-live` from the big card. |
| A15 | Stepper state is only partly exposed: the done state is a checkmark icon (aria-hidden) plus green colour, and only the current step has `aria-current`. | 1.3.1 / 1.4.1 | minor | generate/collecting, summarizing | [M] `.step.is-done` has no text. | Add visually hidden "(done)" / "(next)" to the steps. |

### Color contrast check (measured)

| Element | Fg | Bg | Ratio | Req. | Pass |
|---|---|---|---|---|---|
| Body / summary (light) | #151412 | #f4f0e6 | 16.18 | 4.5 | ✅ |
| Muted: overview, item meta, digest meta (light) | #4a4741 | #f4f0e6 | 8.13 | 4.5 | ✅ |
| Accent eyebrow / nav current / TOC title (light) | #8a1c14 | #f4f0e6 | 8.18 | 4.5 | ✅ |
| Reason badge (light) | #4a4741 | #e9e3d5 | 7.23 | 4.5 | ✅ (size issue, H5) |
| Subtle: feed URL, times, counts (light) | #77736a | #f4f0e6 / #f8f5ed | 4.15 / 4.34 | 4.5 | ❌ |
| Upcoming step (light, in card) | #77736a | #f8f5ed | 4.34 | 4.5 | ❌ |
| Chips ok / warn / error (light) | — | soft bgs | 5.56 / 5.31 / 5.45 | 4.5 | ✅ |
| Placeholder (both) | #757575 | #161513 / #f4f0e6 | 3.96 / ≈4.0 | 4.5 | ❌ |
| Body (dark) | #ece7dc | #161513 | 14.8 | 4.5 | ✅ |
| Muted (dark) | #b8b2a5 | #161513 | 8.65 | 4.5 | ✅ |
| Subtle (dark) | #8c8679 | #161513 / #1c1b18 | 5.04 / 4.76 | 4.5 | ✅ |
| Accent (dark) | #e0796d | #161513 | 6.19 | 4.5 | ✅ |
| Error alert text (dark) | #f0b062 | #33271a | 7.67 | 4.5 | ✅ |
| Switch off track vs page (light / dark) | #dcd9d0 / #33322f | bg | 1.24 / 1.42 | 3.0 | ❌ light (dark OK via thumb) |
| Focus ring (light / dark) | accent | bg | 8.18 / 6.19 | 3.0 | ✅ |

### Keyboard navigation

| Element | Tab order | Enter/Space | Notes |
|---|---|---|---|
| Skip link | 1st | scrolls only | ❌ focus does not move (A9) |
| Brand, nav (4) | 2–6 | navigate | ✅ visible ring |
| Settings fields, selects, switches | logical, top to bottom | native | ✅; the switch label hit area is too large (U7) |
| TOC links | after the back link | scroll only | ❌ focus stays in the TOC (A9) |
| Item / creator links | in DOM order | open new tab | No "opens in new tab" hint (advisory, 3.2.5 AAA) |

### Screen reader (from DOM)

| Element | Announced as | Issue |
|---|---|---|
| Landmarks | banner, navigation "Main", main, complementary "About this page", navigation "In this digest" | ✅ good |
| Headings (digest) | h1 date → h2 topic → h3 item → h2 Creator updates → h3 creator | ✅ logical |
| Chinese summary | read with the English voice | ❌ A1 |
| Settings h2 | "1Model provider" | K7 |
| History row link | "5Oct No. 3 · Monday, 5 October 2026 · 22:23 …" | Redundant date; set `aria-hidden` on the `.history-date` badge (minor) |
| Run finished | nothing | ❌ A14 |

---

## What works well

- Strong, calm editorial hierarchy. The left topic title column beside the story area is an excellent reading structure for long digests on desktop, and the index strip is a lightweight jump list.
- Light-theme contrast is generous for all reading text (16:1 body, 8:1 muted). Both themes pass for body, muted, accent and status text.
- Mixed CJK/English typesetting looks good: summary measure at 1440 is ~48 CJK chars / ~75 Latin chars per line, line-height 1.75.
- Clean semantics: real landmarks, a sensible heading tree, `aria-current` on nav and step, labelled inputs, `role="switch"`, `aria-label="Delete <title>"`, `role="alert"` on errors.
- Visible focus rings everywhere (2 px accent, offset), and the tab order follows the visual order.
- No horizontal overflow at 420 px on any screen, and none at 320 px on the digest.
- Errors are not brand red and always carry an icon and text. Badges always have text (colour is never the only signal).
- The Settings "section rows" mirror the digest grid, so the direction feels coherent on desktop. Calm, honest copy ("listed without a summary because…").

## Priority recommendations

1. **Make reading start sooner.** Compact masthead on Digest and on narrow windows; one-row nav; remove duplicate dates and edition numbers (U1, H1).
2. **Fix the item grid.** Never put a long summary in the 3-column slot; use equal headline sizes (U2, U3).
3. **Fix the keyboard and screen-reader paths.** Skip link and TOC move focus; `lang="zh-Hans"` on generated text; a single persistent status region for run progress and completion (A9, A1, A14).
4. **Token fixes.** Darken light `--subtle`; give the off switch a 3:1 track; style placeholders and stop using the placeholder for the saved key; give "error" a different hue from "warn" (A2, A4, A3, C1).
5. **Make the rail and copy state-aware.** Rail content per state, time in the digest header, consistent sample data, a fixed date-only formatter (K1, K2, K3, K4).
6. **Settings.** Put the ToS risk note directly under its toggle with `aria-describedby`, and shrink the switch hit area (U7, U8, A13).

---

## Resolution (verified and applied, 2026-10-06)

Every finding was checked against the source or measured before any change.
- **Confirmed by measurement:** `--subtle` 4.15:1, switch track 1.24:1, error `#8a4b00` vs warn `#8a5300`, placeholder `#757575`, first topic at 537 of 768 px, masthead "No. 3" vs digest "No. 1", no `lang` on Chinese content, scroll without focus, `aria-live` only on the replaced card, date-only values shown a day early.
- **Rejected:** none.
- **Noted as optional:** A12 target size is WCAG 2.2 (2.5.8), not 2.1 AA. It was still applied (TOC and back-link padding).
- **Planner's own error:** the earlier token check had used a 3:1 threshold for `--subtle`, although that text is informative.

Changes, by finding:
- **Masthead and dates (U1, H1, K2, K3, K4):**
  - one-row masthead on the digest and on narrow windows
  - the masthead shows today's date only
  - edition numbers appear on the digest and in History only
  - the duplicate Generate date and the duplicate "Last digest" are removed
  - the digest headline includes the time
  - sample data made consistent; date-only values parsed as local time
- **Items and digest layout (U2, U3, H2, H4, U13):**
  - item width comes from content (`item-long` spans 6 of 9 columns, `item-short` spans 3), and all titles are the same size
  - the overview uses body color and size
  - a Creator-updates-only digest gets a 3 px rule, an explanatory line, and no single-entry index
- **Generate (U4–U6, U14, K1):**
  - one primary action per state ("Set up your model" on first run; "View digest" after success; "Check settings" after a configuration error)
  - the failed-run copy states what was kept
  - the rail follows the state (Getting started; no archive counts when History is empty)
- **Settings (U7, U8, A13, K7):**
  - the switch hit area is reduced to 220×26 px
  - the caption risk note sits directly under its toggle, linked by `aria-describedby`
  - step numbers are `aria-hidden` and followed by visually hidden "Step N:" text
- **Sources (U9–U11, C7, A7):**
  - visible type badges
  - a `confirm-delete` state
  - feed URLs wrap to two lines with a `title`
  - Preview becomes secondary while a preview is open
  - the URL input has `aria-invalid` and `aria-describedby` linking the error and the hint
- **Tokens (C1, A2–A4):**
  - light `--subtle` changed to `#66625a` (5.33:1)
  - error is now burnt orange `#a33a00`, distinct from warn olive `#6b5e00` and from the brand red; dark theme uses `#ff9a62` / `#d9c25a`
  - placeholders use `--muted`
  - the saved key is shown as text
  - the switch has a 1.5 px `--muted` boundary in the off state

  A strict re-check (all text 4.5:1, the switch boundary 3:1) passes in both themes.
- **Small caps (K5):** `font-variant-caps: all-small-caps` replaces the lowercase transform, so text such as "YouTube" keeps its case. Reasons use sentence case at 0.88em.
- **Accessibility (A1, A5, A6, A9, A11, A14, A15, C5):**
  - `lang="zh-Hans"` on generated text (12 elements in the zh digest)
  - the skip link and the digest index move focus (verified: focus lands on `#main` and `#t0`)
  - reduced motion is respected
  - one persistent `role="status"` region announces run progress and results
  - the progress bar is named by its label
  - stepper steps carry "(done)", "(in progress)", and "(next)"
  - source kind is announced in item meta
  - CJK fallbacks added after the serif faces
- **Other (C2, C3, C4, C6, A8):**
  - run results, the add form, source rows, and history rows use rules instead of boxes
  - creator groups align to the top
  - the narrow stepper is vertical
  - the offline page is centered with a wordmark
  - preview actions wrap
