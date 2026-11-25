# Spec Delta

## MODIFIED Requirements

### Requirement: Sources show their kind and confirm deletion inline
Each saved source SHALL show its kind as visible text (Website feed, Podcast, YouTube channel, X account, Bilibili uploader, or Saved from browser), its feed URL in full (wrapping when long), and its last check outcome and time. An X account shows its profile address, and a Bilibili uploader its space address, in place of a feed URL. The built-in "Saved from browser" source SHALL show how many pages are waiting, in place of a feed URL and check outcome. Deleting a source MUST ask for confirmation in place and say that saved digests remain available.

#### Scenario: Delete confirmation
- **WHEN** the user chooses Delete on a source
- **THEN** that row asks "Delete <title>? Saved digests will remain available." with Delete and Cancel

#### Scenario: Saved-from-browser row
- **WHEN** two pages saved from the browser are waiting
- **THEN** the Sources page shows "Saved from browser" with "2 pages waiting"

#### Scenario: Bilibili uploader row
- **WHEN** the uploader `2267573` is followed
- **THEN** its row shows "Bilibili uploader" and `https://space.bilibili.com/2267573`
