## MODIFIED Requirements

### Requirement: Delete all X data
Settings SHALL offer "Delete all X data", which asks for confirmation in place. Confirming SHALL remove, in one step:
- the saved X token;
- every followed X account, and every post stored for it;
- every item from an X account in saved digests, with its title, summary, link, images, and "Also read" links, and the user's bookmark, like, rating, and note on it;
- every account preview not yet confirmed;
- the overview of every saved topic that held such an item, because it was written from those items; such a topic's title SHALL become "Other" ("其他" in a Chinese digest). A topic left with no items, and a digest left with no items, SHALL be removed. A digest's item and source counts SHALL be lowered to match.

Pages saved from x.com with the browser extension are not followed-account data, and SHALL remain; the confirmation MUST say so.

Other sources, their items, and digest items from other sources MUST remain. Deleting MUST be refused while a digest run is active. X's developer terms treat summaries as derived X content, which must be deleted when the user's access ends or when X or a post's author asks; this is how the user does so.

#### Scenario: Delete all X data
- **WHEN** two X accounts are followed, and a saved digest holds one X item and one website item in the same topic, and the user confirms "Delete all X data"
- **THEN** the token, both accounts, and their stored posts are removed; the digest keeps the website item, the topic's overview is cleared, and its title becomes "Other"

#### Scenario: Digest with only X items
- **WHEN** a saved digest holds only X items, and the user deletes all X data
- **THEN** that digest is removed from History

#### Scenario: During a run
- **WHEN** a digest run is active, and the user confirms "Delete all X data"
- **THEN** it is refused with a message to try again after the run, and nothing is deleted

#### Scenario: Marks on X items
- **WHEN** a saved X item is bookmarked and rated with a note, a website item in the same digest is bookmarked, and the user deletes all X data
- **THEN** the X item's marks and note are removed with it, and the website item stays bookmarked
