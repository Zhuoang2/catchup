# Spec Delta

## MODIFIED Requirements

### Requirement: Show chosen images from their source sites
In the digest reading layout, an item's chosen images SHALL appear under its summary, in the summary's column, in the order chosen. Each image MUST:
- load from its source site;
- load lazily, and send no referrer;
- carry its alt text;
- be at most 320 px tall and no wider than the column.

An image that fails to load MUST be hidden without leaving an empty frame. Settings SHALL offer "Show images from source sites" in the Digest group, on by default. Its note MUST say that opening a digest then contacts those sites, and MUST be associated with the toggle for assistive technology. When it is off, the digest MUST NOT request any image.

An image whose address names this computer or a device on a local network, by the rules of "Keep image candidates for items" in `content-collection`, MUST NOT be shown or requested. This includes images recorded in digests saved before that rule.

#### Scenario: Item with two chosen images
- **WHEN** an item chose a chart and a screenshot
- **THEN** both appear under its summary in that order, each with its alt text

#### Scenario: Image no longer available
- **WHEN** a chosen image's URL answers 404
- **THEN** that image is hidden, and the rest of the item is unchanged

#### Scenario: Images turned off
- **WHEN** the user turns off "Show images from source sites" and opens a digest whose items chose images
- **THEN** no image is shown or requested

#### Scenario: Saved digest with a local image
- **WHEN** a digest saved earlier recorded `http://192.168.1.1/cam.jpg` and a public image for one item, and the user opens it
- **THEN** only the public image is shown, and `http://192.168.1.1/cam.jpg` is never requested

## ADDED Requirements

### Requirement: Show preview progress, and only the current address's preview
On the Sources page, while a preview loads, Preview SHALL stay focusable and be announced as unavailable, and activating it, including pressing Enter in the address field, MUST do nothing. The page MUST announce "Loading the preview…" through its status region. "Save and preview" in the X token form MUST behave the same way while it works.

Editing the address MUST end the wait: Preview becomes available again, the loading message is removed, and the pending answer is ignored. A preview or an error MUST be shown only when it answers the address the field shows, so that Confirm saves a preview of that address. When the X token is saved but the address changed before the preview started, the page MUST NOT preview the old address, and MUST announce "X token saved." unless a newer preview is loading; then its loading message stays.

#### Scenario: Preview loading
- **WHEN** a keyboard user presses Preview, and the answer takes several seconds
- **THEN** focus stays on Preview, which is announced as unavailable, "Loading the preview…" is announced, and pressing Preview again sends no second request

#### Scenario: Address changed while loading
- **WHEN** the user previews address A, changes the field to address B and previews it, and A answers after B
- **THEN** the page shows B's preview, and Confirm saves B's feed

#### Scenario: Error for an earlier address
- **WHEN** the user previews address A, then changes the field before A's preview fails
- **THEN** A's error is not shown, the loading message is gone, and Preview is available
