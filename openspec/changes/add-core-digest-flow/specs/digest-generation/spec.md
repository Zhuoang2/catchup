# Spec Delta

## Purpose

Turns everything new since the last delivered digest into a topic-grouped digest with summaries and citations to the original items, generated on demand in the background with visible progress.

## ADDED Requirements

### Requirement: Start a digest run on demand
The system SHALL start a digest run only when the user requests one. At most one run MAY be active at a time. A request made while a run is active MUST be refused and point to the active run.

#### Scenario: Start a run
- **WHEN** the user clicks Generate Digest and no run is active
- **THEN** a run starts and the user can follow its progress

#### Scenario: Run already active
- **WHEN** the user requests a run while another run is active
- **THEN** the request is refused and the response identifies the active run

### Requirement: Show run progress and per-source outcomes
While a run is active, the system SHALL report its stage (collecting, summarizing, grouping), how many items have been summarized out of the total, and each source's check outcome as it becomes known.

#### Scenario: Following progress
- **WHEN** the user views an active run that is summarizing 12 items, 5 of them done
- **THEN** the user sees the summarizing stage and "5 of 12"

### Requirement: Include every pending item
A run SHALL include every item that is new and has not appeared in any saved digest, with no limit on the number of items. Items MUST be marked as delivered only when the digest containing them is saved.

#### Scenario: Long gap
- **WHEN** 140 items are pending at the start of a run
- **THEN** the saved digest covers all 140 items

#### Scenario: Run fails before saving
- **WHEN** a run fails after some items were summarized but before the digest is saved
- **THEN** all of the run's items remain pending for the next run

### Requirement: No digest when nothing is new
When a run finds no pending items, the system SHALL NOT save a digest. It MUST tell the user that there is no new content and show each source's check outcome.

#### Scenario: Nothing new and one failure
- **WHEN** a run finds no pending items and one source failed
- **THEN** no digest is saved and the user sees "no new content" together with the failed source and its error

### Requirement: Summarize items once and group them by topic
The system SHALL summarize each item individually and reuse a stored summary instead of summarizing the same item again. It SHALL then group the summarized items into topics, each with a title and a short overview. Every item in the run MUST appear in the digest exactly once. Items the grouping does not place MUST appear under an "Other" topic. An item whose summary could not be produced after retries MUST still appear with its title and link and a note that its summary is unavailable.

#### Scenario: Retry after failure
- **WHEN** a run fails during grouping and the user starts a new run
- **THEN** items summarized in the failed run are not summarized again

#### Scenario: Item missing from grouping
- **WHEN** the model's grouping omits an item
- **THEN** that item appears under "Other" in the saved digest

### Requirement: Citations come from stored data
Every item in a digest MUST show its source name and original link taken from stored item and source records. Item references produced by the model that do not match an item in the run MUST be discarded.

#### Scenario: Model returns an unknown item reference
- **WHEN** the grouping output references an item that is not in the run
- **THEN** the reference is ignored and no link is invented for it

### Requirement: Recover from interrupted runs
On startup, the system SHALL mark any run left unfinished as failed. Its items MUST remain pending.

#### Scenario: Restart during a run
- **WHEN** the application restarts while a run is summarizing
- **THEN** after restart that run shows as failed and a new run can include its items

### Requirement: Retry transient model errors
The system SHALL retry model calls that return empty content, rate-limit errors, or temporary server errors, with backoff and a bounded number of attempts. Authentication and insufficient-balance errors MUST fail the run immediately with a message telling the user to fix the configuration.

#### Scenario: Empty model response
- **WHEN** a model call returns empty content once and valid content on retry
- **THEN** the run continues using the valid content

#### Scenario: Rejected key during a run
- **WHEN** the provider rejects the API key during a run
- **THEN** the run fails immediately, its items remain pending, and the user is told to check the model settings
