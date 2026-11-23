## MODIFIED Requirements

### Requirement: Choose important images in summaries
When an item has image candidates, the summary call SHALL receive them as short descriptions: each one's alt text, caption, position, and origin. Candidates that the rules of "Keep image candidates for items" in `content-collection` leave out MUST NOT be offered, including candidates stored before those rules. The model SHALL choose an image only when it shows something the summary relies on, such as a chart, a screenshot, a diagram, or the photo the story is about, and a reader who has not read the item can understand it from the image and its caption. It SHALL usually choose one image, and a second or third only when each shows something different that the summary relies on, ordered by importance, never more than 3. For each choice it SHALL write a caption of up to 120 characters, in the language of the summary, that says what the image shows and why it matters. The caption is stored as the image's text. It MUST choose none when no image matters, and MUST NOT choose logos, avatars, decorative images, or rendered formulas. Choices that do not match a candidate MUST be discarded. The choice SHALL be stored with the summary and reused with it.

#### Scenario: Release post with a screenshot
- **WHEN** an item's summary describes a new tool's interface, and its first image is a screenshot of that interface
- **THEN** the screenshot is chosen, with a caption that says what it shows

#### Scenario: Benchmark drawing
- **WHEN** an item compares models by the drawings they make of a pelican riding a bicycle, and its candidates are those drawings
- **THEN** at most one drawing is chosen unless the others show something different, and its caption says that it is a model's output for that drawing test

#### Scenario: No important image
- **WHEN** an item's only candidate is a decorative header image
- **THEN** no image is chosen

#### Scenario: Formula candidate stored before the rules
- **WHEN** a pending item collected before the formula rule has the candidates `https://s0.wp.com/latex.php?latex=%7BT%7D` and `https://cdn.example/chart.png`
- **THEN** the summary call is offered only the chart, as `I1`

#### Scenario: Unknown image reference
- **WHEN** the summary output names an image reference the item does not have
- **THEN** the reference is dropped and the summary is kept
