# Spec Delta

## Purpose

Defines how CatchUp obtains transcripts for podcast episodes and YouTube videos so that audio and video are summarized only from what is said, and records why an item has no transcript when none can be obtained.

## ADDED Requirements

### Requirement: Recognize podcast and YouTube sources
The system SHALL classify each saved source as a website feed, a podcast, or a YouTube channel:
- a YouTube channel when its feed is a YouTube channel feed on `youtube.com`, `www.youtube.com`, or `m.youtube.com`
- a podcast when more than half of its entries carry audio enclosures
- otherwise a website feed

The classification MUST be refreshed on every successful check, so sources saved before this capability existed are classified on their next check. Their pending items are then handled as podcast or YouTube items. A source classified as a podcast or YouTube channel MUST NOT be reclassified as a website feed by a later check.

#### Scenario: Podcast feed
- **WHEN** the user confirms a feed whose entries carry audio enclosures
- **THEN** the source is saved as a podcast

Within a podcast source, only entries that carry an audio enclosure are episodes. Other entries are handled like website feed entries.

#### Scenario: Blog with one audio post
- **WHEN** a website feed lists 15 entries and only one carries an audio enclosure
- **THEN** the source stays a website feed and its entries are summarized from their article text

#### Scenario: Newsletter feed with iTunes metadata
- **WHEN** a newsletter feed declares iTunes channel elements (such as `itunes:author` and `itunes:owner`) but none of its 20 entries carries an audio enclosure
- **THEN** the source stays a website feed

#### Scenario: Text post in a podcast feed
- **WHEN** a podcast source's feed lists a new entry without an audio enclosure
- **THEN** that entry is summarized from its text like a website feed entry, not held for a transcript

#### Scenario: YouTube channel feed
- **WHEN** the user confirms a YouTube channel feed
- **THEN** the source is saved as a YouTube channel

#### Scenario: YouTube channel saved before this change
- **WHEN** a YouTube channel saved earlier as a website feed is checked successfully
- **THEN** it becomes a YouTube channel, and its pending videos follow the caption rules instead of being summarized from descriptions

### Requirement: Use published podcast transcripts
For a podcast episode, the system SHALL use a transcript the feed publishes for that episode, and SHALL consider every transcript the episode lists:
- It prefers, in order, plain text, WebVTT, SRT, JSON, and HTML.
- A transcript in the feed's language wins over one in another language.
- It recognizes transcript tags by their standard podcast prefix even when the feed declares a nonstandard namespace address.
- It accepts the common nonstandard SRT media type.
- Feeds with minor XML errors that the feed parser tolerates MUST still yield their transcripts.
- Entity definitions declared inside a feed MUST NOT affect transcript addresses. A feed whose internal DTD declares entities is read only through the feed parser's single transcript tag.
- A transcript belongs to the episode whose item lists it. It MUST NOT be attributed to another episode through a link that several items share.
- A transcript tag without a `language` is in the feed's language, and language tags match on their primary subtag (`en-us` matches `en`).

The transcript MUST be fetched through the safe fetcher with the transcript size limit and per-host spacing, and converted to plain text: timing lines removed, speaker names kept as "Name:" labels. An unexpected error while fetching or converting one episode's transcript MUST NOT fail the run. The episode is treated as having no transcript on that run.

#### Scenario: Episode with several transcript formats
- **WHEN** an episode lists HTML, JSON, SRT, and WebVTT transcripts
- **THEN** the system fetches the WebVTT transcript and stores its spoken text with speaker names and without timing lines

#### Scenario: Transcript served with a generic media type
- **WHEN** an SRT transcript is served as `application/octet-stream`
- **THEN** the system still recognizes and converts it

#### Scenario: Shared episode links
- **WHEN** two episodes link to the same show page and only the first lists a transcript
- **THEN** the second episode gets no transcript from the first and waits for its own

#### Scenario: Feed with a public DOCTYPE
- **WHEN** a podcast feed starts with a public DOCTYPE declaration and an episode lists four transcript formats
- **THEN** all four are considered and the preferred one is used

#### Scenario: Feed with an undefined HTML entity
- **WHEN** a podcast feed item contains `&nbsp;` in its title and lists a WebVTT transcript
- **THEN** the transcript is still found and used

### Requirement: Wait for late podcast transcripts
A podcast episode without a transcript SHALL wait for one for a configurable number of days (default 7), counted from when the episode was first recorded. On every run during the wait, the system MUST check the source's freshly fetched feed for a transcript of that episode. If a transcript appears, the episode is summarized from it. When the wait ends without a transcript, the episode MUST be included once under Creator updates with the reason "no transcript within N days" (N is the configured wait). This applies even when the episode is no longer listed in the feed or the source's checks fail.

#### Scenario: Transcript appears on day 2
- **WHEN** an episode had no transcript on its first run and the feed lists a transcript for it on a run two days later
- **THEN** that run fetches the transcript and the episode is summarized from it

#### Scenario: Wait ends
- **WHEN** an episode still has no transcript on a run 7 days after it was first recorded, with the default wait
- **THEN** the episode is included under Creator updates and is not checked again

#### Scenario: Feed keeps failing
- **WHEN** a podcast's checks fail on every run for 8 days after an episode was first recorded without a transcript
- **THEN** the next saved digest lists the episode once under Creator updates

### Requirement: Opt in to fetching YouTube captions locally
The system SHALL fetch YouTube captions only when the user has turned on caption fetching in Settings. The setting MUST be off by default. Its description MUST state that fetching captions this way conflicts with YouTube's Terms of Service. While the setting is off, YouTube videos MUST NOT be summarized from their descriptions or watch pages. They are included under Creator updates with the reason "caption fetching is off".

#### Scenario: Default settings
- **WHEN** a new video from a saved YouTube channel is recorded and the user has not changed the caption setting
- **THEN** no caption request is made and the video appears under Creator updates with the reason "caption fetching is off"

#### Scenario: Setting on
- **WHEN** caption fetching is on and a new video has captions
- **THEN** the video is summarized from its captions

### Requirement: Wait for late YouTube captions
When caption fetching is on and a video has no captions yet, the system SHALL keep the video pending for a configurable number of hours (default 24), counted from when the video was first recorded. The same applies when the video cannot be played yet, such as an upcoming premiere or live stream. On every run during the wait, the system MUST request the video's captions again, within the per-run limit. When captions appear, the video is summarized from them. When the wait ends:
- a video that still has no captions MUST be included once under Creator updates with the reason "the video has no captions"
- a video that still cannot be played MUST be included once with the reason "captions could not be fetched"

Blocked requests and other failures do not wait.

#### Scenario: Captions generated after upload
- **WHEN** a video has no captions on the run right after it was recorded, and has auto-generated captions on a run 6 hours later
- **THEN** the second run fetches the captions and the video is summarized from them

#### Scenario: Caption wait ends
- **WHEN** a video still has no captions on a run 25 hours after it was first recorded, with the default wait
- **THEN** the video is included once under Creator updates with the reason "the video has no captions"

### Requirement: Use captions in the video's original language
When fetching YouTube captions, the system SHALL use captions in the video's original language. Machine-translated tracks MUST NOT be used, and caption tracks that YouTube generates for dubbed audio tracks are not the original. The original-language track is determined in this order:
1. YouTube's player data reports a default audio track. The system uses that track's default caption track. If none is reported, it uses the language of the default audio track.
2. Otherwise, the system infers the language:
   - the language of a manually created track that also has an auto-generated track
   - else the only auto-generated track
   - else the only manually created track
3. Otherwise, the original language cannot be determined. The system MUST NOT pick a track, and the video is recorded as "captions could not be fetched".

Within the original language, a manually created track MUST be preferred over an auto-generated one. The summary is still written in the digest language.

#### Scenario: Manual and auto-generated tracks
- **WHEN** a video has a manually created English track and an auto-generated English track, and English is its original language
- **THEN** the manually created track is used

#### Scenario: Auto-dubbed video
- **WHEN** a video whose default audio track is English has 21 auto-generated tracks in different languages, listed with Arabic first, and one manually created English track
- **THEN** the manually created English track is used, not the Arabic one

#### Scenario: Original language cannot be determined
- **WHEN** YouTube reports no default audio track and a video has auto-generated tracks in several languages and no manually created track
- **THEN** no track is used and the video is recorded as "captions could not be fetched"

#### Scenario: Digest language differs
- **WHEN** a video's original language is English and the digest language is Simplified Chinese
- **THEN** the English captions are used, without a translated track, and the summary is written in Simplified Chinese

### Requirement: Limit and space caption requests
YouTube caption requests SHALL be made for one video at a time, after all sources of the run have been checked, oldest recorded video first across all channels. Videos still in their caption wait are included. They MUST be spaced per host like other source requests. Captions are requested by video identifier, so a deferred video is still handled after it drops out of its channel's feed. The system MUST fetch captions for at most a configurable number of videos (default 20) in one run. Videos beyond the limit MUST stay pending, and the run MUST report how many were deferred to a later run. After YouTube blocks a caption request, the run MUST make no further caption requests. Videos not yet tried stay pending for a later run. An unexpected error for one video MUST NOT fail the run.

#### Scenario: More videos than the limit
- **WHEN** caption fetching is on and 25 new videos need captions in one run, with the default limit
- **THEN** captions are fetched for the 20 first recorded (by recording time, then recording order), and the run reports that 5 videos were deferred to the next run

#### Scenario: Blocked request
- **WHEN** YouTube blocks the caption request for the third of 10 videos in a run
- **THEN** no caption requests are made for the remaining 7 videos in that run, and they stay pending

#### Scenario: Deferred video no longer in the feed
- **WHEN** a video deferred in one run is no longer listed in its channel's feed on the next run
- **THEN** its captions are still requested on that next run, within the limit

### Requirement: Record why a transcript is unavailable
For every podcast or YouTube item that ends without a transcript, the system SHALL record one reason:
- caption fetching is off
- the video has no captions
- blocked by YouTube
- captions could not be fetched
- no transcript within N days

"Blocked by YouTube" MUST be distinguished from "the video has no captions". Any other caption failure, including unexpected errors, is "captions could not be fetched".

#### Scenario: Captions disabled by the uploader
- **WHEN** caption fetching is on and a video's captions are disabled, and they are still disabled when its caption wait ends
- **THEN** the recorded reason is "the video has no captions"

#### Scenario: Unavailable video
- **WHEN** caption fetching is on and a video is unavailable or age-restricted
- **THEN** the recorded reason is "captions could not be fetched"

#### Scenario: Unexpected response format
- **WHEN** caption fetching is on and the caption library fails with an unexpected error for one video
- **THEN** that video's recorded reason is "captions could not be fetched" and the run continues

### Requirement: Skip YouTube Shorts by default
The system SHALL skip YouTube Shorts unless the user turns off "skip Shorts" in Settings. The setting MUST be on by default. A skipped Short MUST be recorded as already seen. It never appears in a digest, neither summarized nor under Creator updates, and no caption request is made for it. This includes Shorts that were pending before this capability existed.

#### Scenario: New Short with default settings
- **WHEN** a YouTube channel's feed lists a new Short
- **THEN** no caption request is made and the Short never appears in a digest
