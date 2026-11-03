## MODIFIED Requirements

### Requirement: Follow the current site from the browser
The extension's popup SHALL offer "Follow this site" for the active tab. It MUST preview the tab's address with the same preview the Sources page uses, show the same details and error messages, and save the source only after the user confirms. On an X page whose address identifies an X account (a profile or a post), it SHALL offer "Follow this account" in place of "Follow this site", with the same preview, error messages, and confirmation. When CatchUp reports that no X token is saved, the popup SHALL ask for the token in a password field, send it to CatchUp, and preview again. When CatchUp already has a token that X rejected, the popup MUST say to replace it in CatchUp's Settings. The popup MUST NOT contact X itself. On other X pages it SHALL offer only "Add this page to my next digest".

#### Scenario: Follow a blog
- **WHEN** the user is reading a blog post and chooses "Follow this site", then confirms
- **THEN** the blog's feed is saved as a source, as if the post's address had been pasted into the Sources page

#### Scenario: Already followed
- **WHEN** the user chooses "Follow this site" on a site that is already a source
- **THEN** the popup says the site is already followed, and saves nothing

#### Scenario: X profile
- **WHEN** the user opens the popup on `https://x.com/simonw`, while an X token is saved
- **THEN** the popup offers "Follow this account", and confirming it follows the account

#### Scenario: X profile without a token
- **WHEN** the user chooses "Follow this account" while no X token is saved
- **THEN** the popup asks for the X token, saves it in CatchUp, and shows the account's preview

#### Scenario: X home page
- **WHEN** the user opens the popup on `https://x.com/home`
- **THEN** the popup offers only "Add this page to my next digest"
