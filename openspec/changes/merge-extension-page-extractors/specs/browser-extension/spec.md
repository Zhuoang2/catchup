# Spec Delta

## MODIFIED Requirements

### Requirement: Add the current page to the next digest
The popup SHALL offer "Add this page to my next digest". The extension MUST read the page only when the user chooses this, and only as it is rendered in the active tab at that moment. It MUST read only what the page shows: text, images, and links inside an element that the page hides, for example with the `hidden` attribute or a style rule, MUST NOT be read. It reads:
- the page's address and title;
- its site name, author, and publication time, when the page states them, in its metadata or in a date element of the post;
- its main text, up to 16,000 characters, found with a reader-view method so that navigation, sidebars, sponsor blocks, and ads are left out. On a short page, the main text MUST come from the post itself, even when a sponsor block or a sidebar beside it is longer. When the reader-view method finds no text, the extension reads the page's main region (its article, its main element, or the whole page) instead;
- up to 8 images, with their alt text;
- its links, each address once. When a link outside navigation, headers, footers, and sidebars has the page's title as its text, and points to another page, it MUST be the first link. The title also matches without a leading label, such as "Release:", and without a trailing site name.

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
