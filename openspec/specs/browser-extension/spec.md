# browser-extension Specification

## Purpose
Lets the user connect a Chrome or Edge extension to their local CatchUp, so that, only when they click, they can follow the site or X account they are viewing, or add the page they are reading to the next digest. An X post is added with its author's own visible replies.

## Requirements

### Requirement: Connect a browser to CatchUp
Settings SHALL offer "Connect a browser". It creates a connection token for a browser the user names, and shows the token once, with a note to paste it into the extension's options. Settings SHALL list the connected browsers, each with its name, when it was connected, and when it was last used. "Disconnect" MUST make that browser's token stop working at once. The system MUST NOT store a token in a form that reveals it, and MUST NOT show it again after it was first shown.

#### Scenario: Connect a browser
- **WHEN** the user chooses "Connect a browser" and names it "Chrome"
- **THEN** Settings shows a token once, with a note to paste it into the extension, and lists "Chrome" as connected

#### Scenario: Token shown only once
- **WHEN** the user reloads Settings after connecting a browser
- **THEN** the browser is still listed, and its token is not shown

#### Scenario: Disconnect a browser
- **WHEN** the user disconnects "Chrome"
- **THEN** the extension in that browser can no longer save sources or pages, and is told it is not connected

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

### Requirement: Add the current page to the next digest
The popup SHALL offer "Add this page to my next digest". The extension MUST read the page only when the user chooses this, and only as it is rendered in the active tab at that moment. It MUST read only what the page shows: text, images, and links inside an element that the page hides, for example with the `hidden` attribute or a style rule, MUST NOT be read. It reads:
- the page's address and title;
- its site name, author, and publication time, when the page states them, in its metadata or in a date element of the post;
- its main text, up to 16,000 characters, found with a reader-view method so that navigation, sidebars, sponsor blocks, and ads are left out. On a short page, the main text MUST come from the post itself, even when a longer block beside it is an `aside`, or is marked as a sponsor block, banner, or sidebar by its class or id. When the reader-view method finds no text, the extension reads the page's main region (its article, its main element, or the whole page) instead;
- up to 8 images, with their alt text;
- its links, each address once. When a link outside `nav`, `header`, `footer`, `aside`, and `form` elements has the page's title as its text, and points to another page, it MUST be the first link. The title also matches without a leading label, such as "Release:", and without a trailing site name.

The saved page MUST wait for the next digest run that the user starts. Saving the same address again, while the page is still waiting, MUST replace it, so that at most one page waits per address. While a digest is being made, saving an address that is already waiting MUST be refused, with a message to save it again when the digest is finished. After the page has been delivered in a digest, saving it again MUST add it again. The popup SHALL show how many pages are waiting, and MUST let the user remove the page just saved. Pages the browser does not let extensions read, such as browser settings pages and extension stores, MUST be reported as unreadable.

#### Scenario: Page without an article element
- **WHEN** the user saves a blog post whose page has a sidebar of recent posts, a sponsor block, and no `<article>` element
- **THEN** the saved text and links come from the post itself, not from the sidebar or the sponsor block

#### Scenario: Short note beside a sponsor banner
- **WHEN** the user saves a page whose post is one short sentence with a link, below a longer sponsor banner with its own link
- **THEN** the saved text is the post's sentence and its link, and none of the banner's text or links is saved

#### Scenario: Short post beside a longer sidebar
- **WHEN** the user saves a short post with one link, on a page whose sidebar holds tags and a promotion that are longer than the post
- **THEN** the saved text and links come from the post, not from the sidebar

#### Scenario: Release note whose title links to the release
- **WHEN** the user saves a release note titled "Release: garden-tools 1.2", whose title row links "garden-tools 1.2" to the release page, beside a longer description of the release
- **THEN** the link to the release page is the first saved link, and the description is the saved text

#### Scenario: Title that links to the page itself
- **WHEN** the page's heading is a link to the page's own address
- **THEN** that link is not added in front of the post's links

#### Scenario: Hidden text in the main region
- **WHEN** the page's main region holds a menu with the `hidden` attribute, a block hidden by a style rule, a paragraph hidden by its own style, and visible text
- **THEN** only the visible text is saved, and no link from the hidden menu is saved

#### Scenario: Reader-view method not available
- **WHEN** the reader-view method cannot run on the page
- **THEN** the page's main region is saved, without its hidden text

#### Scenario: Date shown only in the post
- **WHEN** the page states its publication time only in a date element at the top of its article
- **THEN** that time is saved as the publication time

#### Scenario: Save an article
- **WHEN** the user chooses "Add this page to my next digest" on an article
- **THEN** the popup says the page will be in the next digest, and the next run summarizes it

#### Scenario: Save again before the digest
- **WHEN** the user saves the same article twice before the next run
- **THEN** one page is waiting, with the content of the second save

#### Scenario: Save after delivery
- **WHEN** a saved page was delivered in a digest, and the user saves it again
- **THEN** it waits again, and the next run summarizes it again

#### Scenario: Save again while a digest is being made
- **WHEN** a digest run is in progress, and the user saves an address that is already waiting
- **THEN** the popup says to save it again when the digest is finished, and the waiting page is unchanged

#### Scenario: Remove the page just saved
- **WHEN** the user saves a page, then chooses to remove it
- **THEN** the page no longer waits, and the next run does not include it

#### Scenario: Unreadable page
- **WHEN** the user chooses "Add this page to my next digest" on the browser's settings page
- **THEN** the popup says the page cannot be read, and saves nothing

### Requirement: Read X posts with the author's own replies
On an X post page (`x.com` or `twitter.com`, at `/<user>/status/<id>`), the extension SHALL read the post's text, author, time, images, and links. It SHALL also read the replies visible on the page that the post's author wrote, and save them as the page's author replies. It MUST NOT read replies by anyone else. A link MUST be recorded with its destination address when the page shows that address in full, and MUST be left out when only a shortened link is available. When the page does not have the expected structure, the extension MUST fall back to reading it as a general page.

#### Scenario: Post with the author's replies
- **WHEN** the user saves an X post under which the author replied twice, and two other people replied
- **THEN** the saved page has the post and the author's two replies, and none of the other replies

#### Scenario: Post linking an article
- **WHEN** an X post links an article, and the page shows the article's full address
- **THEN** the saved page records that address, so that the next run can read the article as related context

### Requirement: What the extension never does
The extension MUST NOT:
- read cookies, saved passwords, or site storage;
- read any page in the background;
- scroll, click, or open pages by itself;
- ask for access to any site other than the CatchUp server on the local machine.

It MUST talk only to the CatchUp server address set in its options, `http://127.0.0.1:8000` by default, and the options MUST accept only an http address on `127.0.0.1` or `localhost`. Until it is connected, it MUST send nothing, and say how to connect.

#### Scenario: Installing the extension
- **WHEN** the user installs the extension
- **THEN** the browser asks for access only to `127.0.0.1` and `localhost`

#### Scenario: Not connected
- **WHEN** the user opens the popup before pasting a token
- **THEN** the popup says to connect the browser in CatchUp's Settings, and sends no request to any site

### Requirement: Install the extension from the repository
The README SHALL explain:
- how to build the extension, and load it unpacked in Chrome and Edge;
- how to connect it;
- what it reads, and when;
- that X's terms prohibit scraping in any form, so saving X pages is at the user's own risk.

#### Scenario: Setting up from the README
- **WHEN** a user follows the README's extension section on a machine with CatchUp running
- **THEN** they can load the extension, connect it, and save a page

### Requirement: Keep focus and announcements in the popup
The extension's popup SHALL keep keyboard focus and screen-reader announcements when its content changes.
- **Status line.** After the popup connects to CatchUp, it MUST keep one status line until it closes or shows the disconnected view. Every result message MUST be written to that status line, which stays in the popup when the rest of the content is replaced.
- **Focus after a change.** When new content replaces the popup's content, focus MUST move to this target:
  - after "Follow this site" or "Follow this account", and after the X token is saved: the preview's heading;
  - when the popup asks for the X token: the token field;
  - after the preview's Confirm or Cancel: "Follow this site" or "Follow this account";
  - after a page is saved or removed: "Add this page to my next digest";
  - when an action leads to the disconnected view: "Open options".
- **Busy buttons.** While "Follow this site", "Follow this account", "Add this page to my next digest", Remove, or the X token's Save is working, the button MUST stay focusable and be announced as unavailable, and activating it MUST do nothing.
- **Preview progress.** When a preview starts, the status line MUST say "Loading the preview…" until the preview answers, or until another action, such as saving the page, writes its own result to the status line.
- **Late previews.** When the popup's content was replaced before a preview answered, for example because the user saved the page meanwhile, the answer MUST be ignored: the preview is not shown, the status line is not changed, and focus does not move.

#### Scenario: Save a page with the keyboard
- **WHEN** a keyboard user presses "Add this page to my next digest" and the page is saved
- **THEN** focus is on "Add this page to my next digest", and the status line announces that the page will be in the next digest

#### Scenario: Preview and cancel
- **WHEN** a keyboard user chooses "Follow this site", then Cancel
- **THEN** focus moves to the preview's heading, then back to "Follow this site"

#### Scenario: One status line
- **WHEN** the user saves a page, removes it, and then follows the site
- **THEN** each result is announced through the same status line, which stayed in the popup throughout

#### Scenario: Follow pressed twice while loading
- **WHEN** the user presses "Follow this site" twice before the preview answers
- **THEN** one preview is requested, the button is announced as unavailable while it loads, and the status line says "Loading the preview…"

#### Scenario: Page saved while a preview loads
- **WHEN** the user chooses "Follow this site", then saves the page before the preview answers
- **THEN** the popup keeps the saved-page view with focus on "Add this page to my next digest", and the late preview is not shown
