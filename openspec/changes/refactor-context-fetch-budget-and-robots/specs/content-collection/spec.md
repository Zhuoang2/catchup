## MODIFIED Requirements

### Requirement: Gather related context for website items
For each entry of a website feed, the system SHALL keep the entry's links in body order with their anchor text, and its comment pointers when the feed provides them: the comments URL, the comment feed URL, the comment count, and the entry author. Once per run, after every source is checked and before the run chooses its items, the system SHALL gather context for each pending website item that has none yet:
- **Related links.** At most a configurable number of links per item (default 8), in body order. These are excluded:
  - links to the item itself;
  - same-site tag, category, archive, author, page, and search pages;
  - login-scoped or share pages;
  - image and PDF links;
  - video watch pages;
  - `mailto:` and `javascript:` links;
  - x.com and twitter.com.

  A link counts as same-site when its host equals the site's host, ignoring a leading `www.`. The same rules apply to a page's final URL after redirects.

  Each linked page's extracted text MUST be cut to 3,000 characters, and an item's linked context MUST stay within 16,000 characters.
- **Author replies.** When the feed reports comments on the post, the author's own replies are read from the post page, each with the comment it answers, including when the theme lists replies after the comment they answer rather than inside it. At most 10 replies and 4,000 characters are kept. When the page shows none, the post's comment feed is used.

Every context fetch MUST go through the safe fetcher with the run's host spacing. It MUST honor the site's robots.txt for CatchUp's User-Agent, and MUST count against a per-run limit (default 60). robots.txt is read once per run for each origin. Two URLs have the same origin when their scheme, host, and port are the same: the host ignores letter case, and a URL without a port has its scheme's default port (80 for HTTP, 443 for HTTPS). When robots.txt cannot be read because of a server error (HTTP 5xx), a network error, or any other failure that returns no 4xx status, the system MUST NOT request any URL on that origin in a context fetch for the rest of the run. A 401 or 403 answer also refuses every such request. Any other 4xx answer means that the origin has no robots.txt, and every page is allowed. Before a context fetch follows a redirect, the system MUST check the target against the robots.txt of the target's origin in the same way. A refused target is not requested, and the fetch counts as refused. A context fetch that fails, is refused, or exceeds the limit MUST be skipped without failing the source check or the run. Gathered context SHALL be stored with the item and reused by later runs. When the per-run limit stops an item's fetches before they are done, the item keeps the context gathered so far, and this run's summary uses it. Podcast episodes and YouTube videos MUST NOT get linked or comment context.

#### Scenario: Short post with linked pages
- **WHEN** a pending website item links to its GitHub release, a project page, a changelog, and two of the site's tag pages
- **THEN** the release, project, and changelog pages are read as the item's context, and the tag pages are not fetched

#### Scenario: Author replies in comments
- **WHEN** the feed reports 12 comments on a post, and the post page marks 2 of them as written by the post's author
- **THEN** those 2 replies, each with the comment it answers, are kept as the item's context

#### Scenario: robots.txt disallows a linked page
- **WHEN** a linked page's site disallows CatchUp's User-Agent for that path
- **THEN** the page is not fetched, and the item is summarized without it

#### Scenario: robots.txt answers a server error
- **WHEN** a pending item links to two pages on a site whose robots.txt answers HTTP 503
- **THEN** robots.txt is requested once, neither page is fetched, the run succeeds, and the item is summarized without them

#### Scenario: robots.txt cannot be reached
- **WHEN** the request for a site's robots.txt times out, and the item also links to a page on another site whose robots.txt answers 404
- **THEN** no page of the first site is fetched in that run, and the page on the other site is read as context

#### Scenario: Link redirects to a disallowed page
- **WHEN** a linked page redirects to a page on another site, and that site's robots.txt disallows CatchUp's User-Agent for the target's path
- **THEN** the target is not requested, and the item is summarized without that page

#### Scenario: Link redirects to a site whose robots.txt cannot be read
- **WHEN** a linked page redirects to another site whose robots.txt answers HTTP 503, and the item has a second link on a third site
- **THEN** the target is not requested, and the second link is still read as context

#### Scenario: One site written three ways
- **WHEN** an item links to `https://SITE.example/a`, `https://site.example:443/b`, and `https://site.example/c`
- **THEN** that site's robots.txt is requested once in the run, and its rules apply to all three links

#### Scenario: robots.txt missing
- **WHEN** a site's robots.txt answers HTTP 404
- **THEN** that site's linked pages are read as context

#### Scenario: Per-run fetch limit reached
- **WHEN** a run's items have more related links than the per-run limit allows
- **THEN** context fetches stop at the limit, the run continues, and the remaining items are summarized from what was gathered

#### Scenario: Article links on the same site
- **WHEN** a pending item links to another article on its own site at `/archives/10000`
- **THEN** that article is read as context

#### Scenario: Link redirects to a login page
- **WHEN** a related link redirects to a login page
- **THEN** the login page is not stored as context

#### Scenario: Context gathered once
- **WHEN** an item's context was gathered in a run that then failed, and the user starts a new run
- **THEN** the stored context is reused, and the linked pages are not fetched again
