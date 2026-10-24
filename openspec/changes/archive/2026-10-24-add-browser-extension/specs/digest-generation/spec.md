## ADDED Requirements

### Requirement: Summarize pages saved from the browser
Pages saved from the browser that are waiting SHALL be included in the next digest run, and summarized like website items, with their related context and images. Each one MUST be shown under the saved page's site name, for example "X · Simon Willison", and MUST link to the address the user saved.

#### Scenario: Saved X post in a digest
- **WHEN** a run includes an X post saved from the browser
- **THEN** the digest shows its summary under "X · <author>", linking to the post, and its "Also read" lists any article it linked
