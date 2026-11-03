## MODIFIED Requirements

### Requirement: Summarize items once and group them by topic
The system SHALL summarize each item that has text for summarization individually, and reuse a stored summary instead of summarizing the same item again. It SHALL then group the summarized items into topics, each with a title and a short overview. Every item in the run MUST appear in the digest exactly once: either in a topic or under Creator updates. Summarized items the grouping does not place MUST appear under an "Other" topic. When the grouping cannot be completed, because its model calls still fail after retries or its answer has no valid list of topics, the run MUST NOT fail: all of its summarized items MUST appear under one "Other" topic ("其他" in a Chinese digest), in the order the run lists them. A rejected API key or insufficient balance during grouping MUST still fail the run (see "Retry transient model errors"). A summary produced before an item's transcript was found MUST NOT be reused once the transcript replaces the item's text. An item whose summary could not be produced after retries MUST still appear with its title and link and a note that its summary is unavailable.

#### Scenario: Retry after failure
- **WHEN** a run fails during grouping because the provider rejects the API key, and the user starts a new run
- **THEN** items summarized in the failed run are not summarized again

#### Scenario: Item missing from grouping
- **WHEN** the model's grouping omits an item
- **THEN** that item appears under "Other" in the saved digest

#### Scenario: Grouping cannot be completed
- **WHEN** a run has summarized 2 items, and the grouping answer has no list of topics, or every attempt of the grouping call answers JSON that is cut off
- **THEN** the run saves a digest with one "Other" topic holding both items, the items are delivered, and the next run does not group them again

#### Scenario: Transcript found after an earlier summary
- **WHEN** an item was summarized from its description in a failed run and a later run finds its transcript
- **THEN** the item is summarized again from the transcript

### Requirement: Retry transient model errors
The system SHALL retry model calls that return empty content, rate-limit errors, or temporary server errors, with backoff and a bounded number of attempts. Temporary server errors are HTTP 500, 502, 503, and 504. An answer that is not valid JSON, that is JSON but not an object, or that is not a chat completion with text content, such as an HTML or plain-text page sent with status 200, MUST be retried like empty content. Such an answer MUST NOT fail the run by itself. Authentication and insufficient-balance errors MUST fail the run immediately with a message telling the user to fix the configuration.

#### Scenario: Empty model response
- **WHEN** a model call returns empty content once and valid content on retry
- **THEN** the run continues using the valid content

#### Scenario: Gateway error
- **WHEN** a model call answers HTTP 502 or 504 once and valid content on retry
- **THEN** the run continues using the valid content

#### Scenario: Answer that is not JSON
- **WHEN** an item's summary call answers status 200 with a plain-text page once, and valid content on retry
- **THEN** the item's summary is saved from the valid content

#### Scenario: Bad answers on every attempt
- **WHEN** every attempt of one item's summary call answers status 200 with an HTML page
- **THEN** that item appears with a note that its summary is unavailable, and the run saves the digest

#### Scenario: Rejected key during a run
- **WHEN** the provider rejects the API key during a run
- **THEN** the run fails immediately, its items remain pending, and the user is told to check the model settings

## ADDED Requirements

### Requirement: Fit topic grouping in the model's context window
When the model's context window is known, the system SHALL size topic grouping calls from it, counting one character per token:
- each grouping call's output budget is the usual grouping budget, but at most half the context window;
- the items are split into batches whose text fits in the rest of the window after a fixed prompt allowance. Each batch is grouped, and then the batch topics are combined in one more call.

The instance's grouping batch setting MUST remain an upper limit on a batch's text. When the context window is unknown, batches MUST be limited by that setting alone, as before. The call that combines batch topics is not split; when it cannot be completed, the grouping falls back to one "Other" topic (see "Summarize items once and group them by topic").

#### Scenario: Small context window
- **WHEN** the provider reports an 8,192-token context window, and a run groups 60 items whose summaries total about 36,000 characters
- **THEN** no grouping call asks for more than 4,096 output tokens, no batch's text is longer than 2,096 characters, and every item appears once in the digest

#### Scenario: Unknown context window
- **WHEN** no context window is known, and a run groups the same 60 items
- **THEN** the items are grouped in one call, as before

#### Scenario: Large context window
- **WHEN** the provider reports a 1,000,000-token context window
- **THEN** a batch's text is limited by the instance's grouping batch setting, 200,000 characters by default
