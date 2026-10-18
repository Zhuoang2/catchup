## MODIFIED Requirements

### Requirement: Installable as an app
The web interface SHALL provide a web app manifest with the name CatchUp, a start URL of `/`, a standalone display mode, theme colors, and icons at 192 px, 512 px, and 512 px maskable. It SHALL also provide a 1024 px icon for Safari. The page SHALL declare the app icon for the browser tab, as an SVG with a 192 px PNG fallback, so the tab does not show a default icon. A supporting browser MUST be able to install CatchUp from `http://localhost:8000` or `http://127.0.0.1:8000` into its own window. The manifest MUST be served with the `application/manifest+json` media type.

#### Scenario: Install from Chrome
- **WHEN** the user opens CatchUp at `http://localhost:8000` in Chrome
- **THEN** Chrome offers to install it, and the installed app opens in its own window

#### Scenario: Manifest served correctly
- **WHEN** a client requests `/manifest.webmanifest` from a running container
- **THEN** the response is 200 with the media type `application/manifest+json`

#### Scenario: Icon in the browser tab
- **WHEN** the user opens CatchUp in a browser tab
- **THEN** the tab shows the CatchUp icon instead of the browser's default icon
