# Spec Delta

## MODIFIED Requirements

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
  - no subtitles from RSSHub, for a Bilibili video

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

#### Scenario: Bilibili video past the subtitle wait
- **WHEN** a Bilibili video has no subtitles from RSSHub when its subtitle wait ends
- **THEN** the next saved digest lists it under its uploader in Creator updates with the reason "no subtitles from RSSHub", and no model call is made for it
