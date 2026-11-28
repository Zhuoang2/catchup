## ADDED Requirements

### Requirement: Choose how many items a digest shows
Settings SHALL offer "Items to show" in the Digest group, after "Linked pages", with these options: "All items", the default, "The 5 most important", "The 10 most important", "The 20 most important", and "The 30 most important". It MUST show the saved choice, and All items when none was saved. A note MUST say that each summary also rates how important its item is, from 1 to 5; that a digest with more items in its topics than the choice shows only the most important ones, with a button that shows the rest; that Creator updates are always shown; and that digests saved before ratings show every item. The note MUST be associated with the choice for assistive technology.

The choice MUST be saved by Save, together with the other Digest settings, and its result shown as "Show Settings save results at Save" describes. The server MUST refuse any value other than these five, and keep the saved choice.

#### Scenario: Default choice
- **WHEN** no choice was saved and the user opens Settings
- **THEN** "Items to show" shows "All items", its other options are the 5, 10, 20, and 30 most important, and its description is the note

#### Scenario: Save a number
- **WHEN** the user chooses "The 10 most important" and clicks Save
- **THEN** the choice is saved with the other Digest settings, "Settings saved." is announced, and Settings shows "The 10 most important" when it is opened again

#### Scenario: Value refused
- **WHEN** a preferences request asks for 7 items, or for the value false
- **THEN** the server refuses it, and the saved choice does not change

### Requirement: Show only the most important items
When "Items to show" is a number, the main screen and a saved digest opened from History SHALL show only that many of a digest's topic items, if the digest has more topic items than the number and at least one of them is rated (see "Saved digests keep each item's importance" in `digest-history`). The items shown are chosen by rank:
- rated items rank by their rating, highest first; an unrated item with a summary ranks as 3, and an item whose summary is unavailable ranks below 1;
- items of equal rank keep the digest's reading order.

The shown items MUST stay in their topics, in the digest's order. A topic with no shown item MUST be left out, and so MUST its index entry; each index entry MUST count the topic's shown items. Creator updates MUST always be shown in full, and MUST NOT count toward the number. The headline's item count MUST stay the digest's full count.

Under the headline, a line MUST say "Showing the N most important of the M items in topics.", where N is the choice and M counts the items in the digest's topics, followed by a button "Show all M". Activating the button MUST show every item, change the line to "Showing all M items in topics.", and change the button to "Show the N most important", which limits the digest again. Focus MUST stay on the button, and the digest's status region MUST announce the new line. Each opening of a digest, and each new digest on the main screen, MUST start limited. When a run's saved digest replaces the digest on the main screen while this button has focus, focus MUST move to Generate in the run bar.

A digest with no more topic items than the choice, or with no rated topic item, MUST be shown in full, without the line. The Bookmarks screen MUST NOT be limited. When the saved choice cannot be read, digests MUST be shown in full.

#### Scenario: Limited digest
- **WHEN** "Items to show" is 5, and a digest has the topics Alpha (items rated 2 and 5), Beta (items rated 1 and 1), and Gamma (an item rated 4, an unrated item with a summary, an item whose summary is unavailable, and an item rated 3), and two Creator updates
- **THEN** the digest shows Alpha with both items, and Gamma with its items rated 4, unrated, and 3, in that order; Beta and the unavailable item are not shown; the index lists Alpha with 2, Gamma with 3, and Creator updates with 2; both Creator updates are shown; the headline still says 10 items; and the line says "Showing the 5 most important of the 8 items in topics." with a button "Show all 8"

#### Scenario: Show all
- **WHEN** the user activates "Show all 8" in that digest
- **THEN** all 8 topic items and Beta are shown, the line says "Showing all 8 items in topics.", focus is on the button, which reads "Show the 5 most important", and the status region announces "Showing all 8 items in topics."

#### Scenario: Short digest
- **WHEN** "Items to show" is 5, and a digest has 5 rated topic items
- **THEN** every item is shown, and there is no line or button

#### Scenario: Digest saved before ratings
- **WHEN** "Items to show" is 5, and the user opens a digest with 8 topic items saved before ratings existed
- **THEN** every item is shown, and there is no line or button

#### Scenario: New digest starts limited
- **WHEN** the user showed every item of the digest on the main screen, and a run's new digest with 8 rated topic items replaces it while focus is elsewhere
- **THEN** the new digest shows its 5 most important topic items and the line

#### Scenario: Show all has focus when a new digest arrives
- **WHEN** a run's saved digest replaces the digest on the main screen while "Show all 8" has focus
- **THEN** focus is on Generate in the run bar

#### Scenario: Choice cannot be read
- **WHEN** "Items to show" is 5, and the preferences request fails while a saved digest is opened from History
- **THEN** every item of the digest is shown, and there is no line or button

#### Scenario: Bookmarks
- **WHEN** "Items to show" is 5, and 8 items are bookmarked
- **THEN** the Bookmarks screen lists all 8

## MODIFIED Requirements

### Requirement: Keyboard and screen-reader support
The system SHALL support keyboard and assistive technology use:
- The skip link and the digest index MUST move keyboard focus to their targets, not only scroll.
- Generated digest text MUST carry the language it was written in.
- Run progress and the run result MUST be announced through one persistent status region.
- When a run's saved digest replaces the digest shown on the main screen, keyboard focus MUST NOT move, except when focus is on a control of an item in the replaced digest, or on its button that shows all items or the most important ones; then it moves as "Bookmark, like, and give feedback on digest items" and "Show only the most important items" say.
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
- **WHEN** a run finishes with a saved digest while the user is on the main screen, and focus is not on an item's control or on the button that shows all items or the most important ones
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
