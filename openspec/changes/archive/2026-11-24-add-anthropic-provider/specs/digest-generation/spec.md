# Spec Delta

## ADDED Requirements

### Requirement: Handle model refusals
When the Anthropic provider reports that the model declined a request for safety reasons, the system MUST NOT retry that request.
- A declined summary call makes that item's summary unavailable, and the run still saves the digest.
- A declined grouping call is handled like grouping answers that stay unusable after retries.

For the Anthropic models `claude-fable-5-2`, `claude-fable-5-1`, `claude-opus-5-5`, `claude-opus-5`, and `claude-sonnet-5-5`, every model call MUST ask Anthropic to run a declined request again on a fallback model of Anthropic's choice, within the same call. Only a request that the fallback model also declines counts as declined. Calls to other models MUST NOT ask for a fallback.

#### Scenario: Summary declined
- **WHEN** Anthropic reports that the model declined one item's summary call
- **THEN** the call is made once, that item appears with a note that its summary is unavailable, and the run saves the digest

#### Scenario: Fallback asked for a supported model
- **WHEN** the configured Anthropic model is `claude-opus-5-5`
- **THEN** every summary and grouping call asks Anthropic for a fallback model

#### Scenario: No fallback for other models
- **WHEN** the configured Anthropic model is `claude-haiku-5-5`
- **THEN** no call asks Anthropic for a fallback model

## MODIFIED Requirements

### Requirement: Work with reasoning models by default
The system SHALL request output budgets large enough that a provider's default reasoning mode does not leave summary or grouping responses empty. For the Anthropic provider, every model call MUST allow at least 16,000 output tokens, because thinking cannot be turned off on some Anthropic models and counts toward that limit.

#### Scenario: Provider reasons before answering
- **WHEN** the configured model reasons before producing output, as DeepSeek does by default
- **THEN** item summaries and topic grouping still return content within the requested budget

#### Scenario: Anthropic model that always thinks
- **WHEN** the Anthropic provider is configured, and an item's summary call asks for 4,096 output tokens
- **THEN** the request to Anthropic allows 16,000 output tokens

### Requirement: Retry transient model errors
The system SHALL retry model calls that return empty content, rate-limit errors, or temporary server errors, with backoff and a bounded number of attempts. Temporary server errors are HTTP 500, 502, 503, and 504. An answer that is not valid JSON, that is JSON but not an object, or that is not a chat completion with text content, such as an HTML or plain-text page sent with status 200, MUST be retried like empty content. Such an answer MUST NOT fail the run by itself. Authentication and insufficient-balance errors MUST fail the run immediately with a message telling the user to fix the configuration.

For the Anthropic provider:
- HTTP 529 (overloaded), and an error inside the answer stream that reports an overloaded or internal API error, are also temporary server errors;
- an answer with status 200 that is not a message stream, or whose text is not a JSON object, MUST be retried like empty content;
- a JSON object inside a single fenced code block counts as a JSON object;
- a refusal is not retried (see "Handle model refusals").

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

#### Scenario: Anthropic is overloaded
- **WHEN** an Anthropic summary call answers HTTP 529 once and valid content on retry
- **THEN** the item's summary is saved from the valid content

#### Scenario: Fenced JSON from Anthropic
- **WHEN** an Anthropic summary call answers with a JSON object inside a fenced code block marked `json`
- **THEN** the item's summary is saved from that object, without a retry
