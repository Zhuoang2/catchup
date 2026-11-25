import json

import httpx2
import pytest

from catchup.llm.anthropic_client import AnthropicModelClient
from catchup.llm.client import ModelClient
from catchup.llm.providers import DEFAULT_BASE_URL, DEFAULT_BASE_URLS, REASONING_CHOICES, make_model_client
from test_anthropic_client import BASE, error_response, stream_body
from test_model_errors import completion


@pytest.mark.parametrize("provider", [None, "openai_compatible", "anthropic"])
def test_factory_selects_provider_and_passes_options(provider):
    calls, sleeps = [], []

    def handle(request):
        assert request.url.host == "anthropic.example"
        assert request.url.path == "/v1/messages"
        calls.append(request)
        return error_response(529, "overloaded_error") if len(calls) == 1 else stream_body("{}")

    options = {"http_client": httpx2.Client(transport=httpx2.MockTransport(handle)), "sleep": sleeps.append}
    args = (BASE, "test-only-key", "claude-haiku-5-5")
    client = make_model_client(*args, **options) if provider is None else make_model_client(*args, provider, **options)
    try:
        if provider == "anthropic":
            assert isinstance(client, AnthropicModelClient)
            assert client.chat_json([], 200) == {}
            assert len(calls) == 2
            assert sleeps == [0.25]
        else:
            assert isinstance(client, ModelClient)
    finally:
        client.close()


def test_factory_refuses_unknown_provider():
    with pytest.raises(ValueError):
        make_model_client(BASE, "test-only-key", "", "gemini")


def test_default_base_urls():
    assert DEFAULT_BASE_URL == "https://api.deepseek.com"
    assert DEFAULT_BASE_URLS == {
        "openai_compatible": "https://api.deepseek.com", "anthropic": "https://api.anthropic.com",
    }


@pytest.mark.parametrize("provider", ["openai_compatible", "anthropic"])
def test_factory_passes_the_reasoning_choice(provider):
    requests, sleeps = [], []

    def handle(request):
        assert request.url.host == "anthropic.example"
        assert request.url.path == (
            "/v1/messages" if provider == "anthropic" else "/chat/completions"
        )
        requests.append(request)
        return stream_body("{}") if provider == "anthropic" else completion("{}")

    model = "claude-haiku-5-5" if provider == "anthropic" else "test-model"
    client = make_model_client(
        BASE, "test-only-key", model, provider, "low",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handle)), sleep=sleeps.append,
    )
    try:
        assert client.chat_json([{"role": "user", "content": "x"}], 100) == {}
        body = json.loads(requests[0].content)
        if provider == "anthropic":
            assert body["output_config"] == {"effort": "low"}
        else:
            assert body["reasoning_effort"] == "low"
    finally:
        client.close()


def test_reasoning_choices_per_provider():
    assert REASONING_CHOICES == {
        "openai_compatible": ("default", "low", "off"), "anthropic": ("default", "low"),
    }
