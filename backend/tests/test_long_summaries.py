import pytest

from catchup.digest.summarize import SummaryInput, split_parts, summarize_items
from catchup.llm.prompts import SUMMARY_MAX_TOKENS


def paragraphs(count: int) -> str:
    return "\n\n".join(f"{index:04d} " + "word " * 199 for index in range(count))


class CaptureModel:
    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def chat_json(self, messages, max_tokens):
        self.calls.append((messages, max_tokens))
        if self.failure and len(self.calls) == self.failure:
            from catchup.llm.client import ProviderError
            raise ProviderError("transient")
        return {"summary": "Overview.\n- First point\n- Final point"}


def inputs(text, origin="feed"):
    return [SummaryInput(1, "Long item", text, None, None, origin)]


def run(model, text, budget, origin="feed"):
    results = []
    summarize_items(model, inputs(text, origin), "en", budget, results.append)
    return results[0]


def test_large_context_window_uses_single_call_without_truncation():
    text = paragraphs(170)[:169_961]
    model = CaptureModel()
    result = run(model, text, max(2_000, 1_000_000 - SUMMARY_MAX_TOKENS - 2_000),
                 "transcript")
    assert not result.unavailable and len(model.calls) == 1
    assert text in model.calls[0][0][1]["content"]
    assert "no visual content was seen" in model.calls[0][0][0]["content"]
    assert "3–6 key points" in model.calls[0][0][0]["content"]


@pytest.mark.parametrize("budget,count", [(60_000, 170), (20_000, 51)])
def test_split_into_three_parts_and_combine_without_dropping_text(budget, count):
    text = paragraphs(count)
    text = text[:50_000 if budget == 20_000 else 169_961]
    assert len(text) > budget * 2
    parts = split_parts(text, budget)
    assert len(parts) == 3
    assert all(len(part) <= budget for part in parts)
    assert "".join(parts) == text
    model = CaptureModel()
    result = run(model, text, budget, "transcript")
    assert not result.unavailable
    assert len(model.calls) == 4
    assert all(f"part {index} of 3" in model.calls[index - 1][0][0]["content"]
               for index in range(1, 4))
    assert [call[0][1]["content"].split("Content:\n", 1)[1] for call in model.calls[:3]] == parts
    assert "- First point" in model.calls[-1][0][1]["content"]


def test_long_prompt_only_for_transcripts_above_threshold():
    for origin, length, expected in [
        ("feed", 21_000, False), ("transcript", 20_000, False), ("transcript", 20_001, True),
    ]:
        model = CaptureModel()
        run(model, "x " * (length // 2) + "x" * (length % 2), 60_000, origin)
        assert ("3–6 key points" in model.calls[0][0][0]["content"]) is expected


def test_part_failure_marks_item_unavailable():
    model = CaptureModel(failure=2)
    result = run(model, paragraphs(170), 60_000)
    assert result.unavailable and result.summary is None
    assert len(model.calls) == 2


def test_unspaced_chinese_text_is_losslessly_split_and_summarized():
    text = "中文" * 45_000
    parts = split_parts(text, 60_000)
    assert len(parts) == 2
    assert all(len(part) <= 60_000 for part in parts)
    assert "".join(parts) == text
    result = run(CaptureModel(), text, 60_000, "transcript")
    assert not result.unavailable


def test_overflowing_separators_and_sentence_preference():
    text = "a" * 99 + " " * 102
    parts = split_parts(text, 100)
    assert all(len(part) <= 100 for part in parts)
    assert "".join(parts) == text
    text = "中" * 94 + "。" + "文" * 20
    parts = split_parts(text, 100)
    assert parts[0].endswith("。")
    assert "".join(parts) == text
