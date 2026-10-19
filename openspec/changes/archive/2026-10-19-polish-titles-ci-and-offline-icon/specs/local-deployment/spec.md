## MODIFIED Requirements

### Requirement: Offline page when the server is not running
After the app has been opened once, opening it while the CatchUp server cannot be reached SHALL show an offline page. The page explains that CatchUp is not running, shows how to start it (`docker compose up -d`, or `uv run catchup serve` from a source checkout), and offers a reload. The page MUST show the CatchUp icon in the browser tab without a network request. The service worker MUST NOT cache application code or API responses, so a running server always serves the current version.

#### Scenario: Server stopped
- **WHEN** the user opens the installed app while the CatchUp container is stopped
- **THEN** the offline page is shown instead of a browser error

#### Scenario: Offline tab icon
- **WHEN** the offline page is shown
- **THEN** its browser tab shows the CatchUp icon, which is declared inline in the page

#### Scenario: Server back
- **WHEN** the server is started again and the user reloads
- **THEN** the current version of the app loads, and no cached API data is shown
