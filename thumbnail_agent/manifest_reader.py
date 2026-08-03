"""Reads the files this agent consumes from a Script Agent output folder
(scripts/<topic-slug>_<date>/):

  metadata.json               - required - topic/runtime summary
  script.md                   - required - full narration, used here only
                                 for its opening excerpt (mood/setting)
  production_manifest.json    - required - scene-by-scene titles and
                                 visual_prompts (the Video Production
                                 Agent's shot plan)
  assets/visuals/*.png        - optional - existing scene reference
                                 images from the Visual Generation Agent,
                                 named only, never opened as image data

Pure parsing only, no AI - see thumbnail_writer.py for turning these
inputs into thumbnail concepts.
"""

import json
import re
from pathlib import Path

VISUALS_SUBDIR = Path("assets") / "visuals"
SCRIPT_EXCERPT_MAX_CHARS = 1200


def _read_json(path, what):
    if not path.exists():
        raise FileNotFoundError(f"Expected {path.name} in {path.parent}, but it was not found. {what}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_metadata(folder):
    return _read_json(Path(folder) / "metadata.json", "Run the Script Agent first.")


def load_script_excerpt(folder):
    """Returns the opening of script.md (stripped of markdown headings),
    trimmed to SCRIPT_EXCERPT_MAX_CHARS - enough to convey the story's
    opening mood and setting without sending the entire (multi-thousand
    word) script through an LLM prompt."""
    path = Path(folder) / "script.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Expected script.md in {folder}, but it was not found. Run the Script Agent first."
        )
    text = path.read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if not line.startswith("#") and not line.startswith("_")]
    body = "\n".join(lines).strip()
    body = re.sub(r"\n{2,}", "\n\n", body)
    if len(body) > SCRIPT_EXCERPT_MAX_CHARS:
        body = body[:SCRIPT_EXCERPT_MAX_CHARS].rsplit(" ", 1)[0].rstrip() + "..."
    return body


def load_scenes(folder):
    manifest = _read_json(
        Path(folder) / "production_manifest.json",
        "Run `python video_production_agent/main.py build --from-script <folder>` first.",
    )
    scenes = manifest.get("scenes", [])
    if not scenes:
        raise ValueError(f"production_manifest.json in {folder} has no scenes.")
    return scenes


def list_existing_scene_images(folder):
    """Optional - filenames only (never opened as image data), listed so
    the concept-writing prompt can ask for visual consistency with
    scenes that already have a generated reference image."""
    visuals_dir = Path(folder) / VISUALS_SUBDIR
    if not visuals_dir.exists():
        return []
    return sorted(p.name for p in visuals_dir.glob("scene_*.png"))


def load_project_inputs(folder):
    """Convenience wrapper bundling everything thumbnail_writer.py needs
    from one Script Agent output folder."""
    folder = Path(folder)
    return {
        "metadata": load_metadata(folder),
        "script_excerpt": load_script_excerpt(folder),
        "scenes": load_scenes(folder),
        "existing_scene_images": list_existing_scene_images(folder),
    }
