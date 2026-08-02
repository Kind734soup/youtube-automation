"""Windows SAPI text-to-speech provider (via pyttsx3).

The free, offline, no-API-key voice provider used to test the real
pipeline before paying for a hosted TTS service (OpenAI TTS, ElevenLabs,
...). Uses whatever SAPI5 voices are already installed on this Windows
machine - see README.md, "Setup" for how to check/install voices and the
two packages this provider needs (pyttsx3, pywin32).

Implementation note: a new pyttsx3 engine is created for every single
section instead of reusing one engine across calls. This isn't a style
preference - reusing one engine's runAndWait() across repeated
save_to_file() calls is a well-known way to hang pyttsx3's SAPI5 driver
indefinitely (confirmed while building this provider: it hung on the very
first call of a reused-engine loop). A fresh engine per call is slower to
start up but reliable.
"""

import wave
from pathlib import Path

from .base import VoiceProvider

DEFAULT_RATE_WORDS_PER_MINUTE = 150  # slower than pyttsx3's default (~200) for a calmer pace


class WindowsSAPIProvider(VoiceProvider):
    def __init__(self, voice_id=None, rate=DEFAULT_RATE_WORDS_PER_MINUTE):
        try:
            import pyttsx3  # noqa: F401 - import check only, used per-call in synthesize_section
        except ImportError:
            raise RuntimeError(
                "pyttsx3 is not installed. Install it with:\n"
                "  .venv\\Scripts\\python.exe -m pip install pyttsx3 pywin32\n"
                "pywin32 provides the SAPI5 driver pyttsx3 needs on Windows."
            )
        self._voice_id = voice_id
        self._rate = rate

    def _new_engine(self):
        import pyttsx3

        try:
            engine = pyttsx3.init()
        except Exception as exc:
            raise RuntimeError(
                "Could not start the Windows SAPI voice engine. Make sure pywin32 is "
                f"installed and Windows Speech is available on this machine ({exc})."
            )
        engine.setProperty("rate", self._rate)
        if self._voice_id:
            engine.setProperty("voice", self._voice_id)
        return engine

    def synthesize_section(self, section, output_path_stem):
        output_path = Path(output_path_stem).with_suffix(".wav")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        engine = self._new_engine()
        engine.save_to_file(section["narration"], str(output_path))
        engine.runAndWait()
        del engine

        if not output_path.exists():
            raise RuntimeError(f"pyttsx3 did not produce an audio file at {output_path}")

        with wave.open(str(output_path), "rb") as wav_file:
            duration_seconds = round(wav_file.getnframes() / wav_file.getframerate(), 2)

        return {
            "provider": "windows_sapi",
            "output_path": str(output_path),
            "format": "wav",
            "duration_seconds": duration_seconds,
        }
