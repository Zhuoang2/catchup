# digest-generation Specification

## Purpose
Turns everything new since the last delivered digest into a topic-grouped digest with summaries and citations to the original items, generated on demand in the background with visible progress.

## Requirements

### Requirement: Start a digest run on demand
The system SHALL start a digest run only when the user requests one. At most one run MAY be active at a time. A request made while a run is active MUST be refused and point to the active run.

#### Scenario: Start a run
- **WHEN** the user clicks Generate Digest and no run is active
- **THEN** a run starts and the user can follow its progress

#### Scenario: Run already active
- **WHEN** the user requests a run while another run is active
- **THEN** the request is refused and the response identifies the active run

### Requirement: Show run progress and per-source outcomes
While a run is active, the system SHALL report its stage (collecting, summarizing, grouping), how many items have been summarized out of the total, and each source's check outcome as it becomes known. While the context pass runs, it SHALL also report how many context fetches are done out of the number planned.

#### Scenario: Following progress
- **WHEN** the user views an active run that is summarizing 12 items, 5 of them done
- **THEN** the user sees the summarizing stage and "5 of 12"

#### Scenario: Reading linked pages
- **WHEN** every source is checked and the run has read 7 of 20 planned linked pages
- **THEN** the user sees "Linked pages read: 7 of 20"

### Requirement: Include every pending item
A run SHALL include every item that is new and has not appeared in any saved digest, with no limit on the number of items. There is one exception: a podcast episode still waiting for its transcript (see the `transcripts` capability) is held back. It is included once a transcript is found or its wait ends. YouTube items are also held back while they are in their caption wait, or when their captions are not yet fetched because of the per-run caption limit. They are included once captions are found or the wait ends. Items MUST be marked as delivered only when the digest containing them is saved. Each item MUST appear in at most one saved digest.

#### Scenario: Long gap
- **WHEN** 140 items are pending at the start of a run and none is waiting for a transcript
- **THEN** the saved digest covers all 140 items

#### Scenario: Run fails before saving
- **WHEN** a run fails after some items were summarized but before the digest is saved
- **THEN** all of the run's items remain pending for the next run

#### Scenario: Episode waiting for a transcript
- **WHEN** a run starts one day after a podcast episode was first recorded and the episode still has no transcript
- **THEN** the episode does not appear in that run's digest and stays pending

#### Scenario: Item never repeated
- **WHEN** an item appeared in a saved digest, either summarized or under Creator updates
- **THEN** it does not appear in any later digest

### Requirement: No digest when nothing is new
When a run finds no pending items to include, the system SHALL NOT save a digest. It MUST tell the user that there is no new content and show the sources whose check failed or flagged a possible gap. When podcast episodes or YouTube videos are being held back for transcripts or captions, or YouTube videos are deferred to a later run, the message MUST state how many.

#### Scenario: Nothing new and one failure
- **WHEN** a run finds no pending items and one source failed
- **THEN** no digest is saved and the user sees "no new content" together with the failed source and its error

#### Scenario: Only waiting episodes
- **WHEN** the only pending items are 2 podcast episodes waiting for transcripts
- **THEN** no digest is saved and the user sees "no new content" and "2 items waiting for transcripts or captions"

### Requirement: Summarize items once and group them by topic
The system SHALL summarize each item that has text for summarization individually, and reuse a stored summary instead of summarizing the same item again. It SHALL then group the summarized items into topics, each with a title and a short overview. Every item in the run MUST appear in the digest exactly once: either in a topic or under Creator updates. Summarized items the grouping does not place MUST appear under an "Other" topic. When the grouping cannot be completed because the model's answers are still unusable after retries (no valid list of topics, invalid or cut-off JSON, or an answer that is not a chat completion), the run MUST NOT fail: all of its summarized items MUST appear under one "Other" topic ("其他" in a Chinese digest), in the order the run lists them. A rejected API key, insufficient balance, rate limiting, a failed connection, or an HTTP error status that persists after retries during grouping MUST still fail the run, and its items stay pending, so a later run can summarize or group them (see "Retry transient model errors"). A summary produced before an item's transcript was found MUST NOT be reused once the transcript replaces the item's text. An item whose summary could not be produced after retries MUST still appear with its title and link and a note that its summary is unavailable.

#### Scenario: Retry after failure
- **WHEN** a run fails during grouping because the provider rejects the API key, and the user starts a new run
- **THEN** items summarized in the failed run are not summarized again

#### Scenario: Item missing from grouping
- **WHEN** the model's grouping omits an item
- **THEN** that item appears under "Other" in the saved digest

#### Scenario: Grouping cannot be completed
- **WHEN** a run has summarized 2 items, and the grouping answer has no list of topics, or every attempt of the grouping call answers JSON that is cut off
- **THEN** the run saves a digest with one "Other" topic holding both items, the items are delivered, and the next run does not group them again

#### Scenario: Every model call fails with a server error
- **WHEN** every summary and grouping call in a run answers HTTP 500, or every one answers 404 because the model ID is wrong
- **THEN** the run fails with a provider error, no digest is saved, and the items stay pending for the next run

#### Scenario: Transcript found after an earlier summary
- **WHEN** an item was summarized from its description in a failed run and a later run finds its transcript
- **THEN** the item is summarized again from the transcript

### Requirement: Citations come from stored data
Every item in a digest MUST show its source name and original link taken from stored item and source records. The links an item shows for the context its summary used MUST come from the stored context, never from the model's text. Item references produced by the model that do not match an item in the run MUST be discarded.

#### Scenario: Model returns an unknown item reference
- **WHEN** the grouping output references an item that is not in the run
- **THEN** the reference is ignored and no link is invented for it

#### Scenario: Context link comes from stored context
- **WHEN** a summary used a linked page
- **THEN** the digest shows that page's stored title and URL

### Requirement: Digest language chosen by the user
The system SHALL let the user choose the digest language in the settings shown during initial setup. The options are English, Simplified Chinese, "same as the original", or another language the user types. Summaries, topic titles, and overviews MUST be written in the chosen language. With "same as the original", each item summary uses that item's language, and topic text uses the language most items are written in. A stored item summary MUST be reused only if it was written in the currently chosen language. Changing the language MUST NOT alter saved digests.

#### Scenario: Choose Chinese at setup
- **WHEN** the user selects Simplified Chinese in settings and generates a digest
- **THEN** the digest's summaries, topic titles, and overviews are in Simplified Chinese

#### Scenario: Change language after earlier runs
- **WHEN** an item was summarized in English, the user switches the language to Simplified Chinese, and the item is included in a later run
- **THEN** the item is summarized again in Simplified Chinese, and digests saved earlier remain in English

### Requirement: Require model setup before generating
The system SHALL refuse to start a run while no model configuration is saved, and direct the user to the settings.

#### Scenario: Generate before setup
- **WHEN** the user clicks Generate Digest before saving a model configuration
- **THEN** no run starts and the user is told to complete the model settings first

### Requirement: Recover from interrupted runs
On startup, the system SHALL mark any run left unfinished as failed. Its items MUST remain pending.

#### Scenario: Restart during a run
- **WHEN** the application restarts while a run is summarizing
- **THEN** after restart that run shows as failed and a new run can include its items

### Requirement: Work with reasoning models by default
The system SHALL request output budgets large enough that a provider's default reasoning mode does not leave summary or grouping responses empty.

#### Scenario: Provider reasons before answering
- **WHEN** the configured model reasons before producing output, as DeepSeek does by default
- **THEN** item summaries and topic grouping still return content within the requested budget

### Requirement: Summaries focus on substance
Item summaries SHALL be 2–4 sentences about the item's substance, except for long transcripts as described below. They MUST NOT include platform identifiers, user handles, submission metadata, or timestamps unless essential to the meaning. An item without substantive content MUST be described in one short sentence saying so. A transcript longer than the configurable long-item threshold (default 20,000 characters) SHALL be summarized as a 2–3 sentence overview followed by 3–6 key points. Summaries of transcripts MUST NOT describe visual content.

#### Scenario: Social post with metadata
- **WHEN** an item is a social post whose feed text includes the author handle and a platform identifier
- **THEN** the summary describes what the post says and omits the identifier and handle

#### Scenario: Long episode transcript
- **WHEN** an item's transcript is 170,000 characters long
- **THEN** its summary is an overview followed by 3–6 key points

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

### Requirement: Creator updates
A saved digest SHALL contain a "Creator updates" section after the topic summaries whenever the run includes items that cannot be summarized because no transcript is available. The section MUST group these items by source (the creator or show). For each item it MUST show:
- the title
- the publish time when known
- the link
- one reason:
  - caption fetching is off
  - the video has no captions
  - blocked by YouTube
  - captions could not be fetched
  - no transcript within N days, where N is the wait in effect when the digest was saved

A digest MUST be saved when the run includes only such items. It then contains only the Creator updates section. The system MUST NOT call the model for these items, and MUST NOT show their show notes or descriptions.

#### Scenario: Channel with caption fetching off
- **WHEN** caption fetching is off and a run includes 3 new videos from one YouTube channel
- **THEN** the digest's Creator updates section lists the 3 videos under that channel with the reason "caption fetching is off", and no model call is made for them

#### Scenario: Episode past the transcript wait
- **WHEN** a podcast episode still has no transcript when its wait ends
- **THEN** the next saved digest lists it once under Creator updates with the reason "no transcript within 7 days" under the default wait

#### Scenario: Only Creator updates
- **WHEN** a run's only includable items are 2 videos with caption fetching off
- **THEN** a digest is saved that contains only the Creator updates section with those 2 videos

#### Scenario: Run fails after a wait ends
- **WHEN** a run that would list an expired podcast episode under Creator updates fails before the digest is saved
- **THEN** the episode stays pending and the next saved digest lists it once under Creator updates

#### Scenario: Blocked and missing captions shown differently
- **WHEN** one video's caption request is blocked by YouTube and another video has no captions
- **THEN** Creator updates shows "blocked by YouTube" for the first and "the video has no captions" for the second

### Requirement: Summarize long texts in full
The system SHALL summarize an item's entire text. The single-call budget is computed in characters from the selected model's context window:
- reserve the summary output budget and a fixed prompt allowance
- count the rest at one character per token

When the provider reports no context window, the budget MUST be 60,000 characters. An instance setting, when set, MUST override both. A text within the budget SHALL be summarized in one model call. A longer text MUST be split into consecutive parts, each within the budget. Each part is summarized, then the part summaries are combined into one item summary. The system MUST NOT drop any part of the text.

#### Scenario: Large context window
- **WHEN** the provider reports a 1,000,000-token context window and an item's text is 169,961 characters
- **THEN** the item is summarized in one model call that receives the whole text

#### Scenario: Unknown context window
- **WHEN** the provider reports no context window and an item's text is 169,961 characters made of 1,000-character paragraphs
- **THEN** the text is split into 3 parts of at most 60,000 characters, each part is summarized, and one combining call produces the item summary

#### Scenario: Instance override
- **WHEN** the single-call budget setting is 20,000 characters
- **THEN** a 50,000-character text is summarized in 3 parts and combined, whatever the model's context window

### Requirement: Report model token usage
For each run, the system SHALL record the input and output tokens that the provider reports for the run's model calls. The run view and the saved digest MUST show the totals. A run that makes no model calls shows totals of 0. When the provider reports no usage for calls that were made, the totals are shown as not reported. Prices are not shown.

#### Scenario: Usage reported
- **WHEN** a run makes model calls whose responses report usage
- **THEN** the run view and the saved digest show the total input and output tokens of that run

#### Scenario: No model calls
- **WHEN** a run ends with no new content, or saves a digest that has only Creator updates
- **THEN** the run view and the digest show 0 input and 0 output tokens, not "not reported"

### Requirement: Use related context in summaries
When an item has gathered context, the summary call SHALL receive it after the item's text, labeled by kind (linked page or author reply), with each part's title and site. The model MUST use context only where it relates to the item, and MUST NOT summarize a linked page or a reply on its own. The model SHALL return the references of the context it used. References that do not match the item's context MUST be discarded. The text budget for splitting long items SHALL include the context. The context MUST be treated as data, not instructions. An item that already had a summary when its context was gathered SHALL be summarized again with the context.

#### Scenario: Unrelated linked page
- **WHEN** an item's context holds its release notes and an unrelated page linked from the post's footer
- **THEN** the summary draws on the release notes, and only the release notes are recorded as used

#### Scenario: Link-only post explained by its linked page
- **WHEN** an item's own text is only a release title, and its context holds the release notes
- **THEN** the summary describes the release from the notes, and does not say that the item has no substance

#### Scenario: Context gathered after a summary
- **WHEN** an item was summarized in a run that then failed, and the next run gathers its context
- **THEN** the item is summarized again with that context

#### Scenario: Model returns an unknown context reference
- **WHEN** the summary output names a context reference that the item does not have
- **THEN** the reference is dropped, and the summary is kept

### Requirement: Choose important images in summaries
When an item has image candidates, the summary call SHALL receive them as short descriptions: each one's alt text, caption, position, and origin. The model SHALL choose at most 3 images that show something the summary relies on, such as a chart, a screenshot, a diagram, or the photo the story is about, ordered by importance, each with a short alt text. It MUST choose none when no image matters, and MUST NOT choose logos, avatars, or decorative images. Choices that do not match a candidate MUST be discarded. The choice SHALL be stored with the summary and reused with it.

#### Scenario: Release post with a screenshot
- **WHEN** an item's summary describes a new tool's interface, and its first image is a screenshot of that interface
- **THEN** the screenshot is chosen, with a short alt text

#### Scenario: No important image
- **WHEN** an item's only candidate is a decorative header image
- **THEN** no image is chosen

#### Scenario: Unknown image reference
- **WHEN** the summary output names an image reference the item does not have
- **THEN** the reference is dropped and the summary is kept

### Requirement: Summarize pages saved from the browser
Pages saved from the browser that are waiting SHALL be included in the next digest run, and summarized like website items, with their related context and images. Each one MUST be shown under the saved page's site name, for example "X · Simon Willison", and MUST link to the address the user saved.

#### Scenario: Saved X post in a digest
- **WHEN** a run includes an X post saved from the browser
- **THEN** the digest shows its summary under "X · <author>", linking to the post, and its "Also read" lists any article it linked

### Requirement: Summarize posts from followed X accounts
Posts from followed X accounts that a run includes SHALL be summarized like website items, with their related context and images. Each one MUST be shown under "X · <display name>", MUST link to the post on x.com, and MUST list the linked pages it used under "Also read".

#### Scenario: Followed X post in a digest
- **WHEN** a run includes a post from the followed account "Simon Willison" that links to an article
- **THEN** the digest shows its summary under "X · Simon Willison", linking to the post, and "Also read" lists the article if it was used

### Requirement: Fit topic grouping in the model's context window
When the model's context window is known, the system SHALL size topic grouping calls from it, counting one character per token:
- each grouping call's output budget is the usual grouping budget, but at most half the context window;
- the items are split into batches whose text fits in the rest of the window after a fixed prompt allowance, but is never less than 2,000 characters, so a window under about 8,000 tokens may still be exceeded. Each batch is grouped, and then the batch topics are combined in one more call.

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
