## MODIFIED Requirements

### Requirement: Sources show their kind and confirm deletion inline
Each saved source SHALL show its kind as visible text (Website feed, Podcast, YouTube channel, or Saved from browser), its feed URL in full (wrapping when long), and its last check outcome and time. The built-in "Saved from browser" source SHALL show how many pages are waiting, in place of a feed URL and check outcome. Deleting a source MUST ask for confirmation in place and say that saved digests remain available.

#### Scenario: Delete confirmation
- **WHEN** the user chooses Delete on a source
- **THEN** that row asks "Delete <title>? Saved digests will remain available." with Delete and Cancel

#### Scenario: Saved-from-browser row
- **WHEN** two pages saved from the browser are waiting
- **THEN** the Sources page shows "Saved from browser" with "2 pages waiting"

## ADDED Requirements

### Requirement: Connect a browser in Settings
Settings SHALL have a "Browser extension" group with:
- "Connect a browser", which asks for the browser's name;
- the new token, shown once in a read-only field with a Copy button, and a note that it is shown only once;
- the list of connected browsers, each with its name, connection date, last use, and "Disconnect".

The token field and the note MUST be associated for assistive technology, and copying MUST announce its result.

#### Scenario: Copy the token
- **WHEN** the user connects a browser and chooses Copy
- **THEN** the token is copied, and the result is announced
