# Spec Delta

## MODIFIED Requirements

### Requirement: Preview a source from a pasted URL
The system SHALL accept a pasted URL and identify an RSS or Atom feed for it:
- If the URL is itself a feed, the system uses it.
- If the URL is an Apple Podcasts show or episode page, the system looks up the show's feed URL through Apple's public lookup service.
- If the URL is an HTML page, the system looks for a feed the page declares. If the page declares none, the system tries a bounded list of common feed locations on the same site.
- If the pasted page itself answers an HTTP error, the system still tries the same bounded list of common feed locations on the same site. A timeout, an unresolvable host, a blocked address, or a rate limit stops the search as before.
- If the URL is an X account address, the system previews that X account through the X API instead, as the `x-accounts` capability describes, and requests nothing from x.com or twitter.com.
- If the URL is on a Bilibili host, or is the configured RSSHub's address for a Bilibili uploader, the system previews that uploader through RSSHub instead, as the `bilibili-uploaders` capability describes, and requests nothing from Bilibili.

The preview MUST show:
- the feed's title, the feed URL, and the site URL; for a Bilibili uploader, its name and space address, without a feed URL
- whether the source is a website feed, a podcast, a YouTube channel, an X account, or a Bilibili uploader, and for podcasts, YouTube channels, and Bilibili uploaders how transcripts or subtitles will be obtained
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

#### Scenario: Pasting a Bilibili space URL
- **WHEN** RSSHub is configured and the user pastes `https://space.bilibili.com/2267573`
- **THEN** the system previews the uploader through RSSHub as a Bilibili uploader, without looking for a feed and without requesting bilibili.com

### Requirement: Fetch user-supplied URLs safely
The system MUST refuse to fetch URLs whose host resolves to private, loopback, link-local, or cloud-metadata addresses, including when such an address is reached through a redirect. The system MUST connect only to an address that passed this check, so a host whose DNS answer changes after the check (DNS rebinding) cannot reach such an address. Connecting to the checked address MUST NOT change how the request names the host: HTTPS certificates are still verified for the URL's host name, and the request still names that host. The only exception is the RSSHub origin the instance configures for Bilibili uploaders: requests for an uploader to exactly that origin are allowed to reach a private or loopback address, and nothing they redirect to is, as the `bilibili-uploaders` capability describes. Fetches MUST time out and MUST stop reading responses above a size limit. Feed documents SHALL use their own configurable limit (default 32 MB). All other responses, such as article pages and transcripts, SHALL use a 5 MB limit.

#### Scenario: Internal address
- **WHEN** the user pastes a URL whose host resolves to a loopback or private network address
- **THEN** the system refuses to fetch it and reports that the address is not allowed

#### Scenario: Redirect to an internal address
- **WHEN** a public URL redirects to a cloud-metadata or private address
- **THEN** the system stops at the redirect and reports that the address is not allowed

#### Scenario: DNS answer changes after the check
- **WHEN** a host first resolves to a public address and then, when the connection is opened, to a loopback or private address
- **THEN** the system does not connect to that address and reports that the address is not allowed

#### Scenario: Slow or oversized response
- **WHEN** a server does not respond within the timeout or sends more than the size limit
- **THEN** the fetch fails with a timeout or size error instead of hanging

#### Scenario: Large podcast feed
- **WHEN** a feed document is 6 MB and the feed limit is the default 32 MB
- **THEN** the feed is fetched and previewed, while a 6 MB article page or transcript still fails with a size error

#### Scenario: Confirm a large feed after the preview expired
- **WHEN** the user confirms a 6 MB podcast feed after its preview is no longer reusable
- **THEN** the feed is fetched again with the feed limit and the source is saved

#### Scenario: Pasting the RSSHub address for another route
- **WHEN** RSSHub is configured at `http://localhost:1200`, and the user pastes `http://localhost:1200/github/repos/example`
- **THEN** the system refuses it as an address that is not allowed, because only Bilibili uploader requests are allowed to reach the configured origin's private address
