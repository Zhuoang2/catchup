## ADDED Requirements

### Requirement: Gather related context for website items
For each entry of a website feed, the system SHALL keep the entry's links in body order with their anchor text, and its comment pointers when the feed provides them: the comments URL, the comment feed URL, the comment count, and the entry author. Once per run, after every source is checked and before the run chooses its items, the system SHALL gather context for each pending website item that has none yet:
- **Related links.** At most a configurable number of links per item (default 8), in body order. These are excluded:
  - links to the item itself;
  - same-site tag, category, archive, author, page, and search pages;
  - login-scoped or share pages;
  - image and PDF links;
  - `mailto:` and `javascript:` links;
  - x.com and twitter.com.

  Each linked page's extracted text MUST be cut to 3,000 characters, and an item's linked context MUST stay within 16,000 characters.
- **Author replies.** When the feed reports comments on the post, the author's own replies are read from the post page, each with the comment it answers. At most 10 replies and 4,000 characters are kept. When the page shows none, the post's comment feed is used.

Every context fetch MUST go through the safe fetcher with the run's host spacing. It MUST honor the site's robots.txt for CatchUp's User-Agent, and MUST count against a per-run limit (default 60). A context fetch that fails, is refused, or exceeds the limit MUST be skipped without failing the source check or the run. Gathered context SHALL be stored with the item and reused by later runs. Podcast episodes and YouTube videos MUST NOT get linked or comment context.

#### Scenario: Short post with linked pages
- **WHEN** a pending website item links to its GitHub release, a project page, a changelog, and two of the site's tag pages
- **THEN** the release, project, and changelog pages are read as the item's context, and the tag pages are not fetched

#### Scenario: Author replies in comments
- **WHEN** the feed reports 12 comments on a post, and the post page marks 2 of them as written by the post's author
- **THEN** those 2 replies, each with the comment it answers, are kept as the item's context

#### Scenario: robots.txt disallows a linked page
- **WHEN** a linked page's site disallows CatchUp's User-Agent for that path
- **THEN** the page is not fetched, and the item is summarized without it

#### Scenario: Per-run fetch limit reached
- **WHEN** a run's items have more related links than the per-run limit allows
- **THEN** context fetches stop at the limit, the run continues, and the remaining items are summarized from what was gathered

#### Scenario: Context gathered once
- **WHEN** an item's context was gathered in a run that then failed, and the user starts a new run
- **THEN** the stored context is reused, and the linked pages are not fetched again
