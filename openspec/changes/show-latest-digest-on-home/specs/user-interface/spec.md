## ADDED Requirements

### Requirement: Main screen shows the latest digest
The main screen SHALL show the newest saved digest in the digest reading layout, without another click. A run bar above the digest SHALL offer Generate and show:
- the number of sources, with a link to manage them
- while a run is active: its stage, its progress, and each source's check outcome
- after a run ends: its result, the counts of held-back items, and each source's check outcome

While a run is active, and after a run ends with no new content or fails, the digest already shown MUST stay visible. When a run saves a digest, that digest MUST replace the one shown, without reloading the page. When no digest has been saved, the main screen SHALL guide the user instead, as described under "One primary action per state". The navigation SHALL name the main screen "Latest".

#### Scenario: Returning user
- **WHEN** digests No. 1 to No. 4 are saved and the user opens the main screen
- **THEN** digest No. 4 is shown with its headline, topics, and Creator updates, and Generate is available above it

#### Scenario: Run saves a new digest
- **WHEN** the main screen shows digest No. 12 and the user generates a digest that is saved as No. 13
- **THEN** progress is shown above digest No. 12 while the run is active, and digest No. 13 then replaces it without another click

#### Scenario: Run finds no new content
- **WHEN** the main screen shows digest No. 12 and a run ends with no new content
- **THEN** the run bar says that there is no new content, with each source's outcome, and digest No. 12 stays shown

#### Scenario: No digest yet
- **WHEN** a model is configured, a source is added, and no digest has been saved
- **THEN** the main screen shows Generate digest as its primary action, with the sources and how-it-works side information, and no digest area

#### Scenario: Navigation
- **WHEN** the user opens any screen
- **THEN** the first navigation item reads "Latest" and leads to the main screen

## MODIFIED Requirements

### Requirement: Digest reading layout
A digest SHALL open with:
- a masthead: the full masthead with today's date on the main screen, and a compact one-row masthead when a saved digest is opened from History
- a headline with the digest's edition number, date, and time
- its item count, source count, model, and token totals

When the digest has more than one section, an index of its topics and of Creator updates MUST follow. Each topic MUST be a section row: its title and overview beside its items. Each item MUST show:
- its source kind
- its source name and publish time
- its title linked to the original
- its summary: paragraphs, with "- " lines as a list

An item with key points or a long summary MUST get a wider column than a short item; width MUST NOT depend on the item's position. A digest with only Creator updates MUST say that nothing could be summarized this time. The main screen and a saved digest opened from History MUST use the same layout.

#### Scenario: Long transcript summary
- **WHEN** a topic has one item with an overview and key points, and another item with a two-sentence summary
- **THEN** the first item gets the wide column, its key points show as a list, and both item titles have the same size

#### Scenario: Only Creator updates
- **WHEN** the user opens a digest whose only section is Creator updates
- **THEN** no index is shown and a line explains that nothing could be summarized this time

#### Scenario: Same digest in both places
- **WHEN** the main screen shows digest No. 7, and the user then opens No. 7 from History
- **THEN** both show the same headline, index, topics, items, and Creator updates; only the masthead and the run bar differ

### Requirement: One primary action per state
Each screen state SHALL offer at most one primary action. A state where nothing needs doing next offers none, such as a run that found no new content, or a run that saved a digest that is now shown. The primary action is:
- **first run** (no model configured): set up the model, with Generate shown as unavailable together with the reason
- **no sources yet** (a model is configured): add sources, with Generate shown as unavailable together with the reason
- **ready to generate** (a model and a source, no run active): generate a digest
- **a configuration error:** check settings
- **another failed run:** try again
- **an open source preview:** confirm the source

These states apply whether or not the main screen shows a digest. Other actions remain available as secondary actions.

#### Scenario: First run
- **WHEN** no model is configured and the user opens the main screen
- **THEN** "Set up your model" is the only primary action, and Generate is disabled with a visible reason

#### Scenario: No sources yet
- **WHEN** a model is configured, no source has been added, and the user opens the main screen
- **THEN** "Add sources" is the only primary action, and Generate is disabled with a visible reason

#### Scenario: Digest ready
- **WHEN** a run has just saved a digest
- **THEN** the new digest is shown, no primary action is offered, Generate digest remains available as a secondary action, and no "View digest" action is shown

### Requirement: Side information reflects the state
On wide windows, Sources and History SHALL show side information beside the main content. So SHALL the main screen while it shows no digest. It MUST describe the actual state:
- On first run, getting-started steps instead of source counts.
- On an empty history, no archive counts.
- Otherwise, real counts: on the main screen, sources by kind; on History, the archive.

When the main screen shows a digest, it SHALL show no side information, and the number of sources SHALL be shown in the run bar instead. On narrow windows, the side information follows the main content.

#### Scenario: Empty history
- **WHEN** no digest has been saved and the user opens History
- **THEN** no archive count is shown

#### Scenario: Main screen with a digest
- **WHEN** a digest has been saved and the user opens the main screen in a 1440 px wide window
- **THEN** the digest uses the full content width, no side information is shown, and the run bar shows the number of sources

### Requirement: Keyboard and screen-reader support
The system SHALL support keyboard and assistive technology use:
- The skip link and the digest index MUST move keyboard focus to their targets, not only scroll.
- Generated digest text MUST carry the language it was written in.
- Run progress and the run result MUST be announced through one persistent status region.
- When a run's saved digest replaces the digest shown on the main screen, keyboard focus MUST NOT move.
- The progress bar MUST have an accessible name.
- Field errors and hints MUST be linked to their inputs, and invalid inputs marked invalid.
- Scrolling MUST NOT animate when the user prefers reduced motion.
- Each screen MUST have its own document title that names the screen, and a digest's title MUST include its edition number. The main screen's title names the main screen and, when it shows a digest, that digest's edition number.

#### Scenario: Skip link
- **WHEN** a keyboard user activates "Skip to content"
- **THEN** focus moves to the main content, and the next Tab moves within it

#### Scenario: Chinese digest
- **WHEN** a digest written in Simplified Chinese is shown
- **THEN** its topic titles, overviews, and summaries are marked as Simplified Chinese, and item titles keep the page language

#### Scenario: Run finishes
- **WHEN** a run finishes with a saved digest while the user is on the main screen
- **THEN** the status region announces that the digest is ready and how many items it has, counting Creator updates, the new digest replaces the one shown, and keyboard focus stays where it was

#### Scenario: Run fails
- **WHEN** a run fails while the user is on the main screen
- **THEN** the failure is announced once, through the status region

#### Scenario: Page title
- **WHEN** the user opens digest No. 3 from History
- **THEN** the document title names the digest by its edition number, and each other screen has a different title

#### Scenario: Main screen title
- **WHEN** the main screen shows digest No. 3
- **THEN** the document title names the main screen and edition No. 3, and differs from the title of digest No. 3 opened from History
