## ADDED Requirements

### Requirement: Show chosen images from their source sites
In the digest reading layout, an item's chosen images SHALL appear under its summary, in the summary's column, in the order chosen. Each image MUST:
- load from its source site;
- load lazily, and send no referrer;
- carry its alt text;
- be at most 320 px tall and no wider than the column.

An image that fails to load MUST be hidden without leaving an empty frame. Settings SHALL offer "Show images from source sites" in the Digest group, on by default. Its note MUST say that opening a digest then contacts those sites, and MUST be associated with the toggle for assistive technology. When it is off, the digest MUST NOT request any image.

#### Scenario: Item with two chosen images
- **WHEN** an item chose a chart and a screenshot
- **THEN** both appear under its summary in that order, each with its alt text

#### Scenario: Image no longer available
- **WHEN** a chosen image's URL answers 404
- **THEN** that image is hidden, and the rest of the item is unchanged

#### Scenario: Images turned off
- **WHEN** the user turns off "Show images from source sites" and opens a digest whose items chose images
- **THEN** no image is shown or requested
