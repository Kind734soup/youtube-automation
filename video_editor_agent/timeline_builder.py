"""Deterministic construction of an edit timeline from the Video Production
Agent's and Voice Generation Agent's manifests, plus the original script.

No AI and no FFmpeg here - this only combines four already-generated files
(production_manifest.json, narration_manifest.json, script.md, metadata.json)
into ordered timeline entries with computed timing, placeholder asset
filenames, transitions, default mix levels, fade timing, and captions.
The one thing this module does NOT fill in is music_cue / ambient_sound_cue
(deciding what a scene should sound like isn't something you can derive
mechanically from timing data) - manifest_builder.py adds those afterwards
with one LLM call per scene.
"""

import json
import re
from pathlib import Path

CAPTION_MAX_WORDS = 16  # keeps on-screen caption lines short and readable

DEFAULT_TRANSITION_TYPE = "crossfade"
DEFAULT_TRANSITION_SECONDS = 2.0
OPENING_FADE_SECONDS = 3.0  # fade in from black at the very start of the video
CLOSING_FADE_SECONDS = 6.0  # slower fade to black at the end, matching the wind-down ending

DEFAULT_VOLUME_LEVELS_DB = {"narration_db": 0, "music_db": -22, "ambient_db": -18}


def _parse_script_scenes(script_path):
    text = script_path.read_text(encoding="utf-8")
    header_pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(header_pattern.finditer(text))
    scenes = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        scenes.append({"title": m.group(1).strip(), "narration": text[start:end].strip()})
    return scenes


def _split_captions(narration_text, start_time, duration):
    """Break a scene's narration into short caption cues, spaced out evenly
    across the scene's duration by each cue's share of the total word count
    (a linear approximation - good enough for a placeholder timing plan)."""
    sentences = re.split(r"(?<=[.!?])\s+", narration_text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    captions = []
    current_words = []
    for sentence in sentences:
        words = sentence.split()
        if current_words and len(current_words) + len(words) > CAPTION_MAX_WORDS:
            captions.append(" ".join(current_words))
            current_words = words
        else:
            current_words.extend(words)
    if current_words:
        captions.append(" ".join(current_words))

    total_words = sum(len(c.split()) for c in captions) or 1
    cues = []
    cursor = start_time
    for caption in captions:
        share = len(caption.split()) / total_words
        cue_duration = duration * share
        cues.append(
            {
                "text": caption,
                "start_time_seconds": round(cursor, 1),
                "end_time_seconds": round(cursor + cue_duration, 1),
            }
        )
        cursor += cue_duration
    return cues


def build_timeline(folder):
    """Read production_manifest.json, narration_manifest.json, script.md,
    and metadata.json from `folder` (a Script Agent output folder that has
    also been through the Video Production Agent and Voice Generation
    Agent) and return (metadata, production_manifest, narration_manifest,
    timeline) - timeline is a list of dicts, one per video scene, with
    every edit_manifest.json field except music_cue/ambient_sound_cue."""
    folder = Path(folder)
    paths = {
        "production_manifest.json": folder / "production_manifest.json",
        "narration_manifest.json": folder / "narration_manifest.json",
        "script.md": folder / "script.md",
        "metadata.json": folder / "metadata.json",
    }
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Expected {name} in {folder}, but it was not found.")

    production_manifest = json.loads(paths["production_manifest.json"].read_text(encoding="utf-8"))
    narration_manifest = json.loads(paths["narration_manifest.json"].read_text(encoding="utf-8"))
    metadata = json.loads(paths["metadata.json"].read_text(encoding="utf-8"))
    script_scenes = _parse_script_scenes(paths["script.md"])

    production_scenes = production_manifest["scenes"]
    narration_sections = narration_manifest["sections"]

    if len(script_scenes) != len(production_scenes):
        raise ValueError(
            f"script.md has {len(script_scenes)} scenes but production_manifest.json has "
            f"{len(production_scenes)} - they must match up one-to-one."
        )

    # Group narration sections by scene title, preserving order of first appearance -
    # a scene can span more than one narration section (see section_parser.py in the
    # Voice Generation Agent), but never spans a different scene's sections.
    sections_by_title = {}
    for section in narration_sections:
        sections_by_title.setdefault(section["scene_title"], []).append(section)

    narration_by_title = {scene["title"]: scene["narration"] for scene in script_scenes}

    timeline = []
    cursor = 0.0
    for i, scene in enumerate(production_scenes):
        title = scene["title"]
        matching_sections = sections_by_title.get(title, [])
        if not matching_sections:
            raise ValueError(f'No narration_manifest.json sections found for scene "{title}"')

        duration = round(sum(s["estimated_duration_seconds"] for s in matching_sections), 1)
        start_time = round(cursor, 1)
        end_time = round(cursor + duration, 1)
        is_first = i == 0
        is_last = i == len(production_scenes) - 1

        timeline.append(
            {
                "timeline_index": i + 1,
                "scene_number": scene["scene_number"],
                "scene_title": title,
                "start_time_seconds": start_time,
                "end_time_seconds": end_time,
                "duration_seconds": duration,
                "narration_section_numbers": [s["section_number"] for s in matching_sections],
                "visual_asset_filename": f"scene_{scene['scene_number']:02d}.mp4",
                "audio_asset_filenames": [s["output_filename"] for s in matching_sections],
                "transition_in": (
                    {"type": "fade_from_black", "duration_seconds": OPENING_FADE_SECONDS}
                    if is_first
                    else {"type": DEFAULT_TRANSITION_TYPE, "duration_seconds": DEFAULT_TRANSITION_SECONDS}
                ),
                "transition_out": (
                    {"type": "fade_to_black", "duration_seconds": CLOSING_FADE_SECONDS}
                    if is_last
                    else {"type": DEFAULT_TRANSITION_TYPE, "duration_seconds": DEFAULT_TRANSITION_SECONDS}
                ),
                "volume_levels_db": dict(DEFAULT_VOLUME_LEVELS_DB),
                "music_cue": None,
                "ambient_sound_cue": None,
                "captions": _split_captions(narration_by_title.get(title, ""), start_time, duration),
            }
        )
        cursor = end_time

    return metadata, production_manifest, narration_manifest, timeline
