# content-collection Specification

## Purpose
Defines how CatchUp checks sources, decides what is new since each source's last successful check, and reports each check's outcome, so digests never repeat items or silently miss them.

## Requirements

### Requirement: Check every source on each run
Each digest run SHALL check every saved source once, and record for each source one outcome: `new_items` (at least one new entry recorded), `no_new_items` (fetched and parsed successfully, nothing new), or `failed` (with an error description). A failed check MUST never be reported as `no_new_items`.

#### Scenario: Source unreachable
- **WHEN** a source cannot be fetched or its feed cannot be parsed during a run
- **THEN** that source's outcome is `failed` with an error description, and other sources are still checked

#### Scenario: Nothing new
- **WHEN** a source's feed contains only entries already recorded
- **THEN** that source's outcome is `no_new_items`

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

### Requirement: Recover content after failed checks
Because newness is decided by first sight rather than by time, entries published while a source's checks were failing SHALL be collected on its next successful check, as long as they are still listed in the feed.

#### Scenario: Failure then success
- **WHEN** a source fails on one run and on the next run its feed lists two entries never seen before
- **THEN** both entries are recorded as new on that next run

### Requirement: Flag possible gaps
When a successful check of a source that already has recorded entries finds none of its previously recorded keys or links in the feed, the system SHALL flag that check as a possible gap. A possible gap means older entries may have dropped off the feed between checks.

#### Scenario: All entries unseen
- **WHEN** a source with recorded entries is checked and every entry in its feed is new
- **THEN** the check outcome carries a possible-gap flag that the user can see

### Requirement: Readable titles for untitled entries
When a feed entry has no title, the system SHALL use the beginning of the entry's text (at most 80 characters) as its title. It SHALL show "Untitled" only when the entry has neither title nor text.

#### Scenario: Social post without a title
- **WHEN** a feed entry has no title and its text begins "Happy opening day, hockey fans! Follow all 1,344 games…"
- **THEN** the entry's title shown in previews and digests starts with "Happy opening day, hockey fans!"

### Requirement: Keep article text for summarization
For each new entry of a website feed, the system SHALL keep the text the feed provides. When that text is very short, the system SHALL try to fetch the linked article through the safe fetcher and extract its main text, and fall back to the feed text if extraction fails. Podcast episodes (entries of a podcast source that carry an audio enclosure) and YouTube videos MUST NOT be summarized from their show notes, descriptions, or linked pages. Their text for summarization comes only from a transcript (see the `transcripts` capability).

#### Scenario: Feed provides only a short excerpt
- **WHEN** a new entry's feed text is shorter than the configured threshold and the article page is reachable
- **THEN** the stored text for summarization is the extracted article text

#### Scenario: Podcast episode with short show notes
- **WHEN** a new podcast episode has short show notes and no transcript
- **THEN** the system does not fetch the episode's web page, and the episode is not summarized from its show notes

### Requirement: Identify rate-limited checks
A check that fails because the source rate limited CatchUp SHALL be recorded as `failed`, with the HTTP status and the suggested wait when known. It MUST be shown to the user as "rate limited", distinct from other failures, in the source list and in run progress.

#### Scenario: Rate limited during a run
- **WHEN** a source answers 429 during a digest run and the wait is too long to retry
- **THEN** its check is `failed` with HTTP status 429, and the run progress and source list show it as rate limited

### Requirement: Space requests to the same host during a run
During a digest run, the system SHALL keep at least 1 second between consecutive requests to the same host. This covers feed checks and article fetches.

#### Scenario: Two sources on one host
- **WHEN** a run checks two sources whose feeds are on the same host
- **THEN** the second request to that host starts at least 1 second after the first

#### Scenario: Different hosts
- **WHEN** a run checks two sources on different hosts
- **THEN** no spacing delay is added between them
