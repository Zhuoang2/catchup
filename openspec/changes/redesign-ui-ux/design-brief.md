# Design brief: CatchUp UI/UX (for Claude Design)

Context for this file: written for claude.ai/design to explore visual directions for change `redesign-ui-ux` (#24). It is based on `research.md` (the current UI, its data, and its states). Paste everything below the line into Claude Design. Attach the screenshots of today's pages if you have them.

---

## What CatchUp is

CatchUp is a personal "catch up on what I follow" app. The user adds the blogs, podcasts, YouTube channels, and social feeds they follow. When they choose, they press **Generate Digest**. CatchUp then:
1. checks every source for items that are new since the last digest
2. summarizes each new item with the user's own AI model (for podcasts and videos, from transcripts or captions)
3. groups the items into topics, each with a short overview

The result is a digest the user reads like a briefing, with a link back to every original.

- **Single user, runs locally.** It runs on the user's own computer (Docker or from source) and opens at `http://localhost:8000`. It is installable as a desktop web app (PWA), so it usually lives in its own app window with a Dock icon, not a browser tab. There is no login and no hosted service.
- **Language.** The interface is English. Digest content (topic titles, overviews, summaries) is in the language the user chooses, often Simplified Chinese, while item titles and source names usually stay in their original language. Designs must look good with **mixed Chinese and English text**.
- **Usage pattern.** It is used occasionally (daily or every few days), in one sitting: generate, wait about 30 s to a few minutes, then read. Reading the digest is the main activity, so it should feel calm and pleasant for long reading.

## What to produce

Please create **3 clearly different visual directions** for the same app. For each direction provide:
- **Design tokens:** color palette (light **and** dark), type scale, spacing, radius, and shadows.
- **The six screens below**, including the key states listed for each.
- **A small component set:** primary, secondary, and danger buttons; text input; select; toggle or checkbox; status badge or chip; card; inline alert (error, warning, info, success); progress indicator; empty state.
- **An app icon** for the Dock (an opaque, full-bleed square that works at 512 px and when tiny).

Suggested starting points. Feel free to propose better ones, as long as the three differ clearly:
- **A. Quiet reader.** Editorial and calm, like a good read-later app: generous whitespace, a readable text column, warm neutral background, subtle accents.
- **B. Focused workspace.** Compact and tool-like: a sidebar with the four sections, crisp status chips, and dense lists for sources and history.
- **C. Morning briefing.** A newspaper or briefing feel: strong typographic hierarchy, topic cards, and one confident accent color.

## Constraints

- **Desktop window first:** 1280×800 down to a narrow app window of about 420 px wide. No phone-specific design is needed, but nothing should break when narrow.
- **Offline-friendly:** no web-font CDNs. Use system font stacks, or fonts we can bundle. CJK fallbacks must render well: PingFang SC, Hiragino Sans GB, Noto Sans CJK SC, Microsoft YaHei.
- **Accessibility:** WCAG AA contrast in both themes, visible keyboard focus, color never the only signal (badges have text), a live-updating progress area, and reduced-motion friendly.
- **Implementation:** React 19 + Vite; plain CSS or a light component library. Avoid designs that depend on heavy animation or images. No stock photos; small line icons are fine.
- **Tone of copy:** plain, honest, calm. CatchUp never pretends to have summarized something it did not process: an item without a transcript is listed, not summarized.

## Navigation

Four sections: **Generate** (home), **Sources**, **History**, **Settings**. A digest opens from Generate (after a run) or from History. The app name is **CatchUp**.

## Screens, content, and states

### 1. Generate (home)

The starting point: one primary action, then live progress, then the result.
- **Idle, first use:** no model configured yet. Show a friendly first-run prompt: "Set up your model in Settings first", with a link, before the Generate button is useful. Also show a hint when no sources exist yet.
- **Idle, normal:** a big **Generate Digest** button, and perhaps the last digest's date with a link.
- **Running:** the button is disabled while a run is active. Show the stage — **Checking sources** → **Summarizing** → **Grouping topics** — with a count:
  - checking sources: "Sources checked: 2 of 3"
  - summarizing: "Items summarized: 5 of 12"
  - Source results appear as they arrive, one row per source: "The Daily — no new items", "How to Start a Podcast — new items", "Google for Developers — failed: The source could not be fetched."
  - Other outcomes to design for: "rate limited (try later)" and "possible gap" (older items may have been missed).
- **Succeeded:** a clear link to **View digest**; "Tokens: 8,663 in / 1,893 out"; held-back counts such as "5 items waiting for transcripts or captions" and "2 videos deferred to the next run".
- **No new content:** "No new content", plus the waiting count and the per-source results. Tokens: 0 in / 0 out.
- **Failed:** an error message, for example "The provider rejected the API key. Check the model settings." Generate is available again.

### 2. Digest (the main reading screen)

Header: created time (e.g. "5 Oct 2026, 21:48"), model ("deepseek-flash"), tokens, and the number of items and sources. The body is a list of **topics**. Each topic has a title, an overview, and items. Each **item** has:
- its title, linking to the original (opens outside the app)
- source name · published time
- its summary:
  - usually 2–4 sentences
  - for long podcast or video transcripts, an overview paragraph followed by 3–6 key points (a bullet list)
  - an item whose summary failed shows "Summary unavailable"

After the topics comes the **Creator updates** section. It lists items that could not be summarized, grouped by creator or show, with title, time, link, and a **reason badge**. The reasons are:
- "Caption fetching is off"
- "This video has no captions"
- "Blocked by YouTube"
- "Captions could not be fetched"
- "No transcript within 7 days"

It must feel neutral and useful ("here is what they published"), not like an error list. A digest can contain **only** Creator updates.

A long digest may have 10+ topics. Consider a topic outline or jump list.

Real sample content from a test run (digest language zh-Hans):

> **Topic:** 播客脱颖而出的制作与定位策略
> **Overview:** 围绕如何让播客节目脱颖而出，强调先明确听众、信息与视角，再用"十个词描述"聚焦定位，并结合内容打磨、社区联动、低成本推广和务实预期来实现可持续成功。
> **Item:** The Key to Making Your Podcast Stand Out // Eric Nuzum — *How to Start a Podcast* · 2026-10-01
> **Summary (long transcript):**
> 本期节目由 Travis Albritton 与播客制作人 Eric 对谈，围绕如何让播客脱颖而出，以及新书《Make Noise》的创作背景展开。Eric 结合在 NPR、Audible 和 Magnificent Noise 的经验，强调先理解听众、明确信息与视角，再考虑形式和资源。
> - 出书动机：播客行业已成熟，新节目激增，很多创作者面临的障碍相似；本书聚焦如何把内容做好，而非设备购买或变现技巧。
> - 十个词描述：具体定义听众、要带他们经历的旅程、你想说的话、你的身份/视角和期望结果。
> - 成功与预期：先定义听众，才能定义成功；不要因没有赞助或巨大下载量而过早放弃。
> - 推广与采访：最好的营销是让下一集比上一集更好；采访要真诚好奇，后期像讲故事一样剪辑。

> **Topic:** 利用 Gemini 将语音转化为实体打印纪念物
> **Overview:** 介绍 Journal Receipts 项目：一盏可对话的灯，使用 Gemini 分析说话中的情绪、语气和氛围，再由 Nano Banana 生成象征性图案，并打印成可触摸的收据式纪念物。
> **Item:** How to transform audio into physical prints using Gemini and Google AI Studio — *Google for Developers* · 2026-10-01
> **Summary:** 该项目名为 Journal Receipts，是一盏可以与之对话的灯。它利用 Gemini 分析说话中的情绪、语气和氛围，再将结果交给 Nano Banana 生成象征性图案，并打印成可触摸的收据式纪念物。

> **Creator updates:**
> *Google for Developers* — "How to transform audio into physical prints using Gemini and Google AI Studio" · 2026-10-01 · badge: Caption fetching is off
> *The Daily* — "(an episode title)" · 2026-10-04 · badge: No transcript within 7 days

Also show the same screen with an English digest (topic titles and summaries in English) to check that the design works in both.

### 3. Sources

- **Add a source:** one input, "Website or feed URL" (a blog, a feed, an Apple Podcasts link, a YouTube channel, a Bluesky/Mastodon profile), with a **Preview** button.
- **Preview card** before saving:
  - title (e.g. "The Daily")
  - feed URL and site URL
  - a **type badge**: Website feed / Podcast / YouTube channel
  - a line on how content is obtained:
    - podcast: "Transcripts published by the show"
    - YouTube with captions on: "Captions fetched from YouTube on this computer"
    - YouTube with captions off: "Caption fetching is off; videos will be listed without summaries"
  - an optional scope notice: "CatchUp will follow the whole show, not only this episode." or "…the whole site's feed, not only this page."
  - up to 5 recent entries (title and date)
  - **Confirm source** and Cancel
- **Errors** (inline, plain language):
  - "Enter a valid HTTP or HTTPS URL."
  - "This address is not allowed."
  - "No supported feed was found at this URL."
  - "The URL did not return a parsable feed."
  - "A source for this feed already exists: The Daily."
  - "Rate limited — try again later (about 30 seconds)."
- **Saved sources list:** each row has the title, type badge, feed URL (secondary), the last check (status + time: "New items · 5 Oct 21:48", "No new items", "Failed", "Never checked"), flags ("Rate limited", "Possible gap"), and **Delete**. Delete asks for confirmation: "Saved digests will remain available."
  - Example rows: "The Daily" (Podcast, no new items), "How to Start a Podcast" (Podcast), "Google for Developers" (YouTube channel, failed), "Astral Codex Ten" (Website feed).
- **Empty state:** "No sources added yet". Suggest example kinds of URLs.

### 4. Settings

Three groups. A first-time user should be able to complete it top to bottom.

**Model provider**
- Note: "Content will be sent to your configured model provider."
- Base URL (default `https://api.deepseek.com`).
- API key (masked; when saved, show `•••• 3f9a`; the key is never shown back).
- **Test connection**, which then fills the **Model** dropdown (e.g. deepseek-flash, deepseek-v4-pro).
- Success: "Connection succeeded. Choose a model and save."
- Errors: "The provider rejected the API key.", "Could not reach the model provider. Check the base URL.", "The provider account has insufficient balance."

**Digest**
- Language: English / 简体中文 / Same as original / Other (free text).

**YouTube**
- Toggle: **Fetch captions locally** (off by default), with this risk note, which must stay readable, not hidden: "Fetches captions from YouTube from this computer. YouTube's Terms of Service do not allow automated access, so turn this on only if you accept that risk. When off, new videos are listed under Creator updates without a summary."
- Toggle: **Skip Shorts** (on by default).

Then **Save**, and the confirmation "Settings saved."

### 5. History

- A list of saved digests, newest first: date and time, "12 items · 4 sources". A short preview of the topic titles would be welcome, but it is optional.
- Empty state: "No saved digests yet".

### 6. Offline page (installed app window)

Shown when the app window opens but CatchUp's server is not running:

"CatchUp isn't running. Start it with `docker compose up -d` (or `uv run catchup serve`), then reload."

Show a reload button and keep it calm.

## Out of scope

Login or accounts, multi-user, mobile apps, onboarding tours, notifications, bookmarks and likes (planned later), and editing sources.
