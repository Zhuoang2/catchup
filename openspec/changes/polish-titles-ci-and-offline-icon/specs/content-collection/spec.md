## MODIFIED Requirements

### Requirement: Readable titles for untitled entries
When a feed entry has no title, the system SHALL use the beginning of the entry's text (at most 80 characters) as its title. When the text is cut, the title MUST end with exactly one ellipsis: dots or ellipsis characters at the end of the cut text are removed before the ellipsis is added. It SHALL show "Untitled" only when the entry has neither title nor text.

#### Scenario: Social post without a title
- **WHEN** a feed entry has no title and its text begins "Happy opening day, hockey fans! Follow all 1,344 games…"
- **THEN** the entry's title shown in previews and digests starts with "Happy opening day, hockey fans!"

#### Scenario: Cut text that already ends in dots
- **WHEN** a feed entry has no title, and its text is longer than 80 characters with "..." at the point where it is cut
- **THEN** the derived title ends with a single "…", not "...…"
