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
The web interface SHALL provide a web app manifest with the name CatchUp, a start URL of `/`, a standalone display mode, theme colors, and icons at 192 px, 512 px, and 512 px maskable. It SHALL also provide a 1024 px icon for Safari. The page SHALL declare the app icon for the browser tab, as an SVG with a 192 px PNG fallback, so the tab does not show a default icon. The tab icon MUST stay legible at small sizes: drawn at 16 × 16 or 32 × 32 pixels, it MUST use only the mark's two colors, and its two bars MUST be separate lines of whole pixels, one pixel high at 16 × 16. The 192 px, 512 px, and 1024 px icons SHALL show the same mark as the SVG, so that each of them, averaged over a 16 × 16 grid of equal blocks, gives the same picture. A supporting browser MUST be able to install CatchUp from `http://localhost:8000` or `http://127.0.0.1:8000` into its own window. The manifest MUST be served with the `application/manifest+json` media type.

#### Scenario: Install from Chrome
- **WHEN** the user opens CatchUp at `http://localhost:8000` in Chrome
- **THEN** Chrome offers to install it, and the installed app opens in its own window

#### Scenario: Manifest served correctly
- **WHEN** a client requests `/manifest.webmanifest` from a running container
- **THEN** the response is 200 with the media type `application/manifest+json`

#### Scenario: Icon in the browser tab
- **WHEN** the user opens CatchUp in a browser tab
- **THEN** the tab shows the CatchUp icon instead of the browser's default icon

#### Scenario: Icon at 16 px
- **WHEN** the tab icon is drawn at 16 × 16 pixels
- **THEN** it uses only the mark's two colors, and its two bars are lines one pixel high with two pixels of the mark between them

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

### Requirement: Install from the README on a clean machine
A user who knows nothing about the project MUST be able to install and run CatchUp on a clean machine by following only the README, from source or with Docker.
- **Minimum versions.** The README MUST state minimum versions of Python and Node.js. At those versions, the dependency install, the backend, the frontend build, and both test suites must work, and the versions must match the project's own configuration. When distribution packages can be older than these versions, the README MUST say where else to get them. When the README relies on a tool to provide Python, the version that tool selects MUST be the version CI tests.
- **Frontend build.** The README MUST order the source steps so that a built frontend is served. That means building it before the backend starts, or restarting the backend afterwards.
- **Database path.** The README MUST name the source checkout's database file.
- **Docker source build.** The README MUST say how to get the files it needs. A source build MUST get a local image name and MUST NOT create or replace the published image's tag. Every Compose command the README documents for that setup MUST use the same local image.
- **Health address.** The README MUST name the health address and its answer.
- **Instance secret.** The documented commands MUST create `.env` readable only by its owner, and MUST NOT show the instance secret on screen. They MUST NOT replace an existing `.env`, and MUST NOT write an empty secret when the secret cannot be generated.

#### Scenario: Source checkout on the minimum versions
- **WHEN** a user installs the stated minimum Node.js version, has either the stated minimum Python or no suitable Python, and follows the README's source steps
- **THEN** the dependency install, the backend, the frontend build, the backend tests, and the frontend tests all succeed, and the backend runs on the Python version CI tests

#### Scenario: Built frontend is served
- **WHEN** a user builds the frontend and starts the backend in the order the README gives
- **THEN** opening the backend's address shows the web interface instead of a "not found" answer

#### Scenario: Source build keeps the published image name free
- **WHEN** a user builds the image from a checkout as the README describes
- **THEN** the image has a local name, the published image's tag is neither created nor changed, and later documented Compose commands keep using the local image

#### Scenario: Health address
- **WHEN** a user requests the health address that the README names
- **THEN** the answer is the one the README states

#### Scenario: Private instance secret
- **WHEN** a user creates `.env` with the README's commands
- **THEN** the file is readable only by its owner, the secret is not empty, and the secret is not printed

#### Scenario: Secret is not replaced
- **WHEN** `.env` already exists, or the secret cannot be generated, and a user runs the README's secret commands
- **THEN** the commands stop with an error, and no `.env` with a new or empty secret is written

### Requirement: Back up and restore the data volume
The README MUST give separate commands to back up and to restore a Compose installation's data volume, and each MUST work on its own, in a new shell.
- **Backup.** The backup MUST be written outside the checkout and be readable only by its owner. A backup, including one that fails, MUST NOT overwrite or damage an earlier backup.
- **Restore.** Restoring into an existing installation MUST include a command that empties the stopped service's volume first. Before emptying anything, the restore MUST check that the whole backup can be read and extracted. When any step fails, the restore MUST stop with an error and MUST NOT start the service on an emptied volume.
- **New machine.** The README MUST also give a way to restore a backup on a new machine into a new, empty volume. It MUST refuse to restore into a volume that already holds data.
- **Where and when.** Run outside the installation directory, including from a subdirectory of the checkout, the backup and restore commands MUST stop with an error before they stop, empty, or write anything, and MUST NOT switch the installation to another image. The backup and restore MUST keep working after an upgrade or rebuild that the README documents.

#### Scenario: Restore in a new shell
- **WHEN** a user runs only the README's restore commands, in a new shell, for a stopped service, using a backup made with the README's backup commands
- **THEN** after the service starts again, the data from the backup is back and no data from after the backup remains

#### Scenario: Restore on a new machine
- **WHEN** a user has the backup file, the same `.env`, and the files the README's install path needs, on a machine with no CatchUp volume, and follows the README's new-machine restore commands
- **THEN** a new volume is created, the backup is restored into it, and CatchUp starts with the old data

#### Scenario: Private backup outside the checkout
- **WHEN** a user makes a backup with the README's commands
- **THEN** the backup file is outside the checkout and readable only by its owner

#### Scenario: Failed backup keeps earlier backups
- **WHEN** a user runs the README's backup commands and they fail, or succeed after earlier backups were made
- **THEN** every earlier backup file is unchanged

#### Scenario: Unreadable backup leaves the installation unchanged
- **WHEN** a user runs the README's restore commands with a backup that is missing, empty, or damaged
- **THEN** the commands stop with an error before emptying the volume, and the data in the volume is unchanged

#### Scenario: Backup after a rebuild
- **WHEN** a user upgrades or rebuilds a source build as the README describes, including a rebuild with no source changes, and then runs the README's backup commands
- **THEN** a new backup is written, and CatchUp runs again afterwards

#### Scenario: Commands outside the installation directory
- **WHEN** a user runs the README's backup or restore commands from another directory, including a subdirectory of the checkout
- **THEN** the commands stop with an error before anything is stopped or changed, and the service keeps running from the same image
