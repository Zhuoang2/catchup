import threading

import pytest

from catchup.digest.group import GroupItem, group_items
from catchup.digest.summarize import SummaryInput, summarize_items
from catchup.llm.client import AuthFailed, ProviderError
from catchup.llm.prompts import grouping_max_tokens, summary_messages


class FakeModel:
    def __init__(self, responses=()):
        self.responses = iter(responses)
        self.calls = []

    def chat_json(self, messages, max_tokens):
        self.calls.append((messages, max_tokens))
        answer = next(self.responses)
        if isinstance(answer, Exception):
            raise answer
        return answer


def test_summary_cache_language_prompt_truncation_and_unavailable():
    cached = SummaryInput(1, "Cached", "content", "In English", "en")
    new = SummaryInput(2, "Fresh", "1234567890", None, None)
    failing = SummaryInput(3, "Fails", "failure", None, None)
    class PerItemModel(FakeModel):
        def chat_json(self, messages, max_tokens):
            self.calls.append((messages, max_tokens))
            if "Title: Fails" in messages[1]["content"]:
                raise ProviderError("failed")
            return {"summary": "Fresh summary"}

    client = PerItemModel()
    results = []
    summarize_items(client, [cached, new, failing], "en", 5, results.append)
    assert len(client.calls) == 2
    assert next(r for r in results if r.id == 1).summary == "In English"
    assert next(r for r in results if r.id == 3).unavailable
    assert any("12345" in str(call) and "English" in str(call) and "json" in str(call)
               for call in client.calls)
    assert all("1234567890" not in str(call) and tokens == 4096 for call, tokens in client.calls)

    changed = FakeModel([{"summary": "中文摘要"}])
    output = []
    summarize_items(changed, [cached], "zh-Hans", 100, output.append)
    assert len(changed.calls) == 1
    assert "Simplified Chinese" in str(changed.calls[0])
    assert output[0].summary == "中文摘要"


def test_original_language_instruction():
    client = FakeModel([{"summary": "原文摘要"}])
    summarize_items(client, [SummaryInput(1, "标题", "正文", None, None)],
                    "original", 200, lambda _: None)
    assert "original language of this item" in str(client.calls[0])


def test_summary_prompt_focuses_on_substance_and_retains_json_language():
    system = summary_messages("Post", "A social post", "zh-Hans")[0]["content"]
    assert "2–4 sentences" in system and "substance" in system
    for phrase in ("platform identifiers", "user handles", "submission metadata", "timestamps",
                   "unless essential", "no substantive content", "one short sentence"):
        assert phrase in system
    assert "Simplified Chinese" in system
    assert "json" in system
    assert 'Example output: {"summary":' in system


def test_auth_failure_does_not_wait_for_another_model_worker():
    entered, release = threading.Event(), threading.Event()

    class BlockingModel(FakeModel):
        def chat_json(self, messages, max_tokens):
            if "Title: Slow" in messages[1]["content"]:
                entered.set()
                assert release.wait(timeout=5)
                return {"summary": "Slow result"}
            assert entered.wait(timeout=5)
            raise AuthFailed("Rejected")

    finished = threading.Event()
    failures = []

    def execute():
        try:
            with pytest.raises(AuthFailed):
                summarize_items(
                    BlockingModel(),
                    [SummaryInput(n, title, "text", None, None)
                     for n, title in ((1, "Rejected"), (2, "Slow"))],
                    "en", 100, lambda _: None,
                )
        except Exception as exc:
            failures.append(exc)
        finally:
            finished.set()

    thread = threading.Thread(target=execute)
    thread.start()
    try:
        assert entered.wait(timeout=5)
        assert finished.wait(timeout=5)
        assert not failures
    finally:
        release.set()
        thread.join(timeout=5)


def test_group_discards_unknown_refs_and_duplicates_and_places_omissions():
    items = [GroupItem(n, f"Title {n}", "Source", "Summary") for n in range(1, 4)]
    client = FakeModel([{"topics": [
        {"title": "First", "overview": "One", "item_refs": ["i1", "i999", "i2"]},
        {"title": "Second", "overview": "Two", "item_refs": ["i1"]},
    ]}])
    topics = group_items(client, items, "zh-Hans", 10000)
    assert [(topic.title, topic.item_ids) for topic in topics] == [("First", [1, 2]), ("其他", [3])]
    assert "Simplified Chinese" in str(client.calls[0])
    assert '"source": "Source"' in str(client.calls[0])
    assert "json" in str(client.calls[0])
    assert client.calls[0][1] == 8192 + 24 * len(items)


def test_batch_merge_covers_every_item_once():
    items = [GroupItem(n, f"Title {n}", "Source", "Summary") for n in range(1, 5)]
    client = FakeModel([
        {"topics": [{"title": f"Batch {n}", "overview": "Overview", "item_refs": ["i1"]}]}
        for n in range(1, 5)
    ] + [{"topics": [
        {"title": "Merged", "overview": "Combined", "topic_refs": ["b1", "b2", "b1", "b999"]},
    ]}])
    topics = group_items(client, items, "original", 10)
    assert [(topic.title, topic.item_ids) for topic in topics] == [
        ("Merged", [1, 2]), ("Other", [3, 4]),
    ]
    assert len(client.calls) == 5
    assert "language most items" in str(client.calls[-1])
    assert all(tokens == 8192 + 24 for _, tokens in client.calls[:-1])
    assert client.calls[-1][1] == 8192 + 24 * 4


def test_grouping_budget_is_capped():
    assert grouping_max_tokens(2000) == 32768


@pytest.mark.parametrize("language, expected", [
    ("en", "Other"), ("zh-Hans", "其他"), ("original", "Other"), ("French", "Other"),
])
def test_unplaced_topic_title_follows_digest_language(language, expected):
    client = FakeModel([{"topics": []}])
    topics = group_items(client, [GroupItem(1, "Title", "Source", "Summary")], language, 10000)
    assert [(topic.title, topic.item_ids) for topic in topics] == [(expected, [1])]


def test_unplaced_batch_topic_title_follows_digest_language():
    client = FakeModel([
        {"topics": [{"title": "First", "overview": "One", "item_refs": ["i1"]}]},
        {"topics": [{"title": "Second", "overview": "Two", "item_refs": ["i1"]}]},
        {"topics": []},
    ])
    topics = group_items(client, [GroupItem(n, "Title", "Source", "Summary") for n in (1, 2)],
                         "zh-Hans", 10)
    assert [(topic.title, topic.item_ids) for topic in topics] == [("其他", [1, 2])]
