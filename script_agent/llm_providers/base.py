"""The contract every AI provider must implement.

script_writer.py only ever talks to this interface. To add a new provider
(OpenAI, Gemini, a local model...) later, write a new class here that
implements `generate()` - nothing in script_writer.py has to change.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system, prompt, max_tokens=4096):
        """Return the model's text response to `prompt`, guided by `system`."""
        raise NotImplementedError
