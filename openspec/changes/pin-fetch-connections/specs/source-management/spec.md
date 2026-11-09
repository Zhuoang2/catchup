## MODIFIED Requirements

### Requirement: Fetch user-supplied URLs safely
The system MUST refuse to fetch URLs whose host resolves to private, loopback, link-local, or cloud-metadata addresses, including when such an address is reached through a redirect. The system MUST connect only to an address that passed this check, so a host whose DNS answer changes after the check (DNS rebinding) cannot reach such an address. Connecting to the checked address MUST NOT change how the request names the host: HTTPS certificates are still verified for the URL's host name, and the request still names that host. Fetches MUST time out and MUST stop reading responses above a size limit. Feed documents SHALL use their own configurable limit (default 32 MB). All other responses, such as article pages and transcripts, SHALL use a 5 MB limit.

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
