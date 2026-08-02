"""The contract every voice-synthesis provider implements.

A provider consumes one section dict from narration_manifest.json (see
manifest_builder.py for the exact fields) and is responsible for turning
it into a rendered audio file. `windows_sapi_provider.py` is the first
implementation (free, offline, no API key); OpenAI TTS, ElevenLabs, or
others can be added later behind the same interface.
"""

from abc import ABC, abstractmethod


class VoiceProvider(ABC):
    @abstractmethod
    def synthesize_section(self, section, output_path_stem):
        """Render a single manifest section to an audio file.

        `section` is one entry from narration_manifest.json's "sections"
        list. `output_path_stem` is a Path with the desired filename but
        no extension (e.g. .../assets/audio/section_01) - the provider
        appends whatever extension its own output format actually is
        (.wav, .mp3, ...), since that's a property of the provider, not
        something the caller can know in advance.

        Must return a dict describing the render, at minimum:
          {"provider": ..., "output_path": ..., "format": ..., "duration_seconds": ...}
        """
        raise NotImplementedError
