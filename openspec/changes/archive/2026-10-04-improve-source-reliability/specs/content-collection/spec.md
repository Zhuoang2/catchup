# Spec Delta

## ADDED Requirements

### Requirement: Identify rate-limited checks
A check that fails because the source rate limited CatchUp SHALL be recorded as `failed`, with the HTTP status and the suggested wait when known. It MUST be shown to the user as "rate limited", distinct from other failures, in the source list and in run progress.

#### Scenario: Rate limited during a run
- **WHEN** a source answers 429 during a digest run and the wait is too long to retry
- **THEN** its check is `failed` with HTTP status 429, and the run progress and source list show it as rate limited

### Requirement: Space requests to the same host during a run
During a digest run, the system SHALL keep at least 1 second between consecutive requests to the same host. This covers feed checks and article fetches.

#### Scenario: Two sources on one host
- **WHEN** a run checks two sources whose feeds are on the same host
- **THEN** the second request to that host starts at least 1 second after the first

#### Scenario: Different hosts
- **WHEN** a run checks two sources on different hosts
- **THEN** no spacing delay is added between them
