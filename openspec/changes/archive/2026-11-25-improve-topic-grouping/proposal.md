# Proposal

## Why

Real digests split related items into many small topics (#32). In a Simplified Chinese digest made with `deepseek-flash` on 2026-10-13, 7 items became 6 topics (`docs/process/test-report-redesign-ui-ux.md:256`). Related news, such as two Apple stories and several AI stories, ended up in separate topics, so the index got long and the topic overviews repeated the item summaries.

The grouping instruction gives the model no guidance. `group_messages` (`backend/src/catchup/llm/prompts.py:133-143`) says only "Group the supplied items by topic", and it has not changed since it was written in 89bdc02 (2026-10-03). The merge instruction for batched grouping (`prompts.py:146-156`) says only "Combine similar batch topics". Nothing limits the number of topics (`backend/src/catchup/digest/group.py:33-55`), and the `digest-generation` spec says nothing about topic count or size. This was the second cause named in #25. The user split it out on 2026-10-16, after #25's layout change made single-item topics readable.

## What Changes

- **Broader topics in the grouping call.** The grouping instruction asks the model to:
  - put items about the same subject (one company, product, event, or field) in one topic, even when they come from different sources;
  - prefer fewer, broader topics, with at most a number of topics that grows with the item count;
  - give an item a topic of its own only when it fits no other topic.
- **A topic limit.** The limit is the smallest whole number at least the square root of twice the item count, but never more than the item count or 12. For example: 1 item, 1 topic; 2 items, 2; 7 items, 4; 11 items, 5; 30 items, 8; 61 or more items, 12. Design D2 lists the alternatives for the user.
- **Overviews that connect the items.** Each topic overview is 1–2 sentences about what the topic's items cover together, without repeating each item's summary.
- **Batched grouping uses the same rules.**
  - Each batch call uses the limit for its own items.
  - The call that combines batch topics uses the limit for all the items in the run, and is told how many items each batch topic holds.
- **The limit is guidance only.** When the model returns more topics than asked, the digest keeps them as the model answered, under today's validation rules. No item is dropped or moved, and no extra model call is made. Design D1 lists the alternatives for the user.
- No API, data model, migration, setting, or frontend change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `digest-generation`: new requirement "Group related items into broad topics", covering:
  - the grouping instructions;
  - the topic limit, for single and batched grouping;
  - the overview rule;
  - keeping a grouping that has more topics than the limit.

  The existing requirement "Summarize items once and group them by topic" does not change.

## Impact

- **Code:**
  - `backend/src/catchup/llm/prompts.py`: a new `topic_limit` function; `group_messages` and `merge_messages` take the limit and carry the new instructions.
  - `backend/src/catchup/digest/group.py`: passes the limits, and adds each batch topic's item count to the merge input.
- **Tests:** `backend/tests/test_digest_stages.py` and `backend/tests/test_digest_runner.py`.
- **Docs:** the decision log (D-043), the requirements-changes table, a test report, and the AI usage log. `README.md` does not change (design D5).
- **Out of scope:**
  - ranking topics or items, and showing only the N most important items (#9, the next change on the same pipeline);
  - the topic order, the "Other" fallback, the token budgets, and batch sizes;
  - the size of the combining call's input on small context windows (a gap that exists today; see design "Risks");
  - the reading layout (#25);
  - re-grouping digests saved earlier.
