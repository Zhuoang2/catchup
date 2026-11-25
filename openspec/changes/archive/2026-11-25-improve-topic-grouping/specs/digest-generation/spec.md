## ADDED Requirements

### Requirement: Group related items into broad topics
The grouping call SHALL ask the model:
- to put items about the same subject (such as one company, product, event, or field) in one topic, even when they come from different sources;
- to prefer fewer, broader topics, and to use at most the topic limit;
- to give an item a topic of its own only when it fits no other topic;
- to title each topic with the subject its items share;
- to write each overview in 1–2 sentences about what the topic's items cover together, without repeating each item's summary.

The topic limit for a number of items is the smallest whole number at least the square root of twice that number, but never more than the number of items or 12. For example, 1 item gives 1, 2 items give 2, 7 give 4, 11 give 5, 30 give 8, and 61 or more give 12. A grouping call with one item SHALL ask for one topic, in place of the second and third points above.

When items are grouped in batches:
- each batch call SHALL use the limit for its own items;
- the call that combines batch topics SHALL ask the model to combine batch topics about the same subject, to prefer fewer, broader final topics and use at most the limit for all the items being grouped, to keep a batch topic on its own only when it fits no other final topic, and to title each final topic with the subject its batch topics share and write its overview in 1–2 sentences about what they cover together;
- that call SHALL receive the number of items in each batch topic.

The limit is guidance for the model only. A grouping answer with more topics than the limit MUST be saved as the model answered, under the rules of "Summarize items once and group them by topic". No item may be dropped, moved, or merged because of the limit, and no further model call may be made because of it.

#### Scenario: Related items from different sources
- **WHEN** a run groups 7 summarized items, two of them about the same company from two different sources
- **THEN** the grouping call asks for at most 4 topics, and asks to put items about the same subject in one topic even when they come from different sources

#### Scenario: Model returns more topics than the limit
- **WHEN** a run groups 7 items and the model answers with 6 topics that together place every item once
- **THEN** the saved digest has those 6 topics in the model's order, each item appears once, and the run makes no further model call for grouping

#### Scenario: One item
- **WHEN** a run groups 1 item
- **THEN** the grouping call asks for one topic

#### Scenario: Batched grouping
- **WHEN** 10 items are grouped in three batches of 4, 4, and 2 items
- **THEN** the batch calls ask for at most 3, 3, and 2 topics, and the combining call asks for at most 5 final topics and states how many items each batch topic holds
