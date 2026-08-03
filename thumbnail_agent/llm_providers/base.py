"""The contract every thumbnail-concept LLM provider will implement.

thumbnail_writer.py only ever talks to this interface. To add a new
provider (a live Anthropic API call, a different model, ...) later,
write a new class here that implements `generate()` - nothing in
thumbnail_writer.py has to change.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system, prompt, max_tokens=4096):
        """Return the model's text response to `prompt`, guided by `system`."""
        raise NotImplementedError
