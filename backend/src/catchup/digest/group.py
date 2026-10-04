"""Validate model topic placement without trusting model-provided citations."""

import json
from dataclasses import dataclass
from typing import Any

from catchup.llm.client import ModelClient, ProviderError
from catchup.llm.prompts import group_messages, grouping_max_tokens, merge_messages


@dataclass(frozen=True)
class GroupItem:
    id: int
    title: str
    source_name: str
    summary: str | None


@dataclass
class Topic:
    title: str
    overview: str
    item_ids: list[int]


def _valid_topics(response: dict[str, Any], refs: dict[str, int], field: str, language: str) -> list[Topic]:
    topics = response.get("topics")
    if not isinstance(topics, list):
        raise ProviderError("The model provider returned invalid topics.")
    placed: set[int] = set()
    result: list[Topic] = []
    for topic in topics:
        if not isinstance(topic, dict):
            continue
        title, overview, entries = topic.get("title"), topic.get("overview"), topic.get(field)
        if not isinstance(title, str) or not title.strip() or not isinstance(overview, str) or not isinstance(entries, list):
            continue
        ids = []
        for ref in entries:
            if isinstance(ref, str) and ref in refs and refs[ref] not in placed:
                ids.append(refs[ref])
                placed.add(refs[ref])
        if ids:
            result.append(Topic(title.strip(), overview.strip(), ids))
    missing = [item_id for item_id in refs.values() if item_id not in placed]
    if missing:
        result.append(Topic("其他" if language == "zh-Hans" else "Other", "", missing))
    return result


def _payload(items: list[GroupItem]) -> str:
    return json.dumps([
        {"ref": f"i{index}", "title": item.title, "source": item.source_name,
         "summary": item.summary or "Summary unavailable"}
        for index, item in enumerate(items, 1)
    ], ensure_ascii=False)


def group_items(client: ModelClient, items: list[GroupItem], language: str, batch_chars: int) -> list[Topic]:
    if not items:
        return []
    payload = _payload(items)
    if len(payload) <= batch_chars or len(items) == 1:
        response = client.chat_json(group_messages(payload, language), max_tokens=grouping_max_tokens(len(items)))
        return _valid_topics(response, {f"i{n}": item.id for n, item in enumerate(items, 1)}, "item_refs", language)

    batches: list[list[GroupItem]] = []
    current: list[GroupItem] = []
    for item in items:
        if current and len(_payload([*current, item])) > batch_chars:
            batches.append(current)
            current = []
        current.append(item)
    if current:
        batches.append(current)
    if len(batches) == 1:
        # One oversized item cannot be split further.
        return group_items(client, items, language, len(payload))

    batch_topics: list[Topic] = []
    for batch in batches:
        batch_topics.extend(group_items(client, batch, language, len(_payload(batch))))
    refs = {f"b{n}": n for n in range(1, len(batch_topics) + 1)}
    merge_input = json.dumps([
        {"ref": ref, "title": topic.title, "overview": topic.overview}
        for ref, topic in zip(refs, batch_topics)
    ], ensure_ascii=False)
    merged = client.chat_json(merge_messages(merge_input, language),
                              max_tokens=grouping_max_tokens(len(batch_topics)))
    placements = _valid_topics(merged, refs, "topic_refs", language)
    return [
        Topic(topic.title, topic.overview, [
            item_id for batch_id in topic.item_ids for item_id in batch_topics[batch_id - 1].item_ids
        ])
        for topic in placements
    ]
