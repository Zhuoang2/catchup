# Spec Delta

## MODIFIED Requirements

### Requirement: Reopen a saved digest
The system SHALL let the user open a saved digest and see:
- its edition number (the digest's sequence number), and its date and time
- its topics and each topic's overview
- for each summarized item: its summary, title, source name and source kind, publish date when known, and a link to the original
- its Creator updates section when it has one, with each item's title, publish date when known, link, and reason, grouped by source with the source kind

The content shown MUST be the content that was saved, and MUST NOT be regenerated. The digest MUST record the language its summaries were written in, and each item's source kind, at the time it was saved. Later changes to the digest language setting or to a source MUST NOT change how a saved digest is presented. Digests saved before these were recorded are shown without a language mark or source kind.

#### Scenario: Open an older digest
- **WHEN** the user opens a digest from the history
- **THEN** the same topics, summaries, and links that were generated are shown, and the links open the original items

#### Scenario: Open a digest with Creator updates
- **WHEN** the user opens a saved digest whose Creator updates listed a podcast episode with "no transcript within 7 days", and the configured wait has since changed to 10 days
- **THEN** the episode is still shown with "no transcript within 7 days"

#### Scenario: Language changed after saving
- **WHEN** a digest was saved in Simplified Chinese and the digest language setting is later changed to English
- **THEN** reopening it still marks its summaries as Simplified Chinese

#### Scenario: Source deleted after saving
- **WHEN** a podcast source is deleted after a digest containing its episodes was saved
- **THEN** reopening the digest still shows those items as from a podcast
