# Spec Delta

## ADDED Requirements

### Requirement: Choose how many linked pages a run reads
The system SHALL let the user choose a linked-page level, stored with the Digest settings: Off, Shallow, or Normal. Normal MUST be the level when none was saved, including on instances upgraded from a version without the choice. A run MUST read the level once, when it starts: a change saved during the run applies to the next run.
- **Normal** reads up to `CATCHUP_LINKS_PER_ITEM` related links per item (default 8), and author replies, as "Gather related context for website items" describes.
- **Shallow** reads up to 3 related links per item, or `CATCHUP_LINKS_PER_ITEM` links when that setting is lower, and author replies.
- **Off** MUST NOT make any context request: no linked page, post page, comment feed, or robots.txt. Replies saved with a page from the browser, and replies kept from a followed X account's thread, need no request: they MUST still be kept as the item's author replies. Every other pending item MUST stay not gathered, so that a later run that still finds it pending gathers its context at the level that run uses.

At Shallow and Normal, the per-run limit (`CATCHUP_CONTEXT_FETCHES_PER_RUN`, default 60), the cut of each page's text to 3,000 characters, the 16,000-character cap per item, robots.txt, and the `CATCHUP_AUTHOR_REPLIES` switch apply unchanged. The level applies in the same way to website items, podcast text posts, pages saved from the browser, and posts from followed X accounts. An item whose context was gathered in an earlier run keeps that context when the level changes.

#### Scenario: Shallow reads three links
- **WHEN** the level is Shallow, and a pending item links to five related pages, each on a site of its own whose robots.txt allows them
- **THEN** the run requests the first three pages in body order, with their sites' robots.txt, and never requests the other two

#### Scenario: Shallow under a lower server setting
- **WHEN** `CATCHUP_LINKS_PER_ITEM` is 2, the level is Shallow, and a pending item links to three related pages
- **THEN** the run reads the first two pages

#### Scenario: Normal follows the server setting
- **WHEN** `CATCHUP_LINKS_PER_ITEM` is 5, the level is Normal, and a pending item links to six related pages
- **THEN** the run reads the first five pages

#### Scenario: Off makes no request
- **WHEN** the level is Off, and a pending website item links to two related pages and the feed reports comments on it
- **THEN** the run sends no context request, including robots.txt, its linked-page total is 0, the run succeeds, and the item is summarized without context

#### Scenario: Off keeps saved replies
- **WHEN** the level is Off, and a page saved from the browser has two replies the extension read and links to an article
- **THEN** the page gets an author-replies part with both replies, and the article is not requested

#### Scenario: Item left by Off is read later
- **WHEN** a run at Off fails after its context pass, the user then chooses Normal, and starts a new run in which the item is still pending
- **THEN** the new run reads the item's related linked pages

#### Scenario: Level changed during a run
- **WHEN** the level is Off when a run starts, and the user saves Normal while the run checks its sources
- **THEN** that run sends no context request, and the next run reads linked pages at Normal

#### Scenario: No level saved
- **WHEN** an instance upgraded from a version without the choice starts a run
- **THEN** the run reads linked pages and author replies exactly as at Normal

## MODIFIED Requirements

### Requirement: Gather related context for website items
For each entry of a website feed, the system SHALL keep the entry's links in body order with their anchor text, and its comment pointers when the feed provides them: the comments URL, the comment feed URL, the comment count, and the entry author. Once per run, after every source is checked and before the run chooses its items, the system SHALL gather context for each pending website item that has none yet, at the linked-page level the run uses ("Choose how many linked pages a run reads"):
- **Related links.** At most the level's number of links per item (8 at Normal by default), in body order. These are excluded:
  - links to the item itself;
  - same-site tag, category, archive, author, page, and search pages;
  - login-scoped or share pages;
  - image and PDF links;
  - video watch pages;
  - `mailto:` and `javascript:` links;
  - x.com and twitter.com.

  A link counts as same-site when its host equals the site's host, ignoring a leading `www.`. The same rules apply to a page's final URL after redirects.

  Each linked page's extracted text MUST be cut to 3,000 characters, and an item's linked context MUST stay within 16,000 characters.
- **Author replies.** At every level except Off, when the feed reports comments on the post, the author's own replies are read from the post page, each with the comment it answers, including when the theme lists replies after the comment they answer rather than inside it. At most 10 replies and 4,000 characters are kept. When the page shows none, the post's comment feed is used.

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
