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
- when its summary used gathered context: an "Also read" line after the summary, with each used page's or reply's title linked to its source
- its Bookmark, Like, and Feedback controls (see "Bookmark, like, and give feedback on digest items")

In windows wider than 1100 px, each item MUST be a row of its topic: its source line, linked title, and controls, in that order, beside its summary. From 901 to 1100 px, an item's source line, title, summary, and controls MUST stack within the item area, beside the topic's title and overview. At 900 px and wider, every item's summary MUST have the same width and end at the right edge of the content, whatever the summary's length, the item's position, or the number of items in the topic. In a 1440 px window, a summary line MUST hold no more than 40 Chinese characters or 80 Latin characters. At 900 px and below, an item's source line, title, summary, and controls MUST stack in one column, in that order. A digest with only Creator updates MUST say that nothing could be summarized this time. The main screen and a saved digest opened from History MUST use the same layout.

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
- **THEN** both show the same headline, index, topics, items, marks, and Creator updates. They differ only in the masthead, the main screen's run bar, and the saved digest's link back to all digests

#### Scenario: Item with also-read links
- **WHEN** an item's summary used a GitHub release page and a changelog page
- **THEN** the item shows "Also read:" after its summary, with both titles linked, and opening a link leaves the digest open

#### Scenario: Item controls beside the summary
- **WHEN** a digest is opened in a 1440 px wide window
- **THEN** each topic item's Bookmark, Like, and Feedback controls sit under its title, beside its summary

#### Scenario: Item controls after the summary
- **WHEN** a digest is opened in a 420 px wide window
- **THEN** each topic item's controls follow its summary, and "Also read" when it has one

### Requirement: Keyboard and screen-reader support
The system SHALL support keyboard and assistive technology use:
- The skip link and the digest index MUST move keyboard focus to their targets, not only scroll.
- Generated digest text MUST carry the language it was written in.
- Run progress and the run result MUST be announced through one persistent status region.
- When a run's saved digest replaces the digest shown on the main screen, keyboard focus MUST NOT move, except when focus is on a control of an item in the replaced digest; then it moves as "Bookmark, like, and give feedback on digest items" says.
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
- **WHEN** a run finishes with a saved digest while the user is on the main screen, and focus is not on an item's control
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

## ADDED Requirements

### Requirement: Bookmark, like, and give feedback on digest items
The main screen, a saved digest opened from History, and the Bookmarks screen SHALL show these controls for each item in a topic. In reading order they follow the item's summary or "Summary unavailable", and "Also read" when it has one; "Digest reading layout" says where they sit on screen.
- **Bookmark** and **Like**: toggle buttons that show whether the item is bookmarked or liked. A pressed toggle MUST show a check mark and a stronger border, not only another color;
- **Feedback**, for an item with a summary: it shows and hides the item's feedback panel. When the summary has feedback, "Rated good" or "Rated poor" follows it.

Items in Creator updates have no controls. Each control's accessible name MUST include the item's title: "Bookmark <title>", "Like <title>", and "Feedback on <title>".

The feedback panel MUST:
- ask "How was this summary?", with the choices Good and Poor;
- offer "Note (optional)", with a hint that the note stays in CatchUp and holds up to 500 characters; the field MUST NOT accept more than 500 characters;
- show the saved rating and note when it opens;
- offer "Save feedback", which saves the rating and the note together. Without a chosen rating it MUST send nothing, show "Choose Good or Poor." as an alert linked to the choices, and mark them invalid;
- offer "Remove feedback" when feedback is saved;
- offer "Cancel", which closes the panel without saving.

When the panel closes through Save feedback, Remove feedback, or Cancel, focus MUST move to Feedback.

While a change is being saved, its control MUST stay focusable, be announced as unavailable, ignore activation, and look like a disabled button. A control MUST show its new state only once the change is saved. Results MUST be announced through a status region that is on the page, and empty, before the message appears: "Bookmarked.", "Bookmark removed.", "Liked.", "Like removed.", "Feedback saved.", or "Feedback removed.". A result that repeats the previous message MUST be announced again. The main screen's region for these results is not the run's status region. A change that fails MUST show the server's message as an alert at that item, and leave the control's state as it was.

When a run's saved digest replaces the digest on the main screen while one of the old digest's controls has focus, focus MUST move to Generate in the run bar. In a 320 px window, the controls and the open panel MUST fit without horizontal scrolling.

#### Scenario: Bookmark an item on the main screen
- **WHEN** the main screen shows digest No. 4, and the user activates "Bookmark Rust 2.0 released"
- **THEN** the button is shown as pressed once the bookmark is saved, "Bookmarked." is announced, and focus stays on the button

#### Scenario: Change in progress
- **WHEN** a keyboard user activates Like, and saving takes several seconds
- **THEN** Like keeps focus, is announced as unavailable, and activating it again sends no second request

#### Scenario: Feedback with the keyboard
- **WHEN** a keyboard user opens Feedback, chooses Poor, types a note, and activates Save feedback
- **THEN** the rating and note are saved together, the panel closes, focus is on Feedback, "Rated poor" follows it, and "Feedback saved." is announced

#### Scenario: No rating chosen
- **WHEN** the user opens Feedback on an unrated item and activates Save feedback without choosing Good or Poor
- **THEN** nothing is sent, "Choose Good or Poor." is announced as an alert and linked to the choices, and the choices are marked invalid

#### Scenario: Change fails
- **WHEN** the server refuses a bookmark with "Digest item not found."
- **THEN** that message is shown as an alert at the item, and Bookmark stays not pressed

#### Scenario: Summary unavailable
- **WHEN** a topic item's summary is unavailable
- **THEN** it shows Bookmark and Like, and no Feedback

#### Scenario: New digest while a control has focus
- **WHEN** focus is on Like in digest No. 12 on the main screen, and a run saves digest No. 13
- **THEN** digest No. 13 replaces No. 12, and focus is on Generate in the run bar

#### Scenario: Narrow window
- **WHEN** the window is 320 px wide, and an item's feedback panel is open
- **THEN** the controls and the panel fit, and the screen does not scroll horizontally

### Requirement: Bookmarks screen
The system SHALL offer a Bookmarks screen, reached from a "Bookmarks" link on the History screen. It SHALL show the bookmarked items as "List bookmarked items" in `digest-history` returns them, newest bookmark first. Each entry MUST show:
- its source kind, source name, and publish time;
- its title linked to the original;
- its summary, marked with the language of its digest, or "Summary unavailable";
- its images, unless images are turned off in Settings;
- its "Also read" links;
- a link "From No. <edition> · <date>" to its digest;
- its controls.

Removing a bookmark on this screen MUST keep the entry listed, with Bookmark not pressed, until the screen is opened again; focus stays on Bookmark. When nothing is bookmarked, the screen MUST say "No bookmarks yet" and link to the main screen. The screen's document title MUST name it "Bookmarks". The navigation keeps its four items, and MUST mark History as the current item on this screen.

#### Scenario: Open Bookmarks from History
- **WHEN** the user bookmarked an item of digest No. 3 and opens Bookmarks from History
- **THEN** the item is shown with its summary, its source, and "From No. 3" linked to that digest, and History is the current navigation item

#### Scenario: Remove a bookmark on the Bookmarks screen
- **WHEN** the user activates Bookmark on a listed entry
- **THEN** "Bookmark removed." is announced, the entry stays with Bookmark not pressed, focus stays on Bookmark, and the entry is gone the next time the screen is opened

#### Scenario: No bookmarks
- **WHEN** nothing is bookmarked and the user opens Bookmarks
- **THEN** the screen says "No bookmarks yet" and links to the main screen

#### Scenario: Chinese digest entry
- **WHEN** a bookmarked item comes from a digest written in Simplified Chinese
- **THEN** its summary is marked as Simplified Chinese
