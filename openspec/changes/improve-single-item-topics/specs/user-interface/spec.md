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

In windows wider than 1100 px, each item MUST be a row of its topic: its source line and linked title beside its summary. From 900 to 1100 px, an item's source line, title, and summary MUST stack within the item area, beside the topic's title and overview. At 900 px and wider, every item's summary MUST have the same width and end at the right edge of the content, whatever the summary's length, the item's position, or the number of items in the topic. In a 1440 px window, a summary line MUST hold no more than 40 Chinese characters or 80 Latin characters. Below 900 px of window width, an item's source line, title, and summary MUST stack in one column, in that order. A digest with only Creator updates MUST say that nothing could be summarized this time. The main screen and a saved digest opened from History MUST use the same layout.

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
