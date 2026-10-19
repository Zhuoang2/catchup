## ADDED Requirements

### Requirement: Use related context in summaries
When an item has gathered context, the summary call SHALL receive it after the item's text, labeled by kind (linked page or author reply), with each part's title and site. The model MUST use context only where it relates to the item, and MUST NOT summarize a linked page or a reply on its own. The model SHALL return the references of the context it used. References that do not match the item's context MUST be discarded. The text budget for splitting long items SHALL include the context. The context MUST be treated as data, not instructions. An item that already had a summary when its context was gathered SHALL be summarized again with the context.

#### Scenario: Unrelated linked page
- **WHEN** an item's context holds its release notes and an unrelated page linked from the post's footer
- **THEN** the summary draws on the release notes, and only the release notes are recorded as used

#### Scenario: Link-only post explained by its linked page
- **WHEN** an item's own text is only a release title, and its context holds the release notes
- **THEN** the summary describes the release from the notes, and does not say that the item has no substance

#### Scenario: Context gathered after a summary
- **WHEN** an item was summarized in a run that then failed, and the next run gathers its context
- **THEN** the item is summarized again with that context

#### Scenario: Model returns an unknown context reference
- **WHEN** the summary output names a context reference that the item does not have
- **THEN** the reference is dropped, and the summary is kept

## MODIFIED Requirements

### Requirement: Citations come from stored data
Every item in a digest MUST show its source name and original link taken from stored item and source records. The links an item shows for the context its summary used MUST come from the stored context, never from the model's text. Item references produced by the model that do not match an item in the run MUST be discarded.

#### Scenario: Model returns an unknown item reference
- **WHEN** the grouping output references an item that is not in the run
- **THEN** the reference is ignored and no link is invented for it

#### Scenario: Context link comes from stored context
- **WHEN** a summary used a linked page
- **THEN** the digest shows that page's stored title and URL

### Requirement: Show run progress and per-source outcomes
While a run is active, the system SHALL report its stage (collecting, summarizing, grouping), how many items have been summarized out of the total, and each source's check outcome as it becomes known. While the context pass runs, it SHALL also report how many context fetches are done out of the number planned.

#### Scenario: Following progress
- **WHEN** the user views an active run that is summarizing 12 items, 5 of them done
- **THEN** the user sees the summarizing stage and "5 of 12"

#### Scenario: Reading linked pages
- **WHEN** every source is checked and the run has read 7 of 20 planned linked pages
- **THEN** the user sees "Linked pages read: 7 of 20"
