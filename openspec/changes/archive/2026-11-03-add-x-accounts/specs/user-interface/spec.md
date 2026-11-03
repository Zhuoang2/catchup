## MODIFIED Requirements

### Requirement: Sources show their kind and confirm deletion inline
Each saved source SHALL show its kind as visible text (Website feed, Podcast, YouTube channel, X account, or Saved from browser), its feed URL in full (wrapping when long), and its last check outcome and time. The built-in "Saved from browser" source SHALL show how many pages are waiting, in place of a feed URL and check outcome. Deleting a source MUST ask for confirmation in place and say that saved digests remain available.

#### Scenario: Delete confirmation
- **WHEN** the user chooses Delete on a source
- **THEN** that row asks "Delete <title>? Saved digests will remain available." with Delete and Cancel

#### Scenario: Saved-from-browser row
- **WHEN** two pages saved from the browser are waiting
- **THEN** the Sources page shows "Saved from browser" with "2 pages waiting"

### Requirement: Settings explain risk and keep secrets out of view
Settings SHALL group fields into Model provider, Digest, and YouTube, with separate groups for the browser extension and for X accounts.
- A saved API key, and a saved X token, MUST each be shown as text naming only its last four characters, never in an input placeholder.
- The YouTube caption risk note MUST appear directly with the "Fetch captions locally" toggle and be associated with it for assistive technology.
- A toggle's clickable area MUST be limited to the control and its label.

#### Scenario: Saved key
- **WHEN** a key is saved and the user opens Settings
- **THEN** the page reads "Saved key ending in 3f9a", and the key input is empty

## ADDED Requirements

### Requirement: Ask for the X token where it is needed
When a preview on the Sources page reports that an X token is needed, the page SHALL show, in place, a password field for the token, a link to how to get one, and "Save and preview". Saving MUST store the token as Settings does, then preview the same address again. The field and its explanation MUST be associated for assistive technology, and the result MUST be announced.

Settings SHALL have an "X accounts" group with the token field, "Test", "Remove", and "Delete all X data". "Delete all X data" MUST ask for confirmation in place, say that it also removes followed accounts' items from saved digests, and say that pages saved from X with the extension stay. The group SHALL say that reads are billed to the user's X developer account, and that a spending limit can be set in the X console.

#### Scenario: Token asked in place
- **WHEN** no X token is saved and the user previews `https://x.com/simonw` on the Sources page
- **THEN** the page asks for the token in place, and after "Save and preview" shows the account's preview

#### Scenario: First run with X
- **WHEN** no model key and no X token are saved, and the user opens Settings
- **THEN** the "X accounts" group is optional, and saving the model settings does not require an X token
