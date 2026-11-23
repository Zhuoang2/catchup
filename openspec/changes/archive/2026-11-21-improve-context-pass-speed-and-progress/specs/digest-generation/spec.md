## MODIFIED Requirements

### Requirement: Show run progress and per-source outcomes
While a run is active, the system SHALL report its stage (collecting, summarizing, grouping), how many sources are checked out of the number the run checks, how many items have been summarized out of the total, and each source's check outcome as it becomes known. The number of sources the run checks MUST be fixed when the run starts: adding or deleting a source during the run does not change it.

While the context pass runs, the system SHALL also report how many linked pages are read, out of a total:
- A page counts as read when its request finishes, with or without usable text, or when robots.txt refuses it. A post page and a comment feed read for author replies count as pages, and so do an item's saved replies, which need no request.
- The total MUST be the pages read so far plus the pages the run can still read within the remaining per-run limit. It counts one robots.txt request for each site that the run has not asked yet, and no request for a page that a robots.txt already read refuses. While pages for several items are read at the same time, a page being read is counted before its request takes a unit from the limit, so the total can briefly be higher than this; it is corrected as each read finishes.
- A page that the run will not read MUST leave the total. This applies when the per-run limit is used up, when the item's linked text has reached its cap, and when the item is deleted.
- The linked-page progress MUST be shown from the start of the context pass. When the pass ends, the number read MUST equal the total.

When a source's check finds no new entries, but the source has pending items that are ready for this run, its check outcome MUST be "new items" as soon as the check is saved. The recent entries recorded when the user follows a source are such items. Items that still wait for a transcript or captions are not ready.

#### Scenario: Following progress
- **WHEN** the user views an active run that is summarizing 12 items, 5 of them done
- **THEN** the user sees the summarizing stage and "5 of 12"

#### Scenario: Reading linked pages
- **WHEN** every source is checked and the run has read 7 of the 20 linked pages it can read
- **THEN** the user sees "Linked pages read: 7 of 20"

#### Scenario: Per-run limit lower than the links
- **WHEN** a pending item links to six pages, two on each of three sites, every robots.txt allows them, and the per-run limit is 5
- **THEN** the total is 3 from the start of the context pass, and the pass ends at "Linked pages read: 3 of 3"

#### Scenario: Pages after the cap
- **WHEN** an item's first pages reach its linked-text cap, and the item has more related links
- **THEN** its remaining links leave the total, and the pass ends with the number read equal to the total

#### Scenario: Source added during a run
- **WHEN** a run that checks 3 sources is checking them, and the user adds a fourth source
- **THEN** the progress still reads "of 3", and the run shows the linked-page progress when its context pass starts

#### Scenario: Source deleted during a run
- **WHEN** a source is deleted while the run checks sources, and the run then reads linked pages
- **THEN** the run shows the linked-page progress from the start of the context pass

#### Scenario: Source followed just before a run
- **WHEN** the user follows a feed, its recent entries are recorded as pending, and a run starts before the feed publishes anything new
- **THEN** the feed's check in that run shows "New items" as soon as it is saved

#### Scenario: X account followed just before a run
- **WHEN** the user follows an X account, its recent posts are recorded as pending, and a run reads no newer posts for it
- **THEN** the account's check in that run shows "New items" as soon as it is saved

## ADDED Requirements

### Requirement: Record how long each run stage takes
The system SHALL record, for each run, how many seconds each stage it finished took:
- the source checks, including X accounts;
- the caption pass;
- the context pass;
- the summaries;
- the grouping.

Each duration MUST be saved when its stage ends, so a run that fails keeps the durations of the stages it finished. The run's API response SHALL include them. The screen does not show them.

#### Scenario: Durations of a finished run
- **WHEN** a run checks sources, reads linked pages, summarizes items, groups them, and saves a digest
- **THEN** its API response has a duration in seconds for the checks, the caption pass, the context pass, the summaries, and the grouping

#### Scenario: Run that fails while summarizing
- **WHEN** a run fails during the summaries
- **THEN** its API response has durations for the checks, the caption pass, and the context pass, and none for the summaries or the grouping

#### Scenario: Run with no new content
- **WHEN** a run finds nothing to summarize
- **THEN** its API response has durations for the checks, the caption pass, and the context pass only
