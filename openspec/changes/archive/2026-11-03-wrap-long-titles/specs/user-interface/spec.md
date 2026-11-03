## MODIFIED Requirements

### Requirement: One grid for masthead, navigation, and content
The system SHALL place the masthead, the navigation, and page content in one shared container whose left and right edges align on every screen. On wide windows the content uses a 12-column grid, and page content MUST NOT be centered independently of the masthead. Below 900 px of window width, content becomes a single column. Screens MUST NOT scroll horizontally at a width of 320 px. Text without break points, such as a long address in a title, MUST wrap inside its column instead of widening the screen.

#### Scenario: Wide window
- **WHEN** the user opens any screen in a 1440 px wide window
- **THEN** the left edge of the page headline aligns with the left edge of the masthead rule

#### Scenario: Narrow window
- **WHEN** the window is 420 px wide
- **THEN** content is a single column and the navigation fits on one row

#### Scenario: Long unbroken title at 320 px
- **WHEN** the window is 320 px wide, and a digest item, a Creator updates item, a run's source check, a source, or an entry in a source preview has a title with no break points, such as an X post that starts with a long address
- **THEN** the title wraps inside its column, and the screen does not scroll horizontally
