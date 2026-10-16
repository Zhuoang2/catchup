# digest-history Specification

## Purpose
Keeps every generated digest so the user can return to it later, browse past digests, and open the original items they link to.

## Requirements

### Requirement: List saved digests
The system SHALL list saved digests from newest to oldest, showing for each its edition number, its creation time, the number of items, the number of sources it covers, and the titles of its topics. A digest with only Creator updates SHALL be listed as such. The list MUST be available from a single request.

#### Scenario: Several digests
- **WHEN** the user opens the history after three digests were generated
- **THEN** the three digests are listed newest first with their times, item counts, and topic titles

#### Scenario: Creator updates only
- **WHEN** a saved digest has no topics and only Creator updates
- **THEN** the history lists it as containing only Creator updates

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

### Requirement: Persist across restarts
Saved digests, sources, recorded items, and check outcomes SHALL survive an application restart.

#### Scenario: Restart
- **WHEN** the application is restarted
- **THEN** previously saved digests are still listed and open with their full content

### Requirement: Open the latest digest
The system SHALL return the newest saved digest from a single request, with the same content as reopening it (see "Reopen a saved digest"). "Newest" MUST follow the order of the saved-digest list: newest first, and the higher edition number first when two digests were saved at the same time. When no digest has been saved, the request MUST return an empty result rather than an error.

#### Scenario: Several digests
- **WHEN** digests No. 1, No. 2, and No. 3 have been saved, in that order
- **THEN** the latest-digest request returns digest No. 3 with its topics, items, and Creator updates, exactly as reopening No. 3 shows them

#### Scenario: No digest yet
- **WHEN** no digest has been saved
- **THEN** the latest-digest request succeeds and returns an empty result

#### Scenario: Same save time
- **WHEN** digests No. 2 and No. 3 have the same creation time
- **THEN** the latest-digest request returns digest No. 3
