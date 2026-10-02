# Spec Delta

## Purpose

Lets the user add the websites and feeds they follow by pasting a URL, confirm what CatchUp identified before saving, and manage their saved sources safely.

## ADDED Requirements

### Requirement: Preview a source from a pasted URL
The system SHALL accept a pasted URL and identify an RSS or Atom feed for it. If the URL is itself a feed, the system uses it. If the URL is an HTML page, the system looks for a feed the page declares. The preview MUST show the feed's title, the feed URL, the site URL, and up to five recent entries (title, link, and publish date when available). Previewing MUST NOT save anything.

#### Scenario: Pasting a feed URL
- **WHEN** the user pastes the URL of a valid RSS or Atom feed
- **THEN** the system shows a preview with the feed title, feed URL, and recent entries

#### Scenario: Pasting a website URL that declares a feed
- **WHEN** the user pastes the URL of an HTML page that declares an RSS or Atom feed
- **THEN** the system previews that declared feed

#### Scenario: Pasting a single article URL
- **WHEN** the pasted page is an individual article on a site that declares a feed
- **THEN** the preview states that CatchUp will follow the site's feed, not only that article

### Requirement: Explain unsupported and duplicate sources
The system SHALL tell the user why a URL cannot be added: it is not a valid URL, it could not be fetched, no feed was found, the content is not a parsable feed, it targets a blocked address, or a source with the same feed URL already exists.

#### Scenario: No feed found
- **WHEN** the pasted page declares no feed and is not a feed itself
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
The system MUST refuse to fetch URLs whose host resolves to private, loopback, link-local, or cloud-metadata addresses, including when such an address is reached through a redirect. Fetches MUST time out and MUST stop reading responses above a size limit.

#### Scenario: Internal address
- **WHEN** the user pastes a URL whose host resolves to a loopback or private network address
- **THEN** the system refuses to fetch it and reports that the address is not allowed

#### Scenario: Redirect to an internal address
- **WHEN** a public URL redirects to a cloud-metadata or private address
- **THEN** the system stops at the redirect and reports that the address is not allowed

#### Scenario: Slow or oversized response
- **WHEN** a server does not respond within the timeout or sends more than the size limit
- **THEN** the fetch fails with a timeout or size error instead of hanging
