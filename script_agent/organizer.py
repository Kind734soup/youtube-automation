"""Saves generated scripts into organized folders under scripts/.

Layout:
  scripts/
    <topic-slug>_<date>/
      script.md               <- full narration, ready to record from
      scene_descriptions.md   <- visual prompts for the Video Production Agent
      metadata.json           <- word count, target/estimated runtime

Separate from the Research Agent's research/ folder on purpose - these
are two independent agents that happen to live in the same project.
"""

import json
import re
from datetime import date
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


def _slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def save_script(result):
    """Save a write_script() result. Returns the folder path it was saved to."""
    folder = SCRIPTS_DIR / f"{_slugify(result['topic'])}_{date.today()}"
    folder.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# {result['topic']}",
        f"_Nightfall Atlas script - generated {date.today()}_",
        f"_Target: {result['target_minutes']} min | Estimated: {result['estimated_minutes']} min "
        f"| {result['word_count']} words_",
        "",
    ]
    for scene in result["scenes"]:
        lines.append(f"## {scene['title']}")
        lines.append("")
        lines.append(scene["narration"])
        lines.append("")
    (folder / "script.md").write_text("\n".join(lines), encoding="utf-8")

    visual_lines = [
        f"# Scene Visual Descriptions: {result['topic']}",
        "_For the Video Production Agent_",
        "",
    ]
    for i, scene in enumerate(result["scenes"], start=1):
        visual_lines.append(f"## Scene {i}: {scene['title']}")
        visual_lines.append(scene["visual_description"])
        visual_lines.append("")
    (folder / "scene_descriptions.md").write_text("\n".join(visual_lines), encoding="utf-8")

    metadata = {
        "topic": result["topic"],
        "generated": str(date.today()),
        "target_minutes": result["target_minutes"],
        "estimated_minutes": result["estimated_minutes"],
        "word_count": result["word_count"],
        "scene_count": len(result["scenes"]),
    }
    (folder / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return folder
