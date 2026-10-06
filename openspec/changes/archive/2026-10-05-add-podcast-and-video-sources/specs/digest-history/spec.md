# Spec Delta

## MODIFIED Requirements

### Requirement: Reopen a saved digest
The system SHALL let the user open a saved digest and see:
- its topics and each topic's overview
- for each summarized item: its summary, title, source name, publish date when known, and a link to the original
- its Creator updates section when it has one, with each item's title, publish date when known, link, and reason, grouped by source

The content shown MUST be the content that was saved, and MUST NOT be regenerated.

#### Scenario: Open an older digest
- **WHEN** the user opens a digest from the history
- **THEN** the same topics, summaries, and links that were generated are shown, and the links open the original items

#### Scenario: Open a digest with Creator updates
- **WHEN** the user opens a saved digest whose Creator updates listed a podcast episode with "no transcript within 7 days", and the configured wait has since changed to 10 days
- **THEN** the episode is still shown with "no transcript within 7 days"
