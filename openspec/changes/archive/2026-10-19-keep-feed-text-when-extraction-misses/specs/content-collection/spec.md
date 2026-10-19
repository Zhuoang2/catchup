## MODIFIED Requirements

### Requirement: Keep article text for summarization
For each new entry of a website feed, the system SHALL keep the text the feed provides. When that text is very short, the system SHALL try to fetch the linked article through the safe fetcher and extract its main text, and fall back to the feed text if extraction fails. The extracted text SHALL replace the feed text only when it covers the feed text, that is, when most of the feed text's words appear in it. Otherwise the stored text MUST begin with the feed text, followed by the extracted text, so that the feed's own words are never lost. Podcast episodes (entries of a podcast source that carry an audio enclosure) and YouTube videos MUST NOT be summarized from their show notes, descriptions, or linked pages. Their text for summarization comes only from a transcript (see the `transcripts` capability).

#### Scenario: Feed provides only a short excerpt
- **WHEN** a new entry's feed text is shorter than the configured threshold, the article page is reachable, and the extracted text contains the excerpt
- **THEN** the stored text for summarization is the extracted article text

#### Scenario: Extraction misses the post
- **WHEN** a new entry's feed text is shorter than the configured threshold, and the text extracted from its page does not contain most of the feed text's words, such as a sidebar listing other posts
- **THEN** the stored text begins with the feed text, followed by the extracted text

#### Scenario: Entry without feed text
- **WHEN** a new entry has no feed text and its article page is reachable
- **THEN** the stored text for summarization is the extracted article text

#### Scenario: Podcast episode with short show notes
- **WHEN** a new podcast episode has short show notes and no transcript
- **THEN** the system does not fetch the episode's web page, and the episode is not summarized from its show notes
