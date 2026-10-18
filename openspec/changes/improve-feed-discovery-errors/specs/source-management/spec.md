## MODIFIED Requirements

### Requirement: Preview a source from a pasted URL
The system SHALL accept a pasted URL and identify an RSS or Atom feed for it:
- If the URL is itself a feed, the system uses it.
- If the URL is an Apple Podcasts show or episode page, the system looks up the show's feed URL through Apple's public lookup service.
- If the URL is an HTML page, the system looks for a feed the page declares. If the page declares none, the system tries a bounded list of common feed locations on the same site.
- If the pasted page itself answers an HTTP error, the system still tries the same bounded list of common feed locations on the same site. A timeout, an unresolvable host, a blocked address, or a rate limit stops the search as before.

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

#### Scenario: Page refused but feed available
- **WHEN** the pasted site's home page answers HTTP 403, and a feed exists at `/feed` on the same site
- **THEN** the system finds and previews that feed

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
The system SHALL tell the user why a URL cannot be added:
- it is not a valid URL
- it could not be fetched
- no feed was found
- the site's feed is temporarily unavailable
- the content is not a parsable feed
- it targets a blocked address
- a source with the same feed URL already exists

When a fetch fails with an HTTP error, the message MUST name the HTTP status:
- For a refused request (401 or 403), it MUST suggest pasting the site's feed URL.
- For a missing page (404 or 410), it MUST suggest checking the URL or pasting the feed URL.
- For a server error (5xx), it MUST suggest trying again later.

A feed that answered an HTTP error MUST be reported as temporarily unavailable, not as a feed that could not be parsed. "Not a parsable feed" MUST be reserved for content that was fetched but could not be parsed.

#### Scenario: No feed found
- **WHEN** the pasted page declares no feed, is not a feed itself, and none of the common feed locations returns a feed
- **THEN** the system reports that no supported feed was found at that URL

#### Scenario: Page refused and no feed found
- **WHEN** the pasted page answers HTTP 403, and none of the common feed locations on the same site returns a feed
- **THEN** the system reports that the site refused the request (HTTP 403), and suggests pasting the site's feed URL

#### Scenario: Declared feed unavailable
- **WHEN** the pasted page declares a feed, and fetching that feed answers HTTP 404
- **THEN** the system reports that the site's feed is temporarily unavailable (HTTP 404), and does not say that the feed could not be parsed

#### Scenario: Duplicate source
- **WHEN** the identified feed URL matches an already saved source
- **THEN** the system reports the duplicate and names the existing source
