# user-interface Specification

## Purpose
Defines how CatchUp's interface presents its screens and states: a newspaper-style layout that reads well in both themes and at any window width, one clear action per state, and behavior that works for keyboard and screen-reader users.

## Requirements

### Requirement: One grid for masthead, navigation, and content
The system SHALL place the masthead, the navigation, and page content in one shared container whose left and right edges align on every screen. On wide windows the content uses a 12-column grid, and page content MUST NOT be centered independently of the masthead. Below 900 px of window width, content becomes a single column. Screens MUST NOT scroll horizontally at a width of 320 px. Text without break points, such as a long address in a title, MUST wrap inside its column instead of widening the screen.

#### Scenario: Wide window
- **WHEN** the user opens any screen in a 1440 px wide window
- **THEN** the left edge of the page headline aligns with the left edge of the masthead rule

#### Scenario: Narrow window
- **WHEN** the window is 420 px wide
- **THEN** content is a single column and the navigation fits on one row

#### Scenario: Long unbroken title at 320 px
- **WHEN** the window is 320 px wide, and a digest item, a Creator updates item, a run's source check, a source, or an entry in a source preview has a title with no break points, such as an X post that starts with a long address
- **THEN** the title wraps inside its column, and the screen does not scroll horizontally

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

### Requirement: Settings explain risk and keep secrets out of view
Settings SHALL group fields into Model provider, Digest, and YouTube, with separate groups for the browser extension and for X accounts.
- A saved API key, and a saved X token, MUST each be shown as text naming only its last four characters, never in an input placeholder.
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

### Requirement: Show chosen images from their source sites
In the digest reading layout, an item's chosen images SHALL appear under its summary, in the summary's column, in the order chosen. Each image MUST:
- load from its source site;
- load lazily, and send no referrer;
- show its text as a caption directly under it, in the digest's language, no wider than the column;
- be at most 320 px tall and no wider than the column.

Assistive technology MUST get each image's text once, as the caption of its figure: the image itself MUST NOT repeat the text. An image whose text is empty MUST NOT be shown. Digests saved before captions were shown SHALL show their stored text as the caption.

An image that fails to load MUST be hidden together with its caption, without leaving an empty frame. Settings SHALL offer "Show images from source sites" in the Digest group, on by default. Its note MUST say that opening a digest then contacts those sites, and MUST be associated with the toggle for assistive technology. When it is off, the digest MUST NOT request any image, and MUST NOT show captions.

An image whose address names this computer or a device on a local network, by the rules of "Keep image candidates for items" in `content-collection`, MUST NOT be shown or requested. This includes images recorded in digests saved before that rule. An image whose address is a rendered formula, by the same requirement's rules, MUST NOT be shown or requested either, including in digests saved before that rule.

#### Scenario: Item with two chosen images
- **WHEN** an item chose a chart and a screenshot
- **THEN** both appear under its summary in that order, each with its caption under it

#### Scenario: Caption read once
- **WHEN** an item chose a chart whose text is "Sales doubled after the redesign: the chart the post's argument rests on"
- **THEN** that text is shown under the chart, assistive technology reads it once as the figure's caption, and the image itself has no text of its own

#### Scenario: Digest saved before captions
- **WHEN** the user opens a digest saved before this change, whose item recorded an image with the text "SVG of a pelican riding a bicycle, drawn by a model at its highest reasoning level"
- **THEN** that text is shown under the image as its caption

#### Scenario: Image without text
- **WHEN** a saved digest's item recorded one image with an empty text and one with a text
- **THEN** only the image with a text is shown

#### Scenario: Image no longer available
- **WHEN** a chosen image's URL answers 404
- **THEN** that image and its caption are hidden, and the rest of the item is unchanged

#### Scenario: Images turned off
- **WHEN** the user turns off "Show images from source sites" and opens a digest whose items chose images
- **THEN** no image or caption is shown, and no image is requested

#### Scenario: Saved digest with a local image
- **WHEN** a digest saved earlier recorded `http://192.168.1.1/cam.jpg` and a public image for one item, and the user opens it
- **THEN** only the public image is shown, and `http://192.168.1.1/cam.jpg` is never requested

#### Scenario: Saved digest with a formula image
- **WHEN** a digest saved earlier recorded `https://s0.wp.com/latex.php?latex=%7BT%7D` and a chart for one item, and the user opens it
- **THEN** only the chart is shown, and the formula image is never requested

### Requirement: Connect a browser in Settings
Settings SHALL have a "Browser extension" group with:
- "Connect a browser", which asks for the browser's name;
- the new token, shown once in a read-only field with a Copy button, and a note that it is shown only once;
- the list of connected browsers, each with its name, connection date, last use, and "Disconnect".

The token field and the note MUST be associated for assistive technology, and copying MUST announce its result.

#### Scenario: Copy the token
- **WHEN** the user connects a browser and chooses Copy
- **THEN** the token is copied, and the result is announced

### Requirement: Ask for the X token where it is needed
When a preview on the Sources page reports that an X token is needed, the page SHALL show, in place, a password field for the token, a link to how to get one, and "Save and preview". Saving MUST store the token as Settings does, then preview the same address again. The field and its explanation MUST be associated for assistive technology, and the result MUST be announced.

Settings SHALL have an "X accounts" group with the token field, "Test", "Remove", and "Delete all X data". "Delete all X data" MUST ask for confirmation in place, say that it also removes followed accounts' items from saved digests, and say that pages saved from X with the extension stay. The group SHALL say that reads are billed to the user's X developer account, and that a spending limit can be set in the X console.

#### Scenario: Token asked in place
- **WHEN** no X token is saved and the user previews `https://x.com/simonw` on the Sources page
- **THEN** the page asks for the token in place, and after "Save and preview" shows the account's preview

#### Scenario: First run with X
- **WHEN** no model key and no X token are saved, and the user opens Settings
- **THEN** the "X accounts" group is optional, and saving the model settings does not require an X token

### Requirement: Show Settings save results at Save
When the user clicks **Save** in Settings, the result SHALL appear in the save bar next to Save. The save bar MUST contain a status region that is on the page, empty, before any result.
- Success MUST be announced through that status region.
- An error that belongs to no field MUST be shown and announced as an alert in the save bar, and nowhere else on the page.
- An error that belongs to a field MUST mark that field invalid, with its message linked to the field and announced as an alert. The save bar's status region MUST then say that the settings were not saved, and name the field. These errors belong to fields:
  - a missing model belongs to the Model select;
  - an invalid provider address belongs to the Base URL field;
  - an invalid language belongs to the Other language field;
  - a missing or rejected key belongs to the API key field.
- When the model settings were saved, but the Digest and YouTube settings were not, the save bar MUST say so, and why. The page MUST then show the saved key as saved and clear the key field.
- When Settings cannot be loaded, the error MUST be shown at the top of the page.

#### Scenario: Save before choosing a model
- **WHEN** no model has been listed or chosen, and the user clicks Save
- **THEN** the Model select is marked invalid and linked to a message that says to test the connection and choose a model, and the save bar says that the settings were not saved and names the Model field

#### Scenario: Server without an instance secret
- **WHEN** the user saves a new key, and the server refuses because its instance secret is not configured
- **THEN** the save bar shows and announces "Set CATCHUP_SECRET_KEY on the server before saving an API key.", and the message appears nowhere else on the page

#### Scenario: Settings saved
- **WHEN** Save succeeds
- **THEN** the save bar's status region, which was on the page before the click, announces "Settings saved."

#### Scenario: Model saved, other settings refused
- **WHEN** the model settings are saved with a new key ending in "3f9a", but saving the Digest and YouTube settings fails because the server cannot be reached
- **THEN** the save bar says that the model settings were saved but the Digest and YouTube settings were not, and why, the page reads "Saved key ending in 3f9a", and the key field is empty

#### Scenario: Settings cannot be loaded
- **WHEN** loading the settings fails
- **THEN** the error is shown at the top of the page, above the Model provider group

### Requirement: Keep focus and announcements when content changes in place
The web interface SHALL keep keyboard focus and screen-reader announcements when part of a page changes in place.
- **Busy controls.** While a run is in progress, the main screen's Generate / Try again button MUST stay focusable and be announced as unavailable. Activating it MUST do nothing. It MUST look the same as a disabled button.
- **Removed controls.** When an action removes the control that has focus, focus MUST move to this target:
  - "Delete all X data" in Settings: Cancel in its confirmation;
  - Cancel in that confirmation: "Delete all X data";
  - Delete X data, after the deletion succeeds: the X accounts heading;
  - Disconnect for a browser, after it succeeds: the "Connected browsers" heading;
  - "Save and preview" on the Sources page: the preview's heading when the preview is shown, otherwise the address field;
  - Confirm source, after the source is saved, and Cancel in the preview: the address field;
  - when the first digest replaces the Generate screen while Generate has focus: Generate in the run bar;
  - Generate, when the server answers that no model is set up: "Set up your model".

  While the Sources page repeats the preview after "Save and preview", the X token form MUST stay on the page, so focus does not fall to the page before the preview answers.
- **Announcements.** Result messages in Settings and on the Sources page MUST be announced through status regions that are on the page, empty, before the message appears. An empty status region MUST take no visible space. Errors MUST be announced as alerts.

#### Scenario: Generate keeps focus during a run
- **WHEN** a keyboard user presses Generate digest and the run starts
- **THEN** focus stays on the button, the button is announced as unavailable while the run is in progress, and pressing it again starts no second run

#### Scenario: Delete all X data with the keyboard
- **WHEN** a keyboard user chooses "Delete all X data", then Cancel
- **THEN** focus moves to Cancel in the confirmation, then back to "Delete all X data"

#### Scenario: X data deleted
- **WHEN** the user confirms the deletion of all X data, and it succeeds
- **THEN** focus moves to the X accounts heading, and the counts are announced through a status region that was on the page before

#### Scenario: Save and preview on the Sources page
- **WHEN** the user saves the X token from the Sources page, and the preview loads
- **THEN** focus moves to the preview's heading, and "X token saved." is announced through a status region that was on the page before

#### Scenario: Confirm a source
- **WHEN** the user confirms a source preview, and the source is saved
- **THEN** the address field is empty and has focus, and "Source saved." is announced

#### Scenario: First digest replaces the Generate screen
- **WHEN** the first digest is saved while Generate has focus on the Generate screen
- **THEN** the digest is shown, and focus is on Generate in the run bar

#### Scenario: Generate finds no model set up
- **WHEN** a keyboard user presses Generate digest, and the server answers that no model is set up
- **THEN** the page shows the first-run actions, and focus is on "Set up your model"

### Requirement: Show preview progress, and only the current address's preview
On the Sources page, while a preview loads, Preview SHALL stay focusable and be announced as unavailable, and activating it, including pressing Enter in the address field, MUST do nothing. The page MUST announce "Loading the preview…" through its status region. "Save and preview" in the X token form MUST behave the same way while it works.

Editing the address MUST end the wait: Preview becomes available again, the loading message is removed, and the pending answer is ignored. A preview or an error MUST be shown only when it answers the address the field shows, so that Confirm saves a preview of that address. When the X token is saved but the address changed before the preview started, the page MUST NOT preview the old address, and MUST announce "X token saved." unless a newer preview is loading; then its loading message stays.

#### Scenario: Preview loading
- **WHEN** a keyboard user presses Preview, and the answer takes several seconds
- **THEN** focus stays on Preview, which is announced as unavailable, "Loading the preview…" is announced, and pressing Preview again sends no second request

#### Scenario: Address changed while loading
- **WHEN** the user previews address A, changes the field to address B and previews it, and A answers after B
- **THEN** the page shows B's preview, and Confirm saves B's feed

#### Scenario: Error for an earlier address
- **WHEN** the user previews address A, then changes the field before A's preview fails
- **THEN** A's error is not shown, the loading message is gone, and Preview is available

### Requirement: Choose linked pages in Settings
Settings SHALL offer "Linked pages" in the Digest group: a choice of Off, Shallow, Normal, and Deep, the levels of "Choose how many linked pages a run reads" in `content-collection`. It MUST show the saved level, and Normal when none was saved.
- Off MUST be labeled "Off — no linked pages or author replies".
- Shallow, Normal, and Deep MUST each name how many pages per item they read, with the numbers the server uses, as "Shallow — up to N pages per item", "Normal — up to N pages per item", and "Deep — up to N pages per item".
- A note MUST say that each page read adds time to a run and up to 3,000 characters to that item's summary request (6,000 at Deep, and up to 4,000 for author replies), which uses more tokens, and MUST name the run's limit of page requests at Shallow and Normal and at Deep, robots.txt files included, with the numbers the server uses. It MUST be associated with the choice for assistive technology.

The choice MUST be saved by Save, together with the other Digest settings, and its result shown as "Show Settings save results at Save" describes.

#### Scenario: Default choice
- **WHEN** no level was saved, the server uses its default numbers, and the user opens Settings
- **THEN** "Linked pages" shows "Normal — up to 8 pages per item", its other options read "Off — no linked pages or author replies", "Shallow — up to 3 pages per item", and "Deep — up to 16 pages per item", and its description names 6,000 characters per page at Deep and a limit of 60 page requests per run, 120 at Deep

#### Scenario: Server numbers
- **WHEN** the server's `CATCHUP_LINKS_PER_ITEM` is 5 and `CATCHUP_CONTEXT_FETCHES_PER_RUN` is 40, and the user opens Settings
- **THEN** the options read "Shallow — up to 3 pages per item", "Normal — up to 5 pages per item", and "Deep — up to 10 pages per item", and the description names a limit of 40 page requests per run, 80 at Deep

#### Scenario: Save Off
- **WHEN** the user chooses Off and clicks Save
- **THEN** Off is saved with the other Digest settings, "Settings saved." is announced, and Settings shows Off when it is opened again

#### Scenario: Save Deep
- **WHEN** the user chooses Deep and clicks Save
- **THEN** Deep is saved with the other Digest settings, "Settings saved." is announced, and Settings shows Deep when it is opened again

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
