## ADDED Requirements

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
