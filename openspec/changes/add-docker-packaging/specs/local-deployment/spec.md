# Spec Delta

## Purpose

Lets users run CatchUp on their own machine from a published container image with one command, with data that survives restarts and upgrades and an instance that is reachable only locally by default.

## ADDED Requirements

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
