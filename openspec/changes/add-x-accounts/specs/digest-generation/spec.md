## ADDED Requirements

### Requirement: Summarize posts from followed X accounts
Posts from followed X accounts that a run includes SHALL be summarized like website items, with their related context and images. Each one MUST be shown under "X · <display name>", MUST link to the post on x.com, and MUST list the linked pages it used under "Also read".

#### Scenario: Followed X post in a digest
- **WHEN** a run includes a post from the followed account "Simon Willison" that links to an article
- **THEN** the digest shows its summary under "X · Simon Willison", linking to the post, and "Also read" lists the article if it was used
