"""Registry for voice-synthesis providers.

Empty on purpose - see README.md, "Adding a voice provider" for the plan.
No paid voice API is wired up yet; get_provider() exists so the rest of
the codebase (and future code) has one place to ask for a provider by
name, without needing to know whether it's OpenAI TTS, ElevenLabs, or
something else entirely.

To add a provider later:
  1. Write voice_generation_agent/providers/<name>_provider.py implementing
     VoiceProvider (see providers/base.py).
  2. Add one line to get_provider() below, e.g.:
       if name == "elevenlabs":
           from .elevenlabs_provider import ElevenLabsProvider
           return ElevenLabsProvider()
  3. Call it with the sections from narration_manifest.json.
No other file in this agent has to change.
"""

SUPPORTED_PROVIDERS = ()  # e.g. will become ("openai_tts", "elevenlabs")


def get_provider(name):
    raise NotImplementedError(
        f"No voice providers are connected yet (requested: '{name}'). "
        "This agent currently only produces narration_manifest.json. "
        "See README.md, 'Adding a voice provider', to wire one up."
    )
