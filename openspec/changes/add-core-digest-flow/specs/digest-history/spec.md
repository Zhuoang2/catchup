# Spec Delta

## Purpose

Keeps every generated digest so the user can return to it later, browse past digests, and open the original items they link to.

## ADDED Requirements

### Requirement: List saved digests
The system SHALL list saved digests from newest to oldest, showing for each its creation time, the number of items, and the number of sources it covers.

#### Scenario: Several digests
- **WHEN** the user opens the history after three digests were generated
- **THEN** the three digests are listed newest first with their times and item counts

### Requirement: Reopen a saved digest
The system SHALL let the user open a saved digest and see its topics, each topic's overview, and each item's summary, title, source name, publish date when known, and a link to the original. The content shown MUST be the content that was saved, and MUST NOT be regenerated.

#### Scenario: Open an older digest
- **WHEN** the user opens a digest from the history
- **THEN** the same topics, summaries, and links that were generated are shown, and the links open the original items

### Requirement: Persist across restarts
Saved digests, sources, recorded items, and check outcomes SHALL survive an application restart.

#### Scenario: Restart
- **WHEN** the application is restarted
- **THEN** previously saved digests are still listed and open with their full content
