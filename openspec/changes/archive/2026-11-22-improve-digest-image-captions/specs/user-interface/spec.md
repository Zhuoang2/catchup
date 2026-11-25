## MODIFIED Requirements

### Requirement: Show chosen images from their source sites
In the digest reading layout, an item's chosen images SHALL appear under its summary, in the summary's column, in the order chosen. Each image MUST:
- load from its source site;
- load lazily, and send no referrer;
- show its text as a caption directly under it, in the digest's language, no wider than the column;
- be at most 320 px tall and no wider than the column.

Assistive technology MUST get each image's text once, as the caption of its figure: the image itself MUST NOT repeat the text. An image whose text is empty MUST NOT be shown. Digests saved before captions were shown SHALL show their stored text as the caption.

An image that fails to load MUST be hidden together with its caption, without leaving an empty frame. Settings SHALL offer "Show images from source sites" in the Digest group, on by default. Its note MUST say that opening a digest then contacts those sites, and MUST be associated with the toggle for assistive technology. When it is off, the digest MUST NOT request any image, and MUST NOT show captions.

An image whose address names this computer or a device on a local network, by the rules of "Keep image candidates for items" in `content-collection`, MUST NOT be shown or requested. This includes images recorded in digests saved before that rule. An image whose address is a rendered formula, by the same requirement's rules, MUST NOT be shown or requested either, including in digests saved before that rule.

#### Scenario: Item with two chosen images
- **WHEN** an item chose a chart and a screenshot
- **THEN** both appear under its summary in that order, each with its caption under it

#### Scenario: Caption read once
- **WHEN** an item chose a chart whose text is "Sales doubled after the redesign: the chart the post's argument rests on"
- **THEN** that text is shown under the chart, assistive technology reads it once as the figure's caption, and the image itself has no text of its own

#### Scenario: Digest saved before captions
- **WHEN** the user opens a digest saved before this change, whose item recorded an image with the text "SVG of a pelican riding a bicycle, drawn by a model at its highest reasoning level"
- **THEN** that text is shown under the image as its caption

#### Scenario: Image without text
- **WHEN** a saved digest's item recorded one image with an empty text and one with a text
- **THEN** only the image with a text is shown

#### Scenario: Image no longer available
- **WHEN** a chosen image's URL answers 404
- **THEN** that image and its caption are hidden, and the rest of the item is unchanged

#### Scenario: Images turned off
- **WHEN** the user turns off "Show images from source sites" and opens a digest whose items chose images
- **THEN** no image or caption is shown, and no image is requested

#### Scenario: Saved digest with a local image
- **WHEN** a digest saved earlier recorded `http://192.168.1.1/cam.jpg` and a public image for one item, and the user opens it
- **THEN** only the public image is shown, and `http://192.168.1.1/cam.jpg` is never requested

#### Scenario: Saved digest with a formula image
- **WHEN** a digest saved earlier recorded `https://s0.wp.com/latex.php?latex=%7BT%7D` and a chart for one item, and the user opens it
- **THEN** only the chart is shown, and the formula image is never requested
