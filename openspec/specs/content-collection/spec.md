# content-collection Specification

## Purpose
Defines how CatchUp checks sources, decides what is new since each source's last successful check, and reports each check's outcome, so digests never repeat items or silently miss them.

## Requirements

### Requirement: Check every source on each run
Each digest run SHALL check every saved source once, except the built-in source for pages saved from the browser, which has no feed. It SHALL record for each checked source one outcome:
- `new_items`: the run includes at least one item from this source, either summarized or under Creator updates. It does not matter whether the entry was first seen in this check, recorded when the source was added, or held from an earlier run.
- `no_new_items`: the feed was fetched and parsed successfully, and the run includes nothing from this source.
- `failed`: the feed could not be fetched or parsed, with an error description.

Items held for a transcript or captions, items deferred to a later run, and entries recorded as already seen (such as skipped Shorts) MUST NOT make the outcome `new_items`. While sources are being checked, a successful check's outcome SHALL reflect what the check itself found. The outcome MUST become final once the run has chosen the items it includes, before any item is summarized. A failed check MUST never be reported as `no_new_items`.

#### Scenario: Source unreachable
- **WHEN** a source cannot be fetched or its feed cannot be parsed during a run
- **THEN** that source's outcome is `failed` with an error description, and other sources are still checked

#### Scenario: Nothing new
- **WHEN** a source's feed contains only entries already recorded, and none of the source's items is waiting to be delivered
- **THEN** that source's outcome is `no_new_items`

#### Scenario: First run after adding a source
- **WHEN** a source was added with 2 recent entries marked new, and its feed has not changed since
- **THEN** the next run includes the 2 entries, and that source's outcome is `new_items`

#### Scenario: Item carried over from a failed run
- **WHEN** a run fails after collecting an item, and the next run finds nothing new in that item's feed
- **THEN** the next run includes the item, and that source's outcome is `new_items`

#### Scenario: Episode held for its transcript
- **WHEN** a podcast's only new episode is still waiting for its transcript
- **THEN** that source's outcome is `no_new_items`, and the run reports the episode as waiting

#### Scenario: Skipped Short
- **WHEN** a YouTube channel's only new entry is a Short that is skipped
- **THEN** that source's outcome is `no_new_items`

#### Scenario: Only saved pages are waiting
- **WHEN** a run starts while pages saved from the browser are waiting
- **THEN** the run includes them, records no check for the built-in source, and does not count it among the sources checked

### Requirement: Record entries the first time they are seen
The system SHALL identify each entry within a source by a stable key: the entry's feed identifier, else its link, else a hash of its title and date. An entry is new only the first time its key is seen for that source. An entry whose key is unknown but whose link matches an already recorded entry of the same source MUST be treated as already seen. Publish dates MUST NOT decide whether an entry is new. A link that more than one entry of the same feed document carries (for example, every episode linking to the show's home page) MUST NOT be used to identify, deduplicate, or match entries. An entry without a feed identifier whose link is shared in this way is identified by the hash of its title and date.

#### Scenario: Repeated entries
- **WHEN** a feed still lists entries that were recorded on an earlier run
- **THEN** those entries are not recorded again and do not appear in the next digest again

#### Scenario: Late entry with an old publish date
- **WHEN** an entry appears in a feed for the first time with a publish date older than the source's last successful check
- **THEN** the entry is recorded as new

#### Scenario: Site changes an entry identifier
- **WHEN** a feed lists an entry with a new identifier but the same link as a recorded entry
- **THEN** no duplicate entry is recorded

#### Scenario: Episodes share the show's link
- **WHEN** a podcast feed lists 3 episodes with different identifiers whose links are all the show's home page, and one of them was recorded earlier
- **THEN** the other 2 episodes are recorded as new

### Requirement: Recover content after failed checks
Because newness is decided by first sight rather than by time, entries published while a source's checks were failing SHALL be collected on its next successful check, as long as they are still listed in the feed.

#### Scenario: Failure then success
- **WHEN** a source fails on one run and on the next run its feed lists two entries never seen before
- **THEN** both entries are recorded as new on that next run

### Requirement: Flag possible gaps
When a successful check of a source that already has recorded entries finds none of its previously recorded keys or links in the feed, the system SHALL flag that check as a possible gap. A possible gap means older entries may have dropped off the feed between checks.

#### Scenario: All entries unseen
- **WHEN** a source with recorded entries is checked and every entry in its feed is new
- **THEN** the check outcome carries a possible-gap flag that the user can see

### Requirement: Readable titles for untitled entries
When a feed entry has no title, the system SHALL use the beginning of the entry's text (at most 80 characters) as its title. When the text is cut, the title MUST end with exactly one ellipsis: dots and ellipsis characters at the end of the cut text, including the CJK full stop "。", the fullwidth dot "．", and "⋯", are removed before the ellipsis is added. If that would leave no text, the text is cut at 80 characters instead of at a word boundary. It SHALL show "Untitled" only when the entry has neither title nor text.

#### Scenario: Social post without a title
- **WHEN** a feed entry has no title and its text begins "Happy opening day, hockey fans! Follow all 1,344 games…"
- **THEN** the entry's title shown in previews and digests starts with "Happy opening day, hockey fans!"

#### Scenario: Cut text that already ends in dots
- **WHEN** a feed entry has no title, and its text is longer than 80 characters with "..." at the point where it is cut
- **THEN** the derived title ends with a single "…", not "...…"

#### Scenario: Cut CJK text that ends in full stops
- **WHEN** a feed entry has no title, and its Chinese text is longer than 80 characters with "。。。" at the point where it is cut
- **THEN** the derived title ends with a single "…"

### Requirement: Keep article text for summarization
For each new entry of a website feed, the system SHALL keep the text the feed provides. When that text is very short, the system SHALL try to fetch the linked article through the safe fetcher and extract its main text, and fall back to the feed text if extraction fails. The extracted text SHALL replace the feed text only when it covers the feed text, that is, when most of the feed text's words appear in it. Otherwise the stored text MUST begin with the feed text, followed by the extracted text, so that the feed's own words are never lost. Podcast episodes (entries of a podcast source that carry an audio enclosure) and YouTube videos MUST NOT be summarized from their show notes, descriptions, or linked pages. Their text for summarization comes only from a transcript (see the `transcripts` capability).

#### Scenario: Feed provides only a short excerpt
- **WHEN** a new entry's feed text is shorter than the configured threshold, the article page is reachable, and the extracted text contains the excerpt
- **THEN** the stored text for summarization is the extracted article text

#### Scenario: Extraction misses the post
- **WHEN** a new entry's feed text is shorter than the configured threshold, and the text extracted from its page does not contain most of the feed text's words, such as a sidebar listing other posts
- **THEN** the stored text begins with the feed text, followed by the extracted text

#### Scenario: Entry without feed text
- **WHEN** a new entry has no feed text and its article page is reachable
- **THEN** the stored text for summarization is the extracted article text

#### Scenario: Podcast episode with short show notes
- **WHEN** a new podcast episode has short show notes and no transcript
- **THEN** the system does not fetch the episode's web page, and the episode is not summarized from its show notes

### Requirement: Identify rate-limited checks
A check that fails because the source rate limited CatchUp SHALL be recorded as `failed`, with the HTTP status and the suggested wait when known. It MUST be shown to the user as "rate limited", distinct from other failures, in the source list and in run progress.

#### Scenario: Rate limited during a run
- **WHEN** a source answers 429 during a digest run and the wait is too long to retry
- **THEN** its check is `failed` with HTTP status 429, and the run progress and source list show it as rate limited

### Requirement: Space requests to the same host during a run
During a digest run, the system SHALL keep at least 1 second between consecutive requests to the same host. This covers feed checks and article fetches.

#### Scenario: Two sources on one host
- **WHEN** a run checks two sources whose feeds are on the same host
- **THEN** the second request to that host starts at least 1 second after the first

#### Scenario: Different hosts
- **WHEN** a run checks two sources on different hosts
- **THEN** no spacing delay is added between them

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

Every context fetch MUST go through the safe fetcher with the run's host spacing. It MUST honor the site's robots.txt for CatchUp's User-Agent, and MUST count against a per-run limit (default 60). A context fetch that fails, is refused, or exceeds the limit MUST be skipped without failing the source check or the run. Gathered context SHALL be stored with the item and reused by later runs. When the per-run limit stops an item's fetches before they are done, the item keeps the context gathered so far, and this run's summary uses it. Podcast episodes and YouTube videos MUST NOT get linked or comment context.

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

#### Scenario: Article links on the same site
- **WHEN** a pending item links to another article on its own site at `/archives/10000`
- **THEN** that article is read as context

#### Scenario: Link redirects to a login page
- **WHEN** a related link redirects to a login page
- **THEN** the login page is not stored as context

#### Scenario: Context gathered once
- **WHEN** an item's context was gathered in a run that then failed, and the user starts a new run
- **THEN** the stored context is reused, and the linked pages are not fetched again

### Requirement: Keep image candidates for items
For each entry of a website feed, and for each YouTube video, the system SHALL keep up to 8 image candidates in the order they appear: images in the entry's HTML, with their alt text and figure caption; image `media:content`; `media:thumbnail`; and image enclosures. Only `http` and `https` images are kept. Avatars, site icons, channel images, `data:` URLs, and 1×1 images MUST NOT be kept. Podcast cover art MUST NOT be kept. Keeping candidates MUST NOT fetch any image.

#### Scenario: Post with screenshots
- **WHEN** a website entry's HTML contains two screenshots with alt text and a figure caption
- **THEN** both are kept as candidates in order, with their alt text and caption

#### Scenario: Author avatar in the feed
- **WHEN** a WordPress feed item's `media:content` holds the author's Gravatar avatar and one post image
- **THEN** only the post image is kept

### Requirement: Gather context for pages saved from the browser
For a page saved from the browser, the system SHALL gather related context in the same pass as for website items:
- **Linked pages:** from the links the page recorded, under the same rules for related links. "The same site" means the saved page's own site.
- **Author replies:** the replies the extension read, kept as the page's author replies.

The system MUST NOT fetch the saved page's own address, which may need a login.

#### Scenario: Saved page linking an article
- **WHEN** a saved X post recorded the full address of a public article
- **THEN** the next run reads the article as related context for the post

#### Scenario: Saved page never fetched
- **WHEN** a run gathers context for a saved page
- **THEN** no request is sent to the saved page's own address
