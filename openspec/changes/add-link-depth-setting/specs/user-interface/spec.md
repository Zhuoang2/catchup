# Spec Delta

## ADDED Requirements

### Requirement: Choose linked pages in Settings
Settings SHALL offer "Linked pages" in the Digest group: a choice of Off, Shallow, and Normal, the levels of "Choose how many linked pages a run reads" in `content-collection`. It MUST show the saved level, and Normal when none was saved.
- Off MUST be labeled "Off — no linked pages or author replies".
- Shallow and Normal MUST each name how many pages per item they read, with the numbers the server uses, as "Shallow — up to N pages per item" and "Normal — up to N pages per item".
- A note MUST say that each page read adds time to a run and up to 3,000 characters to that item's summary request (up to 4,000 for author replies), which uses more tokens, and MUST name the run's limit of page requests, robots.txt files included. It MUST be associated with the choice for assistive technology.

The choice MUST be saved by Save, together with the other Digest settings, and its result shown as "Show Settings save results at Save" describes.

#### Scenario: Default choice
- **WHEN** no level was saved, the server uses its default numbers, and the user opens Settings
- **THEN** "Linked pages" shows "Normal — up to 8 pages per item", its other options read "Off — no linked pages or author replies" and "Shallow — up to 3 pages per item", and its description names a limit of 60 page requests per run

#### Scenario: Server numbers
- **WHEN** the server's `CATCHUP_LINKS_PER_ITEM` is 5 and `CATCHUP_CONTEXT_FETCHES_PER_RUN` is 40, and the user opens Settings
- **THEN** the options read "Shallow — up to 3 pages per item" and "Normal — up to 5 pages per item", and the description names a limit of 40 page requests per run

#### Scenario: Save Off
- **WHEN** the user chooses Off and clicks Save
- **THEN** Off is saved with the other Digest settings, "Settings saved." is announced, and Settings shows Off when it is opened again
