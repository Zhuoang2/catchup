## MODIFIED Requirements

### Requirement: Include every pending item
A run SHALL include every item that is new and has not appeared in any saved digest, with no limit on the number of items. There is one exception: a podcast episode still waiting for its transcript (see the `transcripts` capability) is held back. It is included once a transcript is found or its wait ends. YouTube items are also held back while they are in their caption wait, or when their captions are not yet fetched because of the per-run caption limit. They are included once captions are found or the wait ends. Items recorded after the run's context pass has started, such as a page saved from the browser or the recent entries of a source confirmed during the pass, are also left out of that run: they stay pending, are not counted in its source outcomes or waiting counts, and are handled by the next run, including its context pass. Items MUST be marked as delivered only when the digest containing them is saved. Each item MUST appear in at most one saved digest.

#### Scenario: Long gap
- **WHEN** 140 items are pending at the start of a run and none is waiting for a transcript
- **THEN** the saved digest covers all 140 items

#### Scenario: Run fails before saving
- **WHEN** a run fails after some items were summarized but before the digest is saved
- **THEN** all of the run's items remain pending for the next run

#### Scenario: Episode waiting for a transcript
- **WHEN** a run starts one day after a podcast episode was first recorded and the episode still has no transcript
- **THEN** the episode does not appear in that run's digest and stays pending

#### Scenario: Item never repeated
- **WHEN** an item appeared in a saved digest, either summarized or under Creator updates
- **THEN** it does not appear in any later digest

#### Scenario: Page saved while linked pages are read
- **WHEN** the user saves a page from the browser while a run is reading linked pages
- **THEN** that run's digest does not include the page, the page stays pending, and the next run reads its linked pages and includes it
