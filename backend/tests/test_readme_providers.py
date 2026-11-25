from pathlib import Path


def test_readme_documents_supported_model_providers():
    readme = " ".join((Path(__file__).resolve().parents[2] / "README.md").read_text().split())
    for phrase in (
        "Supported model providers", "OpenAI-compatible", "Anthropic", "https://api.anthropic.com",
        "claude-opus-5-5", "at least 16,000 output tokens", "fallback model",
        "Changing the provider or its URL requires entering the API key again",
    ):
        assert phrase in readme
