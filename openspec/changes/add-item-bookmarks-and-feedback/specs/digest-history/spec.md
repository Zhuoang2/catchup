## ADDED Requirements

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
