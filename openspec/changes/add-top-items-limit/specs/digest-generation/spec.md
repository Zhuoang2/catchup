## ADDED Requirements

### Requirement: Rate each item's importance
The call that writes an item's summary SHALL also ask the model to rate the item's importance as a whole number from 1 to 5, on this scale: 5 a major release, finding, decision, or event; 4 a significant development; 3 a useful update; 2 a minor or routine update; 1 little or no substance, such as a bare link or a promotion. For a long text that is summarized in parts, the rating comes from the call that combines the parts. No model call is added for the rating.
- The rating MUST be stored with the item's summary, and reused whenever the summary is reused (see "Summarize items once and group them by topic").
- A rating that is missing, or that is not a whole number from 1 to 5, MUST leave the item unrated. The summary is kept, and the call is not repeated.
- An item whose summary is unavailable, an item listed under Creator updates, and an item whose stored summary was written before ratings existed have no rating.
- Ratings MUST NOT change which items a run includes, how they are grouped into topics, or their order.

#### Scenario: Rated item
- **WHEN** an item's summary call answers a summary and the rating 4
- **THEN** the saved digest has the summary and records the rating 4 for that item

#### Scenario: Invalid rating
- **WHEN** an item's summary call answers a summary with the rating 7, "4", 4.5, true, or no rating
- **THEN** the call is made once, the saved digest has the summary, and the item is unrated

#### Scenario: Rating kept with a reused summary
- **WHEN** an item was summarized with the rating 5 in a run that failed during grouping, and the next run reuses its summary
- **THEN** the next run makes no summary call for the item, and its digest records the rating 5

#### Scenario: Summary unavailable
- **WHEN** an item's summary could not be produced after retries
- **THEN** the item appears with its title, link, and a note that its summary is unavailable, and it is unrated

#### Scenario: Summary written before ratings
- **WHEN** a pending item has a stored summary in the chosen language that was written before ratings existed
- **THEN** the run reuses the summary without a call, and the item is unrated
