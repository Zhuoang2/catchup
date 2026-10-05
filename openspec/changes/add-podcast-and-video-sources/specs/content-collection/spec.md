# Spec Delta

## MODIFIED Requirements

### Requirement: Keep article text for summarization
For each new entry of a website feed, the system SHALL keep the text the feed provides. When that text is very short, the system SHALL try to fetch the linked article through the safe fetcher and extract its main text, and fall back to the feed text if extraction fails. Podcast episodes (entries of a podcast source that carry an audio enclosure) and YouTube videos MUST NOT be summarized from their show notes, descriptions, or linked pages. Their text for summarization comes only from a transcript (see the `transcripts` capability).

#### Scenario: Feed provides only a short excerpt
- **WHEN** a new entry's feed text is shorter than the configured threshold and the article page is reachable
- **THEN** the stored text for summarization is the extracted article text

#### Scenario: Podcast episode with short show notes
- **WHEN** a new podcast episode has short show notes and no transcript
- **THEN** the system does not fetch the episode's web page, and the episode is not summarized from its show notes
