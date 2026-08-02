"""Provider-agnostic entry point for AI text generation.

Everything else in script_agent calls generate() from here - never a
provider's SDK directly. Which provider actually runs is picked once,
based on the LLM_PROVIDER setting in .env (defaults to "anthropic").

To add a new provider later:
  1. Write script_agent/llm_providers/openai_provider.py implementing
     LLMProvider (see llm_providers/base.py).
  2. Add one line to _build_provider() below.
  3. Set LLM_PROVIDER=openai in .env.
No other file in this project has to change.
"""

import os

from dotenv import load_dotenv

load_dotenv()

_provider = None


def _build_provider():
    name = os.environ.get("LLM_PROVIDER", "anthropic").lower()

    if name == "anthropic":
        from script_agent.llm_providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider()

    if name == "manual":
        from script_agent.llm_providers.manual_provider import ManualProvider

        return ManualProvider()

    raise ValueError(f"Unknown LLM_PROVIDER '{name}'. Supported: anthropic, manual")


def generate(system, prompt, max_tokens=4096):
    global _provider
    if _provider is None:
        _provider = _build_provider()
    return _provider.generate(system, prompt, max_tokens=max_tokens)
