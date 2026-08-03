"""Registry for thumbnail-concept LLM providers.

Only `manual` exists today - it doesn't call any API. It saves each
prompt to a file and prints it for you to paste into Claude Pro
yourself, then reads the reply back from the terminal (see
manual_provider.py). No paid API is connected yet, matching this
agent's "manual mode first" scope.

To add a real provider later (Anthropic API, or anything else):
  1. Write thumbnail_agent/llm_providers/<name>_provider.py implementing
     LLMProvider (see llm_providers/base.py).
  2. Add one line to get_provider() below, e.g.:
       if name == "anthropic":
           from .anthropic_provider import AnthropicProvider
           return AnthropicProvider()
  3. Feed it the system/user prompts straight out of thumbnail_writer.py
     - no other file in this agent needs to change.
"""

SUPPORTED_PROVIDERS = ("manual",)  # future: anthropic


def get_provider(name):
    if name == "manual":
        from .manual_provider import ManualProvider

        return ManualProvider()

    raise NotImplementedError(
        f"No thumbnail LLM provider named '{name}' is connected yet (available: {SUPPORTED_PROVIDERS}). "
        "See README.md, 'Adding a provider', to wire one up."
    )
