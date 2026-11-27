# digest-history Specification

## Purpose
Keeps every generated digest so the user can return to it later, browse past digests, and open the original items they link to.

## Requirements

### Requirement: List saved digests
The system SHALL list saved digests from newest to oldest, showing for each its edition number, its creation time, the number of items, the number of sources it covers, and the titles of its topics. A digest with only Creator updates SHALL be listed as such. The list MUST be available from a single request.

#### Scenario: Several digests
- **WHEN** the user opens the history after three digests were generated
- **THEN** the three digests are listed newest first with their times, item counts, and topic titles

#### Scenario: Creator updates only
- **WHEN** a saved digest has no topics and only Creator updates
- **THEN** the history lists it as containing only Creator updates

### Requirement: Reopen a saved digest
The system SHALL let the user open a saved digest and see:
- its edition number (the digest's sequence number), and its date and time
- its topics and each topic's overview
- for each summarized item: its summary, title, source name and source kind, publish date when known, a link to the original, and the "Also read" links of the context its summary used
- its Creator updates section when it has one, with each item's title, publish date when known, link, and reason, grouped by source with the source kind

The content shown MUST be the content that was saved, and MUST NOT be regenerated. The digest MUST record the language its summaries were written in, each item's source kind, and each item's "Also read" links, at the time it was saved. Later changes to the digest language setting or to a source MUST NOT change how a saved digest is presented. Digests saved before these were recorded are shown without a language mark, source kind, or "Also read" links.

#### Scenario: Open an older digest
- **WHEN** the user opens a digest from the history
- **THEN** the same topics, summaries, and links that were generated are shown, and the links open the original items

#### Scenario: Open a digest with Creator updates
- **WHEN** the user opens a saved digest whose Creator updates listed a podcast episode with "no transcript within 7 days", and the configured wait has since changed to 10 days
- **THEN** the episode is still shown with "no transcript within 7 days"

#### Scenario: Language changed after saving
- **WHEN** a digest was saved in Simplified Chinese and the digest language setting is later changed to English
- **THEN** reopening it still marks its summaries as Simplified Chinese

#### Scenario: Source deleted after saving
- **WHEN** a podcast source is deleted after a digest containing its episodes was saved
- **THEN** reopening the digest still shows those items as from a podcast

#### Scenario: Also-read links kept
- **WHEN** a saved digest's item used a linked changelog page, and that item's source is later deleted
- **THEN** reopening the digest still shows the changelog under "Also read"

### Requirement: Persist across restarts
Saved digests, sources, recorded items, and check outcomes SHALL survive an application restart.

#### Scenario: Restart
- **WHEN** the application is restarted
- **THEN** previously saved digests are still listed and open with their full content

### Requirement: Open the latest digest
The system SHALL return the newest saved digest from a single request, with the same content as reopening it (see "Reopen a saved digest"). "Newest" MUST follow the order of the saved-digest list: newest first, and the higher edition number first when two digests were saved at the same time. When no digest has been saved, the request MUST return an empty result rather than an error.

#### Scenario: Several digests
- **WHEN** digests No. 1, No. 2, and No. 3 have been saved, in that order
- **THEN** the latest-digest request returns digest No. 3 with its topics, items, and Creator updates, exactly as reopening No. 3 shows them

#### Scenario: No digest yet
- **WHEN** no digest has been saved
- **THEN** the latest-digest request succeeds and returns an empty result

#### Scenario: Same save time
- **WHEN** digests No. 2 and No. 3 have the same creation time
- **THEN** the latest-digest request returns digest No. 3

### Requirement: Saved digests keep their images
A saved digest SHALL record, for each summarized item, the URLs and alt texts of the images its summary chose, at the time it was saved. Reopening the digest MUST show the same images, and MUST NOT choose images again. Digests saved before images were recorded are shown without images.

#### Scenario: Reopen a digest with images
- **WHEN** a saved digest's item chose one screenshot, and the item's source is later deleted
- **THEN** reopening the digest still shows that screenshot under the item

### Requirement: Bookmark, like, and rate digest items
The system SHALL let the user mark each item in a saved digest's topics, including an item whose summary is unavailable:
- bookmark it, and remove the bookmark;
- like it, and remove the like;
- when it has a summary, give feedback on the summary: a rating of Good or Poor, with an optional note of up to 500 characters. The feedback can be replaced or removed.

The marks MUST belong to the item as it appears in that digest. Reopening a digest and the latest-digest request MUST return, for each item in its topics, an identifier and its marks: whether it is bookmarked, whether it is liked, its rating (or none), and its note (or none). Each change MUST answer with the item's marks.

Rules for changes:
- Items in Creator updates MUST NOT be marked. Such a request MUST be refused with `not_markable`.
- Feedback on an item whose summary is unavailable MUST be refused with `no_summary`.
- A rating other than Good or Poor, or a note longer than 500 characters once leading and trailing spaces are removed, MUST be refused with `invalid_feedback`, and nothing is changed.
- A note that is empty once spaces are removed MUST be stored as no note.
- A request for an unknown item MUST be refused with `not_found`.
- Bookmarking or liking an item that already has that mark, or removing a mark it does not have, MUST succeed and change none of its marks. Bookmarking again MUST keep the first bookmark's time.

Marks MUST NOT change the digest's saved content. They MUST NOT change what later runs collect, summarize, or group, and MUST NOT be sent to the model provider. Marks MUST survive restarts and the deletion of the item's source. They MUST be removed together with their digest item. Changes follow "Refuse write requests from other sites" in `model-settings`, and a browser connection token MUST NOT allow them.

#### Scenario: Bookmark and like an item
- **WHEN** the user bookmarks and likes an item of digest No. 4
- **THEN** reopening No. 4 returns that item as bookmarked and liked, with no rating and no note, and its other items unmarked

#### Scenario: Rate a summary with a note
- **WHEN** the user rates an item's summary Poor with the note "  Misses the price  "
- **THEN** the answer and reopening the digest return the rating Poor and the note "Misses the price"

#### Scenario: Replace and remove feedback
- **WHEN** an item's summary is rated Poor with a note, and the user then rates it Good without a note, and later removes the feedback
- **THEN** after the second change the item has the rating Good and no note, and after the removal it has no rating and no note, and stays bookmarked if it was

#### Scenario: Summary unavailable
- **WHEN** the user bookmarks an item whose summary is unavailable, and then rates its summary
- **THEN** the bookmark is saved, and the rating is refused with `no_summary`

#### Scenario: Creator updates
- **WHEN** a client tries to bookmark an item listed in Creator updates
- **THEN** the request is refused with `not_markable`

#### Scenario: Invalid feedback
- **WHEN** a client sends the rating "excellent", or a note of 501 characters
- **THEN** the request is refused with `invalid_feedback`, and the item's earlier feedback is unchanged

#### Scenario: Repeated bookmark
- **WHEN** an item was bookmarked at 09:00, and the user bookmarks it again at 10:00
- **THEN** the request succeeds, and the bookmark keeps the time 09:00

#### Scenario: Source deleted
- **WHEN** a bookmarked and rated item's source is deleted
- **THEN** reopening the digest still shows the item bookmarked, with its rating and note

#### Scenario: Marks do not reach the model
- **WHEN** items of earlier digests are bookmarked, liked, and rated, and a new run summarizes and groups new items
- **THEN** no request to the model provider contains a rating, a note, or a mark

#### Scenario: Request with a browser connection token
- **WHEN** a request that carries a valid browser connection token tries to bookmark an item
- **THEN** it is refused as cross-site, and the item stays unmarked

### Requirement: List bookmarked items
The system SHALL list bookmarked items from a single request, newest bookmark first, and the higher identifier first when two bookmarks have the same time. Each entry MUST hold the item as its digest saved it, in the same form as reopening that digest: title, link, source name and kind, publish time, summary or "summary unavailable", "Also read" links, and images. Each entry MUST also hold its marks, its bookmark time, and its digest's edition number, creation time, and language. An item whose bookmark is removed MUST leave the list. When nothing is bookmarked, the list MUST be empty.

#### Scenario: Two bookmarks
- **WHEN** the user bookmarks an item of digest No. 3, and then an item of digest No. 5
- **THEN** the list holds the item from No. 5 first, then the item from No. 3, each with its digest's edition number and date

#### Scenario: Bookmark removed
- **WHEN** one of two bookmarked items has its bookmark removed
- **THEN** the list holds only the other item

#### Scenario: Nothing bookmarked
- **WHEN** no item is bookmarked, including when some are liked or rated
- **THEN** the list is empty
