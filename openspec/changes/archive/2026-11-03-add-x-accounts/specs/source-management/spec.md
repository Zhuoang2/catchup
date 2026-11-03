## MODIFIED Requirements

### Requirement: Preview a source from a pasted URL
The system SHALL accept a pasted URL and identify an RSS or Atom feed for it:
- If the URL is itself a feed, the system uses it.
- If the URL is an Apple Podcasts show or episode page, the system looks up the show's feed URL through Apple's public lookup service.
- If the URL is an HTML page, the system looks for a feed the page declares. If the page declares none, the system tries a bounded list of common feed locations on the same site.
- If the pasted page itself answers an HTTP error, the system still tries the same bounded list of common feed locations on the same site. A timeout, an unresolvable host, a blocked address, or a rate limit stops the search as before.
- If the URL is an X account address, the system previews that X account through the X API instead, as the `x-accounts` capability describes, and requests nothing from x.com or twitter.com.

The preview MUST show:
- the feed's title, the feed URL, and the site URL
- whether the source is a website feed, a podcast, a YouTube channel, or an X account, and for podcasts and YouTube channels how transcripts will be obtained
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

#### Scenario: Pasting an X profile URL
- **WHEN** the user pastes `https://x.com/simonw`
- **THEN** the system previews the X account `simonw` through the X API, without looking for a feed
