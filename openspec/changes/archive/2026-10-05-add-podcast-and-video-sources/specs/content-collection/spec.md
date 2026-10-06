# Spec Delta

## MODIFIED Requirements

### Requirement: Record entries the first time they are seen
The system SHALL identify each entry within a source by a stable key: the entry's feed identifier, else its link, else a hash of its title and date. An entry is new only the first time its key is seen for that source. An entry whose key is unknown but whose link matches an already recorded entry of the same source MUST be treated as already seen. Publish dates MUST NOT decide whether an entry is new. A link that more than one entry of the same feed document carries (for example, every episode linking to the show's home page) MUST NOT be used to identify, deduplicate, or match entries. An entry without a feed identifier whose link is shared in this way is identified by the hash of its title and date.

#### Scenario: Repeated entries
- **WHEN** a feed still lists entries that were recorded on an earlier run
- **THEN** those entries are not recorded again and do not appear in the next digest again

#### Scenario: Late entry with an old publish date
- **WHEN** an entry appears in a feed for the first time with a publish date older than the source's last successful check
- **THEN** the entry is recorded as new

#### Scenario: Site changes an entry identifier
- **WHEN** a feed lists an entry with a new identifier but the same link as a recorded entry
- **THEN** no duplicate entry is recorded

#### Scenario: Episodes share the show's link
- **WHEN** a podcast feed lists 3 episodes with different identifiers whose links are all the show's home page, and one of them was recorded earlier
- **THEN** the other 2 episodes are recorded as new

### Requirement: Keep article text for summarization
For each new entry of a website feed, the system SHALL keep the text the feed provides. When that text is very short, the system SHALL try to fetch the linked article through the safe fetcher and extract its main text, and fall back to the feed text if extraction fails. Podcast episodes (entries of a podcast source that carry an audio enclosure) and YouTube videos MUST NOT be summarized from their show notes, descriptions, or linked pages. Their text for summarization comes only from a transcript (see the `transcripts` capability).

#### Scenario: Feed provides only a short excerpt
- **WHEN** a new entry's feed text is shorter than the configured threshold and the article page is reachable
- **THEN** the stored text for summarization is the extracted article text

#### Scenario: Podcast episode with short show notes
- **WHEN** a new podcast episode has short show notes and no transcript
- **THEN** the system does not fetch the episode's web page, and the episode is not summarized from its show notes
