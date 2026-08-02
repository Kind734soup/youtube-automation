"""Reads the two files this agent consumes from a project folder:
production_manifest.json (the Video Production Agent's scene-by-scene
shot plan) and metadata.json (the Script Agent's topic/runtime summary,
already folded into production_manifest.json as "source_metadata" but
read directly too, since it's part of this agent's documented input
contract).

Pure parsing, no AI, no image generation - this module only knows how to
find and validate the two input files.
"""

import json
from pathlib import Path

REQUIRED_SCENE_FIELDS = ("scene_number", "title", "visual_prompt")


def _read_json(path, what):
    if not path.exists():
        raise FileNotFoundError(
            f"Expected {path.name} in {path.parent}, but it was not found. {what}"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_scenes(folder):
    """Return (scenes, metadata) for `folder`, a Script Agent output
    folder that has already been through the Video Production Agent.

    `scenes` is production_manifest.json's "scenes" list, validated to
    have at least scene_number/title/visual_prompt per entry - the only
    fields a VisualProvider needs. `metadata` is the parsed metadata.json.
    """
    folder = Path(folder)

    metadata = _read_json(
        folder / "metadata.json",
        "Run the Script Agent first.",
    )
    production_manifest = _read_json(
        folder / "production_manifest.json",
        "Run `python video_production_agent/main.py build --from-script <folder>` first.",
    )

    scenes = production_manifest.get("scenes", [])
    if not scenes:
        raise ValueError(f"production_manifest.json in {folder} has no scenes.")

    for scene in scenes:
        missing = [field for field in REQUIRED_SCENE_FIELDS if not scene.get(field) and scene.get(field) != 0]
        if missing:
            raise ValueError(
                f"Scene {scene.get('scene_number', '?')} in production_manifest.json is missing "
                f"required field(s): {missing}"
            )

    return scenes, metadata
