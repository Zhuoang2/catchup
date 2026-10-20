# user-interface Specification

## Purpose
Defines how CatchUp's interface presents its screens and states: a newspaper-style layout that reads well in both themes and at any window width, one clear action per state, and behavior that works for keyboard and screen-reader users.

## Requirements

### Requirement: One grid for masthead, navigation, and content
The system SHALL place the masthead, the navigation, and page content in one shared container whose left and right edges align on every screen. On wide windows the content uses a 12-column grid, and page content MUST NOT be centered independently of the masthead. Below 900 px of window width, content becomes a single column. Screens MUST NOT scroll horizontally at a width of 320 px.

#### Scenario: Wide window
- **WHEN** the user opens any screen in a 1440 px wide window
- **THEN** the left edge of the page headline aligns with the left edge of the masthead rule

#### Scenario: Narrow window
- **WHEN** the window is 420 px wide
- **THEN** content is a single column and the navigation fits on one row

### Requirement: Themes follow the system with accessible contrast
The system SHALL use a light or dark theme according to the operating system's color-scheme preference. In both themes, text MUST have a contrast ratio of at least 4.5:1 against its background, including secondary text and placeholders. Component boundaries needed to see a control's state MUST have at least 3:1, such as a switch in its off state. Error, warning, and accent colors MUST be distinct hues, and status MUST never be conveyed by color alone.

#### Scenario: Dark system preference
- **WHEN** the operating system prefers a dark color scheme
- **THEN** CatchUp shows its dark theme without a setting

#### Scenario: Error versus warning
- **WHEN** a run shows one failed source and one source with a possible gap
- **THEN** the two are shown in different hues, each with its text label

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
- when its summary used gathered context: an "Also read" line after the summary, with each used page's or reply's title linked to its source

In windows wider than 1100 px, each item MUST be a row of its topic: its source line and linked title beside its summary. From 901 to 1100 px, an item's source line, title, and summary MUST stack within the item area, beside the topic's title and overview. At 900 px and wider, every item's summary MUST have the same width and end at the right edge of the content, whatever the summary's length, the item's position, or the number of items in the topic. In a 1440 px window, a summary line MUST hold no more than 40 Chinese characters or 80 Latin characters. At 900 px and below, an item's source line, title, and summary MUST stack in one column, in that order. A digest with only Creator updates MUST say that nothing could be summarized this time. The main screen and a saved digest opened from History MUST use the same layout.

#### Scenario: Long transcript summary
- **WHEN** a topic has one item with an overview and key points, and another item with a two-sentence summary
- **THEN** both summaries have the same width and end at the content's right edge, the key points show as a list, and both item titles have the same size

#### Scenario: Single-item topic
- **WHEN** a topic has a single item and the window is 1440 px wide
- **THEN** the item's title sits beside its summary, and the summary ends at the content's right edge, with no empty column after it

#### Scenario: Medium window
- **WHEN** a digest is opened in a 1000 px wide window
- **THEN** the topic's title and overview stay beside its items, each item shows its source line, title, and summary stacked, and each summary ends at the content's right edge

#### Scenario: Narrow window
- **WHEN** a digest is opened in a 420 px wide window
- **THEN** each item shows its source line, title, and summary stacked in one column

#### Scenario: Only Creator updates
- **WHEN** the user opens a digest whose only section is Creator updates
- **THEN** no index is shown and a line explains that nothing could be summarized this time

#### Scenario: Same digest in both places
- **WHEN** the main screen shows digest No. 7, and the user then opens No. 7 from History
- **THEN** both show the same headline, index, topics, items, and Creator updates. They differ only in the masthead, the main screen's run bar, and the saved digest's link back to all digests

#### Scenario: Item with also-read links
- **WHEN** an item's summary used a GitHub release page and a changelog page
- **THEN** the item shows "Also read:" after its summary, with both titles linked, and opening a link leaves the digest open

### Requirement: Readable Creator updates
Creator updates SHALL be grouped by source, and each group shows the source kind. Each item SHALL show its title linked to the original, its publish time, and its reason, in sentence case at a readable size, keeping proper nouns such as "YouTube" as written.

#### Scenario: Caption reason
- **WHEN** a video is listed because caption fetching is off
- **THEN** its reason reads "Caption fetching is off"

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

### Requirement: Sources show their kind and confirm deletion inline
Each saved source SHALL show its kind as visible text (Website feed, Podcast, or YouTube channel), its feed URL in full (wrapping when long), and its last check outcome and time. Deleting a source MUST ask for confirmation in place and say that saved digests remain available.

#### Scenario: Delete confirmation
- **WHEN** the user chooses Delete on a source
- **THEN** that row asks "Delete <title>? Saved digests will remain available." with Delete and Cancel

### Requirement: Settings explain risk and keep secrets out of view
Settings SHALL group fields into Model provider, Digest, and YouTube.
- A saved API key MUST be shown as text naming only its last four characters, never in an input placeholder.
- The YouTube caption risk note MUST appear directly with the "Fetch captions locally" toggle and be associated with it for assistive technology.
- A toggle's clickable area MUST be limited to the control and its label.

#### Scenario: Saved key
- **WHEN** a key is saved and the user opens Settings
- **THEN** the page reads "Saved key ending in 3f9a", and the key input is empty

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

### Requirement: Main screen shows the latest digest
The main screen SHALL show the newest saved digest in the digest reading layout, without another click. A run bar above the digest SHALL offer Generate and show:
- the number of sources, with a link to manage them
- while a run is active: its stage, its progress, and each source's check outcome
- after a run ends: its result, the counts of held-back items, and the sources that need attention

A source needs attention when its check in that run failed, including a rate limit, or flagged a possible gap. Each one MUST be shown with its outcome, and with its error when it has one. A rate-limited source is shown as rate limited in place of its error. When no source needs attention, the main screen MUST NOT show a source list for the ended run. Each source's last outcome stays available on the Sources screen. The same rule applies to the result of an ended run when no digest has been saved yet.

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
