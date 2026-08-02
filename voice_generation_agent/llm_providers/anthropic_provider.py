"""Claude (Anthropic API) implementation of the LLMProvider interface."""

import os

import anthropic

from .base import LLMProvider

DEFAULT_MODEL = "claude-opus-5"


class AnthropicProvider(LLMProvider):
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not found. Make sure it's set in your .env file."
            )
        self._client = anthropic.Anthropic(api_key=api_key)
        # Overridable via .env so you can trade quality for cost without touching code.
        self._model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)

    def generate(self, system, prompt, max_tokens=4096):
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.AuthenticationError:
            raise RuntimeError(
                "Anthropic API key was rejected. Double-check ANTHROPIC_API_KEY in .env."
            )
        except anthropic.RateLimitError:
            raise RuntimeError(
                "Anthropic API rate limit hit. Wait a bit and try again."
            )

        if response.stop_reason == "refusal":
            raise RuntimeError(
                "Claude declined this request (safety refusal). Try rephrasing the prompt."
            )

        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
