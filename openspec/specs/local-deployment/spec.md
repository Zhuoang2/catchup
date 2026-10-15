# local-deployment Specification

## Purpose
Lets users run CatchUp on their own machine from a published container image with one command, with data that survives restarts and upgrades and an instance that is reachable only locally by default.

## Requirements

### Requirement: Start from a published image with one command
The project SHALL provide a container image and a compose file so that a user with Docker can start CatchUp with a single command, with no Python, uv, or Node installation. The running instance MUST serve both the API and the web interface on one port.

#### Scenario: Start with compose
- **WHEN** the user runs the documented compose command in a directory with the compose file and an environment file
- **THEN** CatchUp starts, and opening `http://localhost:8000` shows the web interface

#### Scenario: Images for common machines
- **WHEN** a release image is published
- **THEN** it is available for both `linux/amd64` and `linux/arm64`

### Requirement: Data persists across restarts and upgrades
All instance data SHALL be stored on a persistent volume, separate from the image. Restarting or replacing the container with a newer image MUST keep sources, digests, and settings, and a newer image MUST apply its database migrations automatically on start.

#### Scenario: Restart
- **WHEN** the user saves a setting and then restarts the container
- **THEN** the setting is still present after the restart

#### Scenario: Upgrade to a newer image
- **WHEN** the user starts a newer image with the same data volume
- **THEN** existing data is kept and any new migrations are applied before requests are served

### Requirement: Local-only access by default
The provided compose configuration MUST publish the CatchUp port only on the loopback interface, so a default installation is not reachable from other machines. The documentation MUST explain that the instance has no login and what to change, with that risk stated, to expose it.

#### Scenario: Default compose installation
- **WHEN** CatchUp is started with the provided compose file
- **THEN** the port is bound to `127.0.0.1` only

### Requirement: Run without root privileges
The container process SHALL run as a non-root user, and the data volume MUST be writable by that user.

#### Scenario: Process user
- **WHEN** the container is running
- **THEN** the CatchUp process user id is not 0 and it can create the database on the data volume

### Requirement: Report health
The image SHALL define a health check based on the application's health endpoint, so container tools report whether CatchUp is ready.

#### Scenario: Healthy after start
- **WHEN** CatchUp has started and finished its migrations
- **THEN** the container's health status becomes healthy

### Requirement: Package independent of the source tree
The installed backend package SHALL include its database migrations, and the location of the web interface build MUST be configurable. CatchUp MUST run correctly when installed outside the source repository. A source checkout MUST keep working without extra configuration.

#### Scenario: Installed outside the repository
- **WHEN** the backend is installed as a non-editable package and the frontend build location is configured
- **THEN** startup applies migrations and serves the web interface

#### Scenario: Running from a source checkout
- **WHEN** a developer runs CatchUp from the repository without setting the frontend location
- **THEN** it serves the frontend build from the repository as before

### Requirement: Keep local secrets out of the image
Building the image MUST NOT include local environment files, data directories, dependency folders, or files outside the backend and frontend sources in the build context.

#### Scenario: Environment file present
- **WHEN** an image is built from a working copy that contains a `.env` file and a `data/` directory
- **THEN** neither the `.env` file nor the `data/` contents are present in the image

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
