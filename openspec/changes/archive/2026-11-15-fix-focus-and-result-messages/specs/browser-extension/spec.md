## ADDED Requirements

### Requirement: Keep focus and announcements in the popup
The extension's popup SHALL keep keyboard focus and screen-reader announcements when its content changes.
- **Status line.** After the popup connects to CatchUp, it MUST keep one status line until it closes or shows the disconnected view. Every result message MUST be written to that status line, which stays in the popup when the rest of the content is replaced.
- **Focus after a change.** When new content replaces the popup's content, focus MUST move to this target:
  - after "Follow this site" or "Follow this account", and after the X token is saved: the preview's heading;
  - when the popup asks for the X token: the token field;
  - after the preview's Confirm or Cancel: "Follow this site" or "Follow this account";
  - after a page is saved or removed: "Add this page to my next digest";
  - when an action leads to the disconnected view: "Open options".
- **Busy buttons.** While "Add this page to my next digest", Remove, or the X token's Save is working, the button MUST stay focusable and be announced as unavailable, and activating it MUST do nothing.

#### Scenario: Save a page with the keyboard
- **WHEN** a keyboard user presses "Add this page to my next digest" and the page is saved
- **THEN** focus is on "Add this page to my next digest", and the status line announces that the page will be in the next digest

#### Scenario: Preview and cancel
- **WHEN** a keyboard user chooses "Follow this site", then Cancel
- **THEN** focus moves to the preview's heading, then back to "Follow this site"

#### Scenario: One status line
- **WHEN** the user saves a page, removes it, and then follows the site
- **THEN** each result is announced through the same status line, which stayed in the popup throughout
