## MODIFIED Requirements

### Requirement: Check every source on each run
Each digest run SHALL check every saved source once, and record for each source one outcome:
- `new_items`: the run includes at least one item from this source, either summarized or under Creator updates. It does not matter whether the entry was first seen in this check, recorded when the source was added, or held from an earlier run.
- `no_new_items`: the feed was fetched and parsed successfully, and the run includes nothing from this source.
- `failed`: the feed could not be fetched or parsed, with an error description.

Items held for a transcript or captions, items deferred to a later run, and entries recorded as already seen (such as skipped Shorts) MUST NOT make the outcome `new_items`. While sources are being checked, a successful check's outcome SHALL reflect what the check itself found. The outcome MUST become final once the run has chosen the items it includes, before any item is summarized. A failed check MUST never be reported as `no_new_items`.

#### Scenario: Source unreachable
- **WHEN** a source cannot be fetched or its feed cannot be parsed during a run
- **THEN** that source's outcome is `failed` with an error description, and other sources are still checked

#### Scenario: Nothing new
- **WHEN** a source's feed contains only entries already recorded, and none of the source's items is waiting to be delivered
- **THEN** that source's outcome is `no_new_items`

#### Scenario: First run after adding a source
- **WHEN** a source was added with 2 recent entries marked new, and its feed has not changed since
- **THEN** the next run includes the 2 entries, and that source's outcome is `new_items`

#### Scenario: Item carried over from a failed run
- **WHEN** a run fails after collecting an item, and the next run finds nothing new in that item's feed
- **THEN** the next run includes the item, and that source's outcome is `new_items`

#### Scenario: Episode held for its transcript
- **WHEN** a podcast's only new episode is still waiting for its transcript
- **THEN** that source's outcome is `no_new_items`, and the run reports the episode as waiting

#### Scenario: Skipped Short
- **WHEN** a YouTube channel's only new entry is a Short that is skipped
- **THEN** that source's outcome is `no_new_items`
