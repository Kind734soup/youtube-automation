"""Provider-agnostic entry point for AI text generation.

Everything else in thumbnail_agent calls generate() from here - never a
provider's SDK directly. Which provider actually runs is picked once,
based on the THUMBNAIL_LLM_PROVIDER setting in .env (defaults to
"manual" - see llm_providers/README notes in providers/__init__.py).

This is a deliberately separate env var from script_agent's
LLM_PROVIDER - the two agents are independent and one can run against a
live API while the other stays manual, or vice versa.

To add a new provider later:
  1. Write thumbnail_agent/llm_providers/<name>_provider.py implementing
     LLMProvider (see llm_providers/base.py).
  2. Add one line to get_provider() in llm_providers/__init__.py.
  3. Set THUMBNAIL_LLM_PROVIDER=<name> in .env.
No other file in this project has to change.
"""

import os

from dotenv import load_dotenv

from thumbnail_agent.llm_providers import get_provider

load_dotenv()

_provider = None


def default_provider_name():
    return os.environ.get("THUMBNAIL_LLM_PROVIDER", "manual").lower()


def generate(system, prompt, max_tokens=4096, provider_name=None):
    global _provider
    if provider_name:
        return get_provider(provider_name).generate(system, prompt, max_tokens=max_tokens)
    if _provider is None:
        _provider = get_provider(default_provider_name())
    return _provider.generate(system, prompt, max_tokens=max_tokens)
