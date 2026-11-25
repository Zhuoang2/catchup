"""Select a native model adapter for the saved provider."""

from catchup.llm.anthropic_client import AnthropicModelClient, REASONING_EFFORTS as ANTHROPIC_EFFORTS
from catchup.llm.client import ModelClient, REASONING_EFFORTS as OPENAI_EFFORTS

PROVIDERS = ("openai_compatible", "anthropic")
REASONING_CHOICES = {
    "openai_compatible": ("default", *OPENAI_EFFORTS),
    "anthropic": ("default", *ANTHROPIC_EFFORTS),
}
DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_BASE_URLS = {
    "openai_compatible": DEFAULT_BASE_URL,
    "anthropic": "https://api.anthropic.com",
}


def make_model_client(
    base_url: str, api_key: str, model: str = "", provider: str = "openai_compatible",
    reasoning: str = "default", **options,
) -> ModelClient | AnthropicModelClient:
    if provider == "openai_compatible":
        return ModelClient(base_url, api_key, model, reasoning=reasoning, **options)
    if provider == "anthropic":
        return AnthropicModelClient(base_url, api_key, model, reasoning=reasoning, **options)
    raise ValueError("Choose a supported model provider.")
