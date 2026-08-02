"""Runs a connected VoiceProvider against narration_manifest.json to
render real audio files.

Kept separate from manifest_builder.py on purpose: building the manifest
only ever needs an LLM (for voice direction), never a voice provider;
rendering audio only ever needs a voice provider, never an LLM. This is
the only module in the agent that imports from providers/.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from voice_generation_agent.providers import get_provider

load_dotenv()

AUDIO_SUBDIR = Path("assets") / "audio"


def default_provider_name():
    return os.environ.get("VOICE_PROVIDER", "windows_sapi").lower()


def load_narration_manifest(folder):
    manifest_path = Path(folder) / "narration_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Expected narration_manifest.json in {folder}, but it was not found. "
            "Run `python -m voice_generation_agent.main build --from-script <folder>` first."
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def narrate_sections(folder, sections, provider_name=None):
    """Render `sections` (entries from narration_manifest.json's "sections"
    list) to real audio files under <folder>/assets/audio/, using the
    named voice provider (defaults to VOICE_PROVIDER in .env, or
    "windows_sapi" if unset). Returns the list of result dicts each
    provider's synthesize_section() returns, one per section."""
    folder = Path(folder)
    audio_dir = folder / AUDIO_SUBDIR
    audio_dir.mkdir(parents=True, exist_ok=True)

    provider = get_provider(provider_name or default_provider_name())

    results = []
    for section in sections:
        # The manifest's output_filename is a provider-agnostic placeholder (e.g. "section_01.mp3");
        # keep its numbering, but let the provider decide the real extension it actually produces.
        stem = Path(section["output_filename"]).stem
        result = provider.synthesize_section(section, audio_dir / stem)
        results.append(result)
    return results
