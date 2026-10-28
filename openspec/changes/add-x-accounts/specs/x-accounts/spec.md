## ADDED Requirements

### Requirement: Recognize X account addresses
The system SHALL treat a pasted address as an X account address when its host is `x.com` or `twitter.com`, with or without `www.` or `mobile.`. Its path must be `/<username>`, `/<username>/<section>`, or `/<username>/status/<id>`, where the username is 1 to 15 letters, digits, or underscores. A post address identifies the post's author.

X's own pages are not accounts, and the system MUST report "not an X account" for them. These are first path segments such as `home`, `explore`, `search`, `i`, `settings`, `notifications`, `messages`, `compose`, `login`, `signup`, `tos`, `privacy`, `hashtag`, `intent`, and `share`. Addresses on any other host under `x.com` or `twitter.com`, such as `help.x.com`, are not accounts either.

The system MUST NOT request any page on x.com or twitter.com. It reads X only through the X API, with the user's token.

#### Scenario: Profile address
- **WHEN** the user pastes `https://x.com/simonw`
- **THEN** the system treats it as the X account `simonw`, and requests nothing from x.com

#### Scenario: Post address
- **WHEN** the user pastes `https://twitter.com/simonw/status/1890000000000000000`
- **THEN** the system treats it as the X account `simonw`

#### Scenario: Mobile address
- **WHEN** the user pastes `https://mobile.x.com/simonw/media`
- **THEN** the system treats it as the X account `simonw`

#### Scenario: X's own page
- **WHEN** the user pastes `https://x.com/home`
- **THEN** the system reports that the address is not an X account, and saves nothing

#### Scenario: Another X site
- **WHEN** the user pastes `https://help.x.com/en`
- **THEN** the system reports that the address is not an X account, requests nothing from help.x.com, and saves nothing

### Requirement: Store the user's X API token
The system SHALL store one X API token, an app-only Bearer token from the user's own X developer account, encrypted with the secret supplied through the instance's environment, as it stores the model key.
- It MUST NOT return the token, or write it to logs.
- It MAY return only the token's last four characters.
- Saving MUST be refused when the instance secret is missing.

Settings SHALL let the user save, replace, remove, and test the token. Testing MUST NOT read any post or account. A request from the browser extension MAY save a token only when none is saved; replacing or removing a token is done in Settings.

#### Scenario: Saved token
- **WHEN** a token is saved and the user opens Settings
- **THEN** the "X accounts" group reads "Saved token ending in" followed by its last four characters, and the token input is empty

#### Scenario: Missing instance secret
- **WHEN** the instance secret is not set and the user saves an X token
- **THEN** saving is refused with the same message as for the model key, and nothing is stored

#### Scenario: Remove the token
- **WHEN** the user removes the token
- **THEN** no token is stored, the next run reports each X account as needing a token, and an account preview shown before cannot be confirmed

#### Scenario: Extension cannot replace a token
- **WHEN** a token is saved and the extension sends another token
- **THEN** the request is refused, and the saved token is unchanged

### Requirement: Preview an X account
When the pasted address is an X account address, the preview SHALL look the account up through the X API, and show:
- the account's display name, `@username`, and profile address;
- the kind "X account", and that posts are read through the X API with the user's token;
- up to five of the account's recent posts, without retweets or replies, each with the start of its text, its link, and its time.

The preview MUST make at most one account lookup and read at most five posts. Previewing MUST NOT save anything.

The system SHALL tell the user why an X account cannot be added:
- no X token is saved: "X token needed", with a way to paste one in place;
- X rejected the token;
- the account does not exist, or is suspended;
- the account is protected, because its posts cannot be read with an app-only token;
- X is rate limiting requests, with when to try again;
- the account is already followed.

#### Scenario: Preview with a saved token
- **WHEN** a token is saved and the user pastes `https://x.com/simonw`
- **THEN** the preview shows the account's name, `@simonw`, the kind "X account", and up to five recent posts

#### Scenario: No token yet
- **WHEN** no X token is saved and the user pastes an X profile address
- **THEN** the system reports "X token needed", offers a field to paste the token, and saves nothing

#### Scenario: Protected account
- **WHEN** the account is protected
- **THEN** the preview reports that protected accounts cannot be followed, and saves nothing

#### Scenario: Rejected token
- **WHEN** X answers the lookup with 401
- **THEN** the system reports that X rejected the token, and says to replace it in Settings

### Requirement: Follow an X account
Confirming an X account preview SHALL save a source of the kind "X account":
- its title is the account's display name;
- its site address is the account's profile address;
- it is identified by the account's X id, so the same account cannot be followed twice, even under a new username.

Among the posts the preview read, up to five from the last seven days SHALL be marked new, like a feed source's first entries. Posts published before the account was followed MUST NOT be read by later runs.

#### Scenario: Follow an account
- **WHEN** the user confirms the preview of an account that posted 2 times in the last 7 days
- **THEN** the account is saved, and the next run includes those 2 posts

#### Scenario: Account renamed
- **WHEN** an account already followed changes its username, and the user pastes its new address
- **THEN** the system reports that the account is already followed

### Requirement: Read new posts on each run
Each digest run SHALL read each followed X account's posts published since the newest post it has read, through the X API.
- Retweets MUST be left out.
- A reply by the account in a conversation started by one of its own posts read in the same run SHALL be kept as that post's author reply, up to 10 replies and 4,000 characters per post.
- Every other reply MUST be left out.
- Each kept post becomes an item:
  - its link is the post's address on x.com;
  - its title is the start of its text;
  - its site name is "X · <display name>";
  - its text is the post's full text, including long posts, with every shortened `t.co` link replaced by its destination;
  - its links are those destinations;
  - its photos, with their alt text, are image candidates.

#### Scenario: New post
- **WHEN** an account posted once since the last run
- **THEN** the run includes that post under "X · <display name>", linking to the post

#### Scenario: Thread by the author
- **WHEN** an account posted a post, then replied to it twice in the same thread, all since the last run
- **THEN** the run includes the first post, with the two replies as its author replies

#### Scenario: Reply to someone else
- **WHEN** an account's only new post is a reply to another person's post
- **THEN** the run includes nothing from that account

#### Scenario: Long post with a link
- **WHEN** a new post is longer than 280 characters, and contains a shortened link to an article
- **THEN** the item holds the post's full text with the article's address, and the article can be read as related context

### Requirement: Limit X reads per run
Each run SHALL read at most `CATCHUP_X_READS_PER_RUN` posts from the X API, 200 by default. Every post the API returns counts, including posts that are left out.
- Accounts SHALL be read starting with the one checked longest ago.
- An account that the limit leaves unread SHALL be recorded with the outcome `deferred`, shown as "Waits for the next run".
- When the limit is reached partway through an account, the posts already read SHALL be kept, and the account's remaining posts SHALL be read by later runs, before its newer posts.

A post MUST NOT be lost because of the limit, unless the X API no longer returns it. The run SHALL report how many X posts it read, and how many accounts have posts waiting.

#### Scenario: Limit reached before an account
- **WHEN** the limit is 200, and the first accounts read return 200 posts
- **THEN** each remaining account is recorded as `deferred`, and is read first in the next run

#### Scenario: Limit reached within an account
- **WHEN** an account has 150 new posts, and 50 reads are left
- **THEN** the run keeps the 50 newest posts it read, and a later run reads the other 100 before any newer post

#### Scenario: New posts on several pages
- **WHEN** an account has 150 new posts, and 200 reads are left
- **THEN** the run reads all 150 posts, the account has no posts waiting, and the next run reads only posts newer than those

#### Scenario: Run result
- **WHEN** a run read 37 X posts, and 2 accounts have posts waiting
- **THEN** the run result shows "37 X posts read" and "2 X accounts have posts waiting for the next run", with singular forms "1 X post read" and "1 X account has posts waiting for the next run"

#### Scenario: Deferred account read first next time
- **WHEN** the limit is 5, account A is read and account B is deferred in one run, and both have new posts before the next run
- **THEN** the next run reads B before A

### Requirement: Report X API errors
A failed X account check SHALL be recorded as `failed`, with a reason the user can act on, and other sources SHALL still be checked.
- When X answers 429, the account SHALL be shown as rate limited, as for other sources.
- When X answers 401 or 403, the reason SHALL be that X rejected the token.
- When no token is saved, the reason SHALL be that an X token is needed.
- When the account no longer exists, is suspended, or became protected, the reason SHALL say so.

#### Scenario: Rate limited
- **WHEN** X answers 429 while an account is read
- **THEN** that account is shown as "Rate limited · try later", and the next account is still read if reads remain

#### Scenario: Token removed
- **WHEN** a run starts with X accounts followed and no token saved
- **THEN** each X account is `failed` with "X token needed", and website, podcast, and YouTube sources are checked as usual

### Requirement: Clear delivered X posts
After a run delivers an X post in a digest, the system SHALL remove the post's stored text, author replies, and the context text gathered for it. The digest SHALL keep the item's summary, title, link, source name, and "Also read" links. Deleting an X account source SHALL delete the posts stored for it.

#### Scenario: After delivery
- **WHEN** a run delivers an X post
- **THEN** the stored item no longer holds the post's text or replies, and the saved digest still shows its summary and link

### Requirement: Delete all X data
Settings SHALL offer "Delete all X data", which asks for confirmation in place. Confirming SHALL remove, in one step:
- the saved X token;
- every followed X account, and every post stored for it;
- every item from an X account in saved digests, with its title, summary, link, images, and "Also read" links;
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

