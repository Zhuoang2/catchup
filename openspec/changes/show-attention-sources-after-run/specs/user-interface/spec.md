## MODIFIED Requirements

### Requirement: Main screen shows the latest digest
The main screen SHALL show the newest saved digest in the digest reading layout, without another click. A run bar above the digest SHALL offer Generate and show:
- the number of sources, with a link to manage them
- while a run is active: its stage, its progress, and each source's check outcome
- after a run ends: its result, the counts of held-back items, and the sources that need attention

A source needs attention when its check in that run failed, including a rate limit, or flagged a possible gap. Each one MUST be shown with its outcome, and with its error when it has one. When no source needs attention, the main screen MUST NOT show a source list for the ended run. Each source's last outcome stays available on the Sources screen. The same rule applies to the result of an ended run when no digest has been saved yet.

While a run is active, and after a run ends with no new content or fails, the digest already shown MUST stay visible. When a run saves a digest, that digest MUST replace the one shown, without reloading the page. When no digest has been saved, the main screen SHALL guide the user instead, as described under "One primary action per state". The navigation SHALL name the main screen "Latest".

#### Scenario: Returning user
- **WHEN** digests No. 1 to No. 4 are saved and the user opens the main screen
- **THEN** digest No. 4 is shown with its headline, topics, and Creator updates, and Generate is available above it

#### Scenario: Run saves a new digest
- **WHEN** the main screen shows digest No. 12 and the user generates a digest that is saved as No. 13
- **THEN** progress is shown above digest No. 12 while the run is active, and digest No. 13 then replaces it without another click

#### Scenario: Run finds no new content
- **WHEN** the main screen shows digest No. 12, and a run ends with no new content while one source is rate limited
- **THEN** the run bar says that there is no new content and shows that source as rate limited, and digest No. 12 stays shown

#### Scenario: Every source fine after a run
- **WHEN** a run with three sources saves a digest, and every source's check found new items or no new items without a possible gap
- **THEN** the run bar shows the result with three sources and no source list

#### Scenario: Some sources need attention after a run
- **WHEN** a run with three sources ends, one source failed with an error, one flagged a possible gap, and one found new items
- **THEN** the run bar lists the failed source with its error and the source with the possible gap, and does not list the third source

#### Scenario: Every checked source shown during a run
- **WHEN** a run is active and two of three sources have been checked, one with new items and one with no new items
- **THEN** the run bar lists both checked sources with their outcomes

#### Scenario: No digest yet
- **WHEN** a model is configured, a source is added, and no digest has been saved
- **THEN** the main screen shows Generate digest as its primary action, with the sources and how-it-works side information, and no digest area

#### Scenario: Navigation
- **WHEN** the user opens any screen
- **THEN** the first navigation item reads "Latest" and leads to the main screen
