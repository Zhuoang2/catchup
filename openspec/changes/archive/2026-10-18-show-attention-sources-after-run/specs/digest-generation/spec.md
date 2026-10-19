## MODIFIED Requirements

### Requirement: No digest when nothing is new
When a run finds no pending items to include, the system SHALL NOT save a digest. It MUST tell the user that there is no new content and show the sources whose check failed or flagged a possible gap. When podcast episodes or YouTube videos are being held back for transcripts or captions, or YouTube videos are deferred to a later run, the message MUST state how many.

#### Scenario: Nothing new and one failure
- **WHEN** a run finds no pending items and one source failed
- **THEN** no digest is saved and the user sees "no new content" together with the failed source and its error

#### Scenario: Only waiting episodes
- **WHEN** the only pending items are 2 podcast episodes waiting for transcripts
- **THEN** no digest is saved and the user sees "no new content" and "2 items waiting for transcripts or captions"
