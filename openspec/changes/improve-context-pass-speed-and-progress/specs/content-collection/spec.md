## ADDED Requirements

### Requirement: Read linked pages for several items at the same time
The context pass SHALL gather context for up to 4 items at the same time, and MUST NOT work on more. It starts the items in the order it plans them. Within one item, its pages MUST still be read one after another, in the order "Gather related context for website items" gives, with the same caps. Across items:
- requests to the same host MUST stay at least 1 second apart, as "Space requests to the same host during a run" requires;
- robots.txt MUST be requested at most once per origin in the run, even when several items need it at the same moment;
- the run MUST NOT make more context requests than the per-run limit, robots.txt requests included.

When the per-run limit runs out, which items got their context can depend on how fast their pages answered. Each item keeps the context it gathered, as before.

#### Scenario: Items on different sites
- **WHEN** eight pending items each link to one page on a site of its own, and every page is slow to answer
- **THEN** pages for four items are requested at the same time, and never more than four

#### Scenario: Two items on one site
- **WHEN** two pending items, read at the same time, link to pages on the same site
- **THEN** that site's robots.txt is requested once, and the two page requests start at least 1 second apart

#### Scenario: Per-run limit with items read at the same time
- **WHEN** eight pending items each link to three pages on a site of its own, and the per-run limit is 10
- **THEN** the run makes at most 10 context requests, including robots.txt, and the run succeeds
