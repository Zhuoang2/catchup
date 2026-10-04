# Spec Delta

## ADDED Requirements

### Requirement: Identify CatchUp in outgoing requests
Every request CatchUp makes to a source SHALL carry a User-Agent that names CatchUp, its version, and the project URL. When the instance configures a contact, the User-Agent MUST include it.

#### Scenario: Default User-Agent
- **WHEN** CatchUp fetches a page, feed, or article with no contact configured
- **THEN** the request's User-Agent starts with `CatchUp/` and contains the project URL

#### Scenario: Configured contact
- **WHEN** the instance sets a contact such as `by /u/example`
- **THEN** the User-Agent of every request includes that contact

### Requirement: Honor rate limits when fetching
When a source responds with HTTP 429, or 503 with a `Retry-After` header, the system SHALL wait and retry once if the requested delay is at most 10 seconds and fits within the fetch deadline. Otherwise it MUST stop without retrying and report that the source is rate limited, including the suggested wait when the server provided one. Both `Retry-After` forms (seconds and HTTP date) MUST be understood.

#### Scenario: Short wait requested
- **WHEN** a source answers 429 with `Retry-After: 3` and then succeeds
- **THEN** the system waits about 3 seconds, retries once, and the fetch succeeds

#### Scenario: Long wait requested
- **WHEN** a source answers 429 with `Retry-After: 120`
- **THEN** the system does not wait, makes no further request to it, and reports the source as rate limited with a suggested wait of about 120 seconds

#### Scenario: No wait given
- **WHEN** a source answers 429 without a `Retry-After` header
- **THEN** the system does not retry and reports the source as rate limited

#### Scenario: Rate limited while adding a source
- **WHEN** a preview or confirm request is rate limited
- **THEN** the user sees a "rate limited, try again later" message that differs from other fetch errors

### Requirement: Reuse a recent preview on confirm
When the user confirms a source within 10 minutes of previewing it, the system SHALL use the feed content fetched during the preview instead of fetching the feed again. After that window, or when no preview content is available (e.g. after a restart), confirm MUST fetch the feed as before.

#### Scenario: Confirm right after preview
- **WHEN** the user previews a feed and confirms it a few seconds later
- **THEN** the source is saved without another request to the feed URL

#### Scenario: Confirm after the window
- **WHEN** the user confirms more than 10 minutes after the preview
- **THEN** the system fetches the feed again before saving
