# source-management Specification

## Purpose
Lets the user add the websites and feeds they follow by pasting a URL, confirm what CatchUp identified before saving, and manage their saved sources safely.

## Requirements

### Requirement: Preview a source from a pasted URL
The system SHALL accept a pasted URL and identify an RSS or Atom feed for it:
- If the URL is itself a feed, the system uses it.
- If the URL is an Apple Podcasts show or episode page, the system looks up the show's feed URL through Apple's public lookup service.
- If the URL is an HTML page, the system looks for a feed the page declares. If the page declares none, the system tries a bounded list of common feed locations on the same site.

The preview MUST show:
- the feed's title, the feed URL, and the site URL
- whether the source is a website feed, a podcast, or a YouTube channel, and for podcasts and YouTube channels how transcripts will be obtained
- up to five recent entries (title, link, and publish date when available)

Previewing MUST NOT save anything.

#### Scenario: Pasting a feed URL
- **WHEN** the user pastes the URL of a valid RSS or Atom feed
- **THEN** the system shows a preview with the feed title, feed URL, and recent entries

#### Scenario: Pasting a website URL that declares a feed
- **WHEN** the user pastes the URL of an HTML page that declares an RSS or Atom feed
- **THEN** the system previews that declared feed

#### Scenario: Website exposes a feed without declaring it
- **WHEN** the pasted HTML page declares no feed, but a feed exists at a common location on the same site (such as the page URL with `.rss` appended, `/feed`, `/rss.xml`, or `/atom.xml`)
- **THEN** the system finds and previews that feed, and the preview shows the feed URL that was found

#### Scenario: Profile or section page with its own declared feed
- **WHEN** the pasted page is a profile or section page (not an article) that declares its own feed
- **THEN** the preview does not say that the whole site's feed will be followed

#### Scenario: Pasting a single article URL
- **WHEN** the pasted page is an individual article on a site that declares a feed
- **THEN** the preview states that CatchUp will follow the site's feed, not only that article

#### Scenario: Pasting an Apple Podcasts show URL
- **WHEN** the user pastes an Apple Podcasts show URL and Apple's lookup service returns a feed URL for the show
- **THEN** the system previews that podcast feed and marks the source as a podcast

#### Scenario: Pasting an Apple Podcasts episode URL
- **WHEN** the user pastes an Apple Podcasts episode URL
- **THEN** the system previews the show's feed and states that CatchUp will follow the whole show, not only that episode

#### Scenario: Apple Podcasts show without a feed
- **WHEN** Apple's lookup service returns no result or no feed URL for the pasted Apple Podcasts URL
- **THEN** the system reports that no supported feed was found at that URL

#### Scenario: Pasting a YouTube channel URL
- **WHEN** the user pastes a YouTube channel page that declares its channel feed
- **THEN** the preview marks the source as a YouTube channel and states whether captions will be fetched under the current setting

### Requirement: Explain unsupported and duplicate sources
The system SHALL tell the user why a URL cannot be added: it is not a valid URL, it could not be fetched, no feed was found, the content is not a parsable feed, it targets a blocked address, or a source with the same feed URL already exists.

#### Scenario: No feed found
- **WHEN** the pasted page declares no feed, is not a feed itself, and none of the common feed locations returns a feed
- **THEN** the system reports that no supported feed was found at that URL

#### Scenario: Duplicate source
- **WHEN** the identified feed URL matches an already saved source
- **THEN** the system reports the duplicate and names the existing source

### Requirement: Confirm and save a source
The system SHALL save a source only after the user confirms a preview. On saving, it MUST record the feed's current entries. Entries published within the last 7 days, up to the 5 most recent, MUST be marked as new for the next digest. All other current entries, including entries without a publish date, MUST be marked as existing so they never appear in a digest. Both limits are configurable instance settings.

#### Scenario: Confirm a feed with old and recent entries
- **WHEN** the user confirms a feed with 2 entries from the last 7 days and 10 older entries
- **THEN** the source is saved, the 2 recent entries will appear in the next digest, and the 10 older entries never will

#### Scenario: Confirm a feed with many recent entries
- **WHEN** the user confirms a feed with 8 entries from the last 7 days
- **THEN** only the 5 most recent of them are marked as new

### Requirement: List and delete sources
The system SHALL list saved sources with their title, feed URL, and the outcome and time of their most recent check. The system SHALL let the user delete a source. Deleting a source MUST NOT delete digests that were already saved.

#### Scenario: Delete a source
- **WHEN** the user deletes a source that appeared in earlier digests
- **THEN** the source no longer appears in the list and earlier digests still open with their items and links

### Requirement: Fetch user-supplied URLs safely
The system MUST refuse to fetch URLs whose host resolves to private, loopback, link-local, or cloud-metadata addresses, including when such an address is reached through a redirect. Fetches MUST time out and MUST stop reading responses above a size limit. Feed documents SHALL use their own configurable limit (default 32 MB). All other responses, such as article pages and transcripts, SHALL use a 5 MB limit.

#### Scenario: Internal address
- **WHEN** the user pastes a URL whose host resolves to a loopback or private network address
- **THEN** the system refuses to fetch it and reports that the address is not allowed

#### Scenario: Redirect to an internal address
- **WHEN** a public URL redirects to a cloud-metadata or private address
- **THEN** the system stops at the redirect and reports that the address is not allowed

#### Scenario: Slow or oversized response
- **WHEN** a server does not respond within the timeout or sends more than the size limit
- **THEN** the fetch fails with a timeout or size error instead of hanging

#### Scenario: Large podcast feed
- **WHEN** a feed document is 6 MB and the feed limit is the default 32 MB
- **THEN** the feed is fetched and previewed, while a 6 MB article page or transcript still fails with a size error

#### Scenario: Confirm a large feed after the preview expired
- **WHEN** the user confirms a 6 MB podcast feed after its preview is no longer reusable
- **THEN** the feed is fetched again with the feed limit and the source is saved

### Requirement: Identify CatchUp in outgoing requests
Every request CatchUp makes to a source SHALL carry a User-Agent that names CatchUp, its version, and the project URL. When the instance configures a contact, the User-Agent MUST include it.

#### Scenario: Default User-Agent
- **WHEN** CatchUp fetches a page, feed, or article with no contact configured
- **THEN** the request's User-Agent starts with `CatchUp/` and contains the project URL

#### Scenario: Configured contact
- **WHEN** the instance sets a contact such as `by /u/example`
- **THEN** the User-Agent of every request includes that contact

### Requirement: Honor rate limits when fetching
When a source responds with HTTP 429, or 503 with a `Retry-After` header, the system SHALL wait and retry once if the requested delay is at most 10 seconds and fits within the fetch deadline. Otherwise it MUST stop without retrying and report that the source is rate limited, including the suggested wait when the server provided one. Both `Retry-After` forms (seconds and HTTP date) MUST be understood.

#### Scenario: Short wait requested
- **WHEN** a source answers 429 with `Retry-After: 3` and then succeeds
- **THEN** the system waits about 3 seconds, retries once, and the fetch succeeds

#### Scenario: Long wait requested
- **WHEN** a source answers 429 with `Retry-After: 120`
- **THEN** the system does not wait, makes no further request to it, and reports the source as rate limited with a suggested wait of about 120 seconds

#### Scenario: No wait given
- **WHEN** a source answers 429 without a `Retry-After` header
- **THEN** the system does not retry and reports the source as rate limited

#### Scenario: Rate limited while adding a source
- **WHEN** a preview or confirm request is rate limited
- **THEN** the user sees a "rate limited, try again later" message that differs from other fetch errors

### Requirement: Reuse a recent preview on confirm
When the user confirms a source within 10 minutes of previewing it, the system SHALL use the feed content fetched during the preview instead of fetching the feed again. After that window, or when no preview content is available (e.g. after a restart), confirm MUST fetch the feed as before.

#### Scenario: Confirm right after preview
- **WHEN** the user previews a feed and confirms it a few seconds later
- **THEN** the source is saved without another request to the feed URL

#### Scenario: Confirm after the window
- **WHEN** the user confirms more than 10 minutes after the preview
- **THEN** the system fetches the feed again before saving
