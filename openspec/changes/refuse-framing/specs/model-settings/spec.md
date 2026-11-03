## ADDED Requirements

### Requirement: Refuse to be shown inside other sites' pages
Every response from CatchUp's server MUST tell the browser not to show it inside a frame, with both `X-Frame-Options: DENY` and `Content-Security-Policy: frame-ancestors 'none'`. This covers:
- CatchUp's pages and the files they load, including the offline page, the service worker, and the manifest;
- API responses;
- error responses, including refused requests and internal errors.

A page on another site, or on another local port, therefore cannot show CatchUp inside its own page, and cannot trick the user into clicking CatchUp's controls there. Those clicks would otherwise be accepted as coming from CatchUp's own pages. The policy MUST restrict only framing. Pages, the installed app, the offline page, and the browser extension MUST work as before, and each response MUST keep its status, content type, and body.

#### Scenario: Another site frames CatchUp
- **WHEN** a page on another site embeds CatchUp's address in a frame
- **THEN** the browser does not show CatchUp in that frame, so no click on that page reaches CatchUp's controls

#### Scenario: Pages and files
- **WHEN** a browser requests `/`, a client route such as `/digests/3`, `/offline.html`, `/sw.js`, `/manifest.webmanifest`, or a file under `/assets/`
- **THEN** each response carries both headers, with the same status, content type, and body as before

#### Scenario: API and error responses
- **WHEN** a client requests an API address, an unknown API address, or an address under a host that is not allowed, or sends a write that is refused as cross-site, or a request that fails with an internal error
- **THEN** each response carries both headers, with the same status and body as before

#### Scenario: Installed app and offline page
- **WHEN** the user opens the installed app, and later opens it while CatchUp is not running
- **THEN** the app opens as before, and the offline page is shown as before
