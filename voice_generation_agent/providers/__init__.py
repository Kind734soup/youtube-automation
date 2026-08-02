"""Registry for voice-synthesis providers.

get_provider() exists so the rest of the codebase has one place to ask
for a provider by name, without needing to know whether it's the local
Windows SAPI engine, OpenAI TTS, ElevenLabs, or something else entirely.

`windows_sapi` is the only provider connected so far - a free, offline,
no-API-key option (see windows_sapi_provider.py) used to test the real
pipeline before paying for a hosted TTS service.

To add a paid/hosted provider later:
  1. Write voice_generation_agent/providers/<name>_provider.py implementing
     VoiceProvider (see providers/base.py).
  2. Add one line to get_provider() below, e.g.:
       if name == "elevenlabs":
           from .elevenlabs_provider import ElevenLabsProvider
           return ElevenLabsProvider()
  3. Call it with the sections from narration_manifest.json.
No other file in this agent has to change.
"""

SUPPORTED_PROVIDERS = ("windows_sapi",)  # e.g. will grow to ("windows_sapi", "openai_tts", "elevenlabs")


def get_provider(name):
    if name == "windows_sapi":
        from .windows_sapi_provider import WindowsSAPIProvider

        return WindowsSAPIProvider()

    raise NotImplementedError(
        f"No voice provider named '{name}' is available. Supported: {SUPPORTED_PROVIDERS}. "
        "See README.md, 'Adding a voice provider', to wire up another one."
    )
