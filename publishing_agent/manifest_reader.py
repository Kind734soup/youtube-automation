"""Reads the files the Publishing Agent needs from a project's two
folders - the same folders every other agent in this pipeline already
writes to:

  scripts/<topic-slug>_<date>/   - metadata.json (required), plus
                                    edit_manifest.json and
                                    production_manifest.json (both
                                    optional - used to build chapters)
  final/<topic-slug>_<date>/     - final.mp4 and subtitles.srt
                                    (required, written by the FFmpeg
                                    Render Agent), plus thumbnail.png
                                    (optional - future input)

Pure parsing only, no AI and no manifest-building - see
metadata_builder.py for how these get turned into upload_manifest.json.
"""

import json
from pathlib import Path

FINAL_DIR_NAME = "final"


def project_root_for(scripts_folder):
    """The repository root - the parent of both scripts/ and final/."""
    return Path(scripts_folder).resolve().parent.parent


def final_folder_for(scripts_folder):
    """Mirrors ffmpeg_render_agent.renderer.output_folder_for: final.mp4
    lives under final/<same folder name as scripts_folder>, alongside
    research/ and scripts/ at the project root."""
    scripts_folder = Path(scripts_folder).resolve()
    return project_root_for(scripts_folder) / FINAL_DIR_NAME / scripts_folder.name


def load_metadata(scripts_folder):
    path = Path(scripts_folder) / "metadata.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Expected metadata.json in {scripts_folder}, but it was not found. "
            "Run the Script Agent first."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_edit_manifest(scripts_folder):
    """Optional - preferred source for chapters, since its start_time_seconds
    reflects the actual rendered timeline. Returns None if not present."""
    path = Path(scripts_folder) / "edit_manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_production_manifest(scripts_folder):
    """Optional - fallback source for chapters (scene titles plus
    estimated_duration_seconds) when edit_manifest.json isn't available.
    Returns None if not present."""
    path = Path(scripts_folder) / "production_manifest.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def locate_final_assets(final_folder, project_root):
    """Checks final.mp4 and subtitles.srt exist (required) and reports
    whether thumbnail.png exists (optional - future input, this agent
    only records its expected path today).

    Path fields are returned relative to `project_root` (POSIX-style,
    e.g. "final/<slug>_<date>/final.mp4") rather than as absolute
    filesystem paths - upload_manifest.json describes upload content,
    not a local machine layout, so it shouldn't embed this machine's
    absolute paths or username."""
    final_folder = Path(final_folder)
    project_root = Path(project_root)
    final_video_path = final_folder / "final.mp4"
    subtitles_path = final_folder / "subtitles.srt"
    thumbnail_path = final_folder / "thumbnail.png"

    if not final_video_path.exists():
        raise FileNotFoundError(
            f"Expected final.mp4 in {final_folder}, but it was not found. "
            "Run the FFmpeg Render Agent's `render` command first."
        )
    if not subtitles_path.exists():
        raise FileNotFoundError(
            f"Expected subtitles.srt in {final_folder}, but it was not found. "
            "Run the FFmpeg Render Agent's `render` command first."
        )

    def _relative(path):
        return path.resolve().relative_to(project_root).as_posix()

    return {
        "final_video_path": _relative(final_video_path),
        "subtitles_path": _relative(subtitles_path),
        "thumbnail_path": _relative(thumbnail_path),
        "thumbnail_exists": thumbnail_path.exists(),
    }
