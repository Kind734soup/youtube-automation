"""Runs a connected VisualProvider against production_manifest.json to
generate one still image per scene, and (optionally) publishes those
images to the exact path the FFmpeg Render Agent already reads real
visual assets from.

Kept separate from manifest_reader.py on purpose, the same way the Voice
Generation Agent splits manifest-building from audio-rendering: reading
the manifest never needs a provider; generating images always does.
"""

import os
import shutil
from pathlib import Path

from dotenv import load_dotenv

from visual_generation_agent.manifest_reader import load_scenes
from visual_generation_agent.providers import get_provider

load_dotenv()

VISUALS_SUBDIR = Path("assets") / "visuals"

# Not this agent's own output folder - this is the FFmpeg Render Agent's
# pre-existing, documented hand-off path for real visual clips (see
# ffmpeg_render_agent/README.md, "Placeholder visuals"). Publishing here
# is opt-in (`--publish`) and is the only place this agent reaches
# outside its own assets/visuals/ folder.
VIDEO_SUBDIR = Path("assets") / "video"
BACKUP_SUBDIR_NAME = "_pre_visual_generation_agent"


def default_provider_name():
    return os.environ.get("VISUAL_PROVIDER", "placeholder").lower()


def _publish_to_video_assets(folder, stem, source_path):
    """Copy `source_path` into <folder>/assets/video/<stem>.png - the
    exact stem the FFmpeg Render Agent's own `_find_existing` glob
    already looks for. Any pre-existing file(s) for this stem (e.g. a
    previously generated fallback title-card .mp4) are moved aside into
    assets/video/_pre_visual_generation_agent/ rather than deleted, so
    nothing is silently lost - and moved into a subdirectory, which the
    render agent's own non-recursive glob never looks inside, so it
    can't accidentally get picked up instead of the real image."""
    video_dir = folder / VIDEO_SUBDIR
    video_dir.mkdir(parents=True, exist_ok=True)
    backup_dir = video_dir / BACKUP_SUBDIR_NAME

    target_path = video_dir / f"{stem}.png"
    for existing in sorted(video_dir.glob(f"{stem}.*")):
        if existing == target_path:
            continue
        backup_dir.mkdir(parents=True, exist_ok=True)
        existing.replace(backup_dir / existing.name)

    shutil.copyfile(source_path, target_path)
    return target_path


def generate_scene_visuals(folder, provider_name=None, force=False, publish=False):
    """Generate <folder>/assets/visuals/scene_NN.png for every scene in
    production_manifest.json, using the named visual provider (defaults
    to VISUAL_PROVIDER in .env, or "placeholder" if unset).

    If a scene's image already exists, it is left alone and reported as
    skipped rather than regenerated - pass force=True to regenerate it
    anyway. If publish=True, each image is also copied to
    assets/video/scene_NN.png (see _publish_to_video_assets).

    Returns one result dict per scene, each with at least
    {"scene_number", "title", "output_path", "skipped"}."""
    folder = Path(folder)
    scenes, _metadata = load_scenes(folder)

    visuals_dir = folder / VISUALS_SUBDIR
    visuals_dir.mkdir(parents=True, exist_ok=True)

    provider = get_provider(provider_name or default_provider_name())

    results = []
    for scene in scenes:
        stem = f"scene_{scene['scene_number']:02d}"
        output_path = visuals_dir / f"{stem}.png"

        if output_path.exists() and not force:
            result = {
                "scene_number": scene["scene_number"],
                "title": scene["title"],
                "output_path": str(output_path),
                "skipped": True,
            }
        else:
            info = provider.generate_visual(scene, output_path)
            result = {
                "scene_number": scene["scene_number"],
                "title": scene["title"],
                "skipped": False,
                **info,
            }

        if publish:
            result["published_path"] = str(_publish_to_video_assets(folder, stem, output_path))

        results.append(result)

    return results
