"""The contract every voice-synthesis provider will implement.

Nothing in this project calls a paid voice API yet. This class exists so
the shape of that integration is decided now, while the actual providers
(OpenAI TTS, ElevenLabs, ...) get plugged in later without touching the
manifest builder or any other part of this agent.

A future provider consumes one section dict from narration_manifest.json
(see manifest_builder.py for the exact fields) and is responsible for
turning it into a rendered audio file.
"""

from abc import ABC, abstractmethod


class VoiceProvider(ABC):
    @abstractmethod
    def synthesize_section(self, section, output_path):
        """Render a single manifest section to an audio file at output_path.

        `section` is one entry from narration_manifest.json's "sections"
        list. `output_path` is where the rendered audio should be written.
        Should return metadata about the render (e.g. provider job id,
        actual duration, file path) as a dict.
        """
        raise NotImplementedError
