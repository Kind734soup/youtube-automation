"""Parses the Script Agent's output files into a list of per-scene dicts.

No AI calls here - this module only reads script.md, scene_descriptions.md,
and metadata.json and turns them into plain data. Anything that requires
judgment (camera movement, lighting, continuity, etc.) happens later in
manifest_builder.py.
"""

import json
import re
from pathlib import Path


def _split_on_headers(text, header_pattern):
    """Split markdown text on lines matching header_pattern (a compiled regex
    with MULTILINE). Returns a list of (header_match, body_text)."""
    matches = list(header_pattern.finditer(text))
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append((m, text[start:end].strip()))
    return sections


def _parse_script(script_path):
    text = script_path.read_text(encoding="utf-8")
    header_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    scenes = []
    for m, body in _split_on_headers(text, header_pattern):
        scenes.append({"title": m.group(1).strip(), "narration": body.strip()})
    return scenes


def _parse_scene_descriptions(descriptions_path):
    text = descriptions_path.read_text(encoding="utf-8")
    header_pattern = re.compile(r"^## Scene \d+:\s*(.+)$", re.MULTILINE)
    descriptions = []
    for m, body in _split_on_headers(text, header_pattern):
        descriptions.append({"title": m.group(1).strip(), "visual_description": body.strip()})
    return descriptions


def load_source_files(folder):
    """Read script.md, scene_descriptions.md and metadata.json from `folder`
    (a Script Agent output folder, e.g. scripts/<topic-slug>_<date>) and
    return (metadata, scenes), where scenes is a list of dicts with:
      scene_number, title, narration, visual_description
    """
    folder = Path(folder)
    script_path = folder / "script.md"
    descriptions_path = folder / "scene_descriptions.md"
    metadata_path = folder / "metadata.json"

    for path in (script_path, descriptions_path, metadata_path):
        if not path.exists():
            raise FileNotFoundError(f"Expected {path.name} in {folder}, but it was not found.")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    narrations = _parse_script(script_path)
    visuals = _parse_scene_descriptions(descriptions_path)

    if len(narrations) != len(visuals):
        raise ValueError(
            f"script.md has {len(narrations)} scenes but scene_descriptions.md has "
            f"{len(visuals)} scenes - they must match up one-to-one."
        )

    scenes = []
    for i, (narration_scene, visual_scene) in enumerate(zip(narrations, visuals), start=1):
        scenes.append(
            {
                "scene_number": i,
                "title": narration_scene["title"],
                "narration": narration_scene["narration"],
                "visual_description": visual_scene["visual_description"],
            }
        )
    return metadata, scenes
