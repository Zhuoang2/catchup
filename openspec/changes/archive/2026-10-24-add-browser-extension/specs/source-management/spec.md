## ADDED Requirements

### Requirement: A built-in source for pages saved from the browser
The system SHALL keep pages saved from the browser under one built-in source, "Saved from browser", created when the first page is saved. It MUST NOT be previewed or confirmed like a feed, and it MUST NOT be checked as one. Deleting it MUST remove its waiting pages, and saved digests MUST remain available.

#### Scenario: First page saved
- **WHEN** the user saves a page from the browser for the first time
- **THEN** the "Saved from browser" source appears on the Sources page, with one page waiting

#### Scenario: Delete the built-in source
- **WHEN** the user deletes "Saved from browser" while a page is waiting
- **THEN** the waiting page is removed, and earlier digests still show the pages they delivered
