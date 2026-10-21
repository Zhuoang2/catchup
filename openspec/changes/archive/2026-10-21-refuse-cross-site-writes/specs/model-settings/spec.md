## ADDED Requirements

### Requirement: Refuse write requests from other sites
The system MUST refuse any request that changes data or starts work (`POST`, `PUT`, `PATCH`, or `DELETE`) when a browser sent it from a page on another origin, and MUST perform none of the requested action. A request counts as coming from another origin when either holds:
- its `Origin` header is `null`, is not an http or https origin, or names a different host or port than its `Host` header;
- its `Sec-Fetch-Site` header is `cross-site` or `same-site`.

A page on another port of the same machine is another origin. Requests from CatchUp's own pages, and requests that carry neither header (such as command-line tools), are accepted as before. Read-only requests are not affected.

#### Scenario: Another site tries to start a digest run
- **WHEN** a page on another site submits a form to CatchUp's digest-run address, while a model is configured
- **THEN** the request is refused, and no digest run starts

#### Scenario: Another local app writes to CatchUp
- **WHEN** a page served from `http://localhost:3000` sends a request that changes CatchUp's settings on port 8000
- **THEN** the request is refused, and the settings are unchanged

#### Scenario: CatchUp's own pages
- **WHEN** the user saves settings, previews or deletes a source, or starts a run from CatchUp's own pages
- **THEN** the requests are accepted as before

#### Scenario: Command-line tools
- **WHEN** a request without `Origin` or `Sec-Fetch-Site` headers changes data, for an allowed host
- **THEN** it is accepted as before

#### Scenario: Deployed behind a domain
- **WHEN** CatchUp is served at `https://catchup.example.org` through a proxy that passes the browser's `Host` header, and that host is allowed
- **THEN** its own pages can save settings
