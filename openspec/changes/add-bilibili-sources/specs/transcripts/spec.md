# Spec Delta

## MODIFIED Requirements

### Requirement: Recognize podcast and YouTube sources
The system SHALL classify each saved source as a website feed, a podcast, or a YouTube channel:
- a YouTube channel when its feed is a YouTube channel feed on `youtube.com`, `www.youtube.com`, or `m.youtube.com`
- a podcast when more than half of its entries carry audio enclosures
- otherwise a website feed

The built-in source for pages saved from the browser is a fourth kind, "Saved from browser". A followed X account is a fifth kind, "X account". A followed Bilibili uploader is a sixth kind, "Bilibili uploader". None of these three is ever classified or reclassified: the first two have no feed, and an uploader is recognized from its address.

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

#### Scenario: Saved-from-browser source
- **WHEN** the first page is saved from the browser
- **THEN** its source has the kind "Saved from browser", and no check reclassifies it

#### Scenario: X account source
- **WHEN** the user follows an X account
- **THEN** its source has the kind "X account", and no check reclassifies it

#### Scenario: Bilibili uploader source
- **WHEN** the user follows a Bilibili uploader
- **THEN** its source has the kind "Bilibili uploader", and no check reclassifies it

### Requirement: Record why a transcript is unavailable
For every podcast, YouTube, or Bilibili item that ends without a transcript, the system SHALL record one reason:
- caption fetching is off
- the video has no captions
- blocked by YouTube
- captions could not be fetched
- no transcript within N days
- no subtitles from RSSHub (Bilibili videos only)

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

#### Scenario: Bilibili video without subtitles
- **WHEN** a Bilibili video still has no subtitles from RSSHub when its subtitle wait ends
- **THEN** the recorded reason is "no subtitles from RSSHub"
