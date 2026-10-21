## ADDED Requirements

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
The extension's popup SHALL offer "Follow this site" for the active tab. It MUST preview the tab's address with the same preview the Sources page uses, show the same details and error messages, and save the source only after the user confirms. On an X page, it MUST say that X accounts cannot be followed, and offer "Add this page to my next digest" instead.

#### Scenario: Follow a blog
- **WHEN** the user is reading a blog post and chooses "Follow this site", then confirms
- **THEN** the blog's feed is saved as a source, as if the post's address had been pasted into the Sources page

#### Scenario: Already followed
- **WHEN** the user chooses "Follow this site" on a site that is already a source
- **THEN** the popup says the site is already followed, and saves nothing

#### Scenario: X profile
- **WHEN** the user chooses "Follow this site" on an X profile
- **THEN** the popup says X accounts cannot be followed, and offers adding the page instead

### Requirement: Add the current page to the next digest
The popup SHALL offer "Add this page to my next digest". The extension MUST read the page only when the user chooses this, and only as it is rendered in the active tab at that moment. It reads:
- the page's address and title;
- its site name, author, and publication time, when the page states them;
- its main text, up to 16,000 characters;
- up to 8 images, with their alt text;
- its links.

The saved page MUST wait for the next digest run that the user starts. Saving the same address again, while the page is still waiting, MUST replace it, so that at most one page waits per address. While a digest is being made, saving an address that is already waiting MUST be refused, with a message to save it again when the digest is finished. After the page has been delivered in a digest, saving it again MUST add it again. The popup SHALL show how many pages are waiting, and MUST let the user remove the page just saved. Pages the browser does not let extensions read, such as browser settings pages and extension stores, MUST be reported as unreadable.

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
