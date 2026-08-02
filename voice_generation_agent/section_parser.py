"""Parses script.md into narration sections small enough to hand to a
text-to-speech provider.

No AI, and no voice API, here - this module only reads script.md and
metadata.json and splits the narration into plain-text chunks. Anything
that requires judgment (tone, pace, pauses, pronunciation) happens later
in manifest_builder.py.

Sections are built one scene at a time (splitting on script.md's "## "
headers). A scene's narration becomes its own section as long as it fits
under MAX_CHARS_PER_SECTION; longer scenes are split further on paragraph
boundaries so no single request to a TTS provider gets too large (OpenAI's
TTS endpoint caps input at 4096 characters, and providers like ElevenLabs
recommend shorter chunks for more consistent, less drifting prosody).
"""

import json
import re
from pathlib import Path

MAX_CHARS_PER_SECTION = 3000


def _parse_scenes(script_path):
    text = script_path.read_text(encoding="utf-8")
    header_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(header_pattern.finditer(text))

    scenes = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        scenes.append({"title": m.group(1).strip(), "narration": text[start:end].strip()})
    return scenes


def _chunk_scene(narration, max_chars):
    """Greedily group a scene's paragraphs into chunks no larger than
    max_chars (a single paragraph longer than max_chars becomes its own
    oversized chunk rather than being cut mid-sentence)."""
    paragraphs = [p.strip() for p in narration.split("\n\n") if p.strip()]

    chunks = []
    current = []
    current_len = 0
    for paragraph in paragraphs:
        added_len = len(paragraph) + (2 if current else 0)
        if current and current_len + added_len > max_chars:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = len(paragraph)
        else:
            current.append(paragraph)
            current_len += added_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def load_source_files(folder):
    """Read script.md and metadata.json from `folder` (a Script Agent
    output folder, e.g. scripts/<topic-slug>_<date>) and return
    (metadata, sections), where sections is a list of dicts with:
      section_number, scene_title, narration
    """
    folder = Path(folder)
    script_path = folder / "script.md"
    metadata_path = folder / "metadata.json"

    for path in (script_path, metadata_path):
        if not path.exists():
            raise FileNotFoundError(f"Expected {path.name} in {folder}, but it was not found.")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    scenes = _parse_scenes(script_path)

    sections = []
    for scene in scenes:
        for chunk in _chunk_scene(scene["narration"], MAX_CHARS_PER_SECTION):
            sections.append({"scene_title": scene["title"], "narration": chunk})

    for i, section in enumerate(sections, start=1):
        section["section_number"] = i

    return metadata, sections
