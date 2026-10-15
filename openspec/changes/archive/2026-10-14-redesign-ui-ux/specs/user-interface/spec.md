# Spec Delta

## Purpose

Defines how CatchUp's interface presents its screens and states: a newspaper-style layout that reads well in both themes and at any window width, one clear action per state, and behavior that works for keyboard and screen-reader users.

## ADDED Requirements

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
- a compact one-row masthead
- a headline with the digest's edition number, date, and time
- its item count, source count, model, and token totals

When the digest has more than one section, an index of its topics and of Creator updates MUST follow. Each topic MUST be a section row: its title and overview beside its items. Each item MUST show:
- its source kind
- its source name and publish time
- its title linked to the original
- its summary: paragraphs, with "- " lines as a list

An item with key points or a long summary MUST get a wider column than a short item; width MUST NOT depend on the item's position. A digest with only Creator updates MUST say that nothing could be summarized this time.

#### Scenario: Long transcript summary
- **WHEN** a topic has one item with an overview and key points, and another item with a two-sentence summary
- **THEN** the first item gets the wide column, its key points show as a list, and both item titles have the same size

#### Scenario: Only Creator updates
- **WHEN** the user opens a digest whose only section is Creator updates
- **THEN** no index is shown and a line explains that nothing could be summarized this time

### Requirement: Readable Creator updates
Creator updates SHALL be grouped by source, and each group shows the source kind. Each item SHALL show its title linked to the original, its publish time, and its reason, in sentence case at a readable size, keeping proper nouns such as "YouTube" as written.

#### Scenario: Caption reason
- **WHEN** a video is listed because caption fetching is off
- **THEN** its reason reads "Caption fetching is off"

### Requirement: One primary action per state
Each screen state SHALL offer at most one primary action. A state where nothing needs doing next, such as a run that found no new content, offers none. The primary action is:
- **first run** (no model configured): set up the model, with Generate shown as unavailable together with the reason
- **no sources yet** (a model is configured): add sources, with Generate shown as unavailable together with the reason
- **a finished digest:** view the digest
- **a configuration error:** check settings
- **an open source preview:** confirm the source

Other actions remain available as secondary actions.

#### Scenario: First run
- **WHEN** no model is configured and the user opens Generate
- **THEN** "Set up your model" is the only primary action, and Generate is disabled with a visible reason

#### Scenario: No sources yet
- **WHEN** a model is configured, no source has been added, and the user opens Generate
- **THEN** "Add sources" is the only primary action, and Generate is disabled with a visible reason

#### Scenario: Digest ready
- **WHEN** a run has just saved a digest
- **THEN** "View digest" is the only primary action

### Requirement: Side information reflects the state
On wide windows, Generate, Sources, and History SHALL show side information beside the main content. It MUST describe the actual state:
- On first run, getting-started steps instead of a last digest or source counts.
- On an empty history, no archive counts.
- Otherwise, real counts: the last digest with its edition number and time; sources by kind.

On narrow windows, the side information follows the main content.

#### Scenario: Empty history
- **WHEN** no digest has been saved and the user opens History
- **THEN** no archive count is shown

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
- The progress bar MUST have an accessible name.
- Field errors and hints MUST be linked to their inputs, and invalid inputs marked invalid.
- Scrolling MUST NOT animate when the user prefers reduced motion.
- Each screen MUST have its own document title that names the screen, and a digest's title MUST include its edition number.

#### Scenario: Skip link
- **WHEN** a keyboard user activates "Skip to content"
- **THEN** focus moves to the main content, and the next Tab moves within it

#### Scenario: Chinese digest
- **WHEN** a digest written in Simplified Chinese is shown
- **THEN** its topic titles, overviews, and summaries are marked as Simplified Chinese, and item titles keep the page language

#### Scenario: Run finishes
- **WHEN** a run finishes with a saved digest while the user is on Generate
- **THEN** the status region announces that the digest is ready and how many items it has, counting Creator updates

#### Scenario: Run fails
- **WHEN** a run fails while the user is on Generate
- **THEN** the failure is announced once, through the status region

#### Scenario: Page title
- **WHEN** the user opens digest No. 3
- **THEN** the document title names the digest by its edition number, and each other screen has a different title
