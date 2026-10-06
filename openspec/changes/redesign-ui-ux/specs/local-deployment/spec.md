# Spec Delta

## ADDED Requirements

### Requirement: Installable as an app
The web interface SHALL provide a web app manifest with the name CatchUp, a start URL of `/`, a standalone display mode, theme colors, and icons at 192 px, 512 px, and 512 px maskable. It SHALL also provide a 1024 px icon for Safari. A supporting browser MUST be able to install CatchUp from `http://localhost:8000` or `http://127.0.0.1:8000` into its own window. The manifest MUST be served with the `application/manifest+json` media type.

#### Scenario: Install from Chrome
- **WHEN** the user opens CatchUp at `http://localhost:8000` in Chrome
- **THEN** Chrome offers to install it, and the installed app opens in its own window

#### Scenario: Manifest served correctly
- **WHEN** a client requests `/manifest.webmanifest` from a running container
- **THEN** the response is 200 with the media type `application/manifest+json`

### Requirement: Offline page when the server is not running
After the app has been opened once, opening it while the CatchUp server cannot be reached SHALL show an offline page. The page explains that CatchUp is not running, shows how to start it (`docker compose up -d`, or `uv run catchup serve` from a source checkout), and offers a reload. The service worker MUST NOT cache application code or API responses, so a running server always serves the current version.

#### Scenario: Server stopped
- **WHEN** the user opens the installed app while the CatchUp container is stopped
- **THEN** the offline page is shown instead of a browser error

#### Scenario: Server back
- **WHEN** the server is started again and the user reloads
- **THEN** the current version of the app loads, and no cached API data is shown
