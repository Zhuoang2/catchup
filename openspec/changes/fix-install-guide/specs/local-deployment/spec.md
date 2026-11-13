## ADDED Requirements

### Requirement: Install from the README on a clean machine
A user who knows nothing about the project MUST be able to install and run CatchUp on a clean machine by following only the README, from source or with Docker.
- **Minimum versions.** The README MUST state minimum versions of Python and Node.js. At those versions, the dependency install, the backend, the frontend build, and both test suites must work, and the versions must match the project's own configuration. When distribution packages can be older than these versions, the README MUST say where else to get them.
- **Frontend build.** The README MUST order the source steps so that a built frontend is served. That means building it before the backend starts, or restarting the backend afterwards.
- **Database path.** The README MUST name the source checkout's database file.
- **Docker source build.** The README MUST say how to get the files it needs. A source build MUST get a local image name and MUST NOT create or replace the published image's tag. Every Compose command the README documents for that setup MUST use the same local image.
- **Health address.** The README MUST name the health address and its answer.
- **Instance secret.** The documented commands MUST create `.env` readable only by its owner, and MUST NOT show the instance secret on screen.

#### Scenario: Source checkout on the minimum versions
- **WHEN** a user installs the stated minimum Python and Node.js versions and follows the README's source steps
- **THEN** the dependency install, the backend, the frontend build, the backend tests, and the frontend tests all succeed

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
- **THEN** the file is readable only by its owner and the secret is not printed

### Requirement: Back up and restore the data volume
The README MUST give separate commands to back up and to restore a Compose installation's data volume, and each MUST work on its own, in a new shell.
- **Backup.** The backup MUST be written outside the checkout and be readable only by its owner.
- **Restore.** Restoring into an existing installation MUST include a command that empties the stopped service's volume first.
- **New machine.** The README MUST also give a way to restore a backup on a new machine into a new, empty volume.

#### Scenario: Restore in a new shell
- **WHEN** a user runs only the README's restore commands, in a new shell, for a stopped service, using a backup made with the README's backup commands
- **THEN** after the service starts again, the data from the backup is back and no data from after the backup remains

#### Scenario: Restore on a new machine
- **WHEN** a user has the backup file, the same `.env`, and the files the README's install path needs, on a machine with no CatchUp volume, and follows the README's new-machine restore commands
- **THEN** a new volume is created, the backup is restored into it, and CatchUp starts with the old data

#### Scenario: Private backup outside the checkout
- **WHEN** a user makes a backup with the README's commands
- **THEN** the backup file is outside the checkout and readable only by its owner
