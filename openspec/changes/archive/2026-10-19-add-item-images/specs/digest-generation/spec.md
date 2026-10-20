## ADDED Requirements

### Requirement: Choose important images in summaries
When an item has image candidates, the summary call SHALL receive them as short descriptions: each one's alt text, caption, position, and origin. The model SHALL choose at most 3 images that show something the summary relies on, such as a chart, a screenshot, a diagram, or the photo the story is about, ordered by importance, each with a short alt text. It MUST choose none when no image matters, and MUST NOT choose logos, avatars, or decorative images. Choices that do not match a candidate MUST be discarded. The choice SHALL be stored with the summary and reused with it.

#### Scenario: Release post with a screenshot
- **WHEN** an item's summary describes a new tool's interface, and its first image is a screenshot of that interface
- **THEN** the screenshot is chosen, with a short alt text

#### Scenario: No important image
- **WHEN** an item's only candidate is a decorative header image
- **THEN** no image is chosen

#### Scenario: Unknown image reference
- **WHEN** the summary output names an image reference the item does not have
- **THEN** the reference is dropped and the summary is kept
