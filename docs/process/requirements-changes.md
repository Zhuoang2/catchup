# Requirements Changes

Each entry: date, change, reason, source. Changes before 2026-10-01 are reconstructed from `docs/handoff.md`.

| Date | Change | Reason | Source |
| --- | --- | --- | --- |
| before 2026-10-01 | Automatic daily digest → manual "Generate Digest" covering the period since the last successful request | Simpler first release; users who check less often still get everything since their last digest | handoff §4 |
| before 2026-10-01 | Scope narrowed from "any website" to selected public sites/blogs and podcasts/videos with accessible transcripts | Arbitrary scraping is unreliable; summarizing audio/video without transcripts would overclaim | handoff §3 |
| before 2026-10-01 | Bookmarks, likes, feedback moved after the core workflow (still planned, not dropped) | Core collect → digest flow comes first | handoff §4 |
| before 2026-10-01 | Browser extension, logged-in content, page-change detection, scheduling → stretch / later | Keep the initial release achievable | handoff §4 |
| 2026-10-02 | No per-run limit on how many new items a digest covers (a proposed cap of 50 was rejected) | User wants every new item included after a long gap; progress display and batched topic grouping handle volume instead | User feedback on `add-core-digest-flow` proposals |
| 2026-10-02 | New future feature: let the user choose to output only the N most important items | User request; per-item summaries in the chosen design make ranking possible later | User feedback on `add-core-digest-flow` proposals |
| 2026-10-02 | Digest language is chosen by the user in Settings during initial setup (English, Simplified Chinese, same as original, or another language), instead of an environment variable defaulting to English | User request; the audience is not English-only. Cached item summaries now record their language so a language change re-summarizes instead of mixing languages | User feedback on the `add-core-digest-flow` plan |
