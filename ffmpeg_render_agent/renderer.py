"""Top-level orchestration: reads edit_manifest.json and produces
final.mp4, subtitles.srt, and render_report.md for a project folder.

Everything else in this agent is a building block called from here (and
from main.py, which just wraps this as a CLI) - no other module should
need to be called directly.
"""

import json
import shutil
import tempfile
from pathlib import Path

from ffmpeg_render_agent.ffmpeg_utils import ffmpeg_path
from ffmpeg_render_agent.render_report import build_report
from ffmpeg_render_agent.scene_renderer import prepare_scene_clip
from ffmpeg_render_agent.subtitles import build_srt, burn_subtitles, save_srt
from ffmpeg_render_agent.timeline_render import assemble_timeline

FINAL_DIR_NAME = "final"


def _load_edit_manifest(folder):
    manifest_path = Path(folder) / "edit_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Expected edit_manifest.json in {folder}, but it was not found. "
            "Run the Video Editor Agent's `build` command first."
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def output_folder_for(folder):
    """final.mp4/subtitles.srt/render_report.md go under final/<same folder
    name as the source project>, alongside research/ and scripts/ at the
    project root."""
    folder = Path(folder).resolve()
    project_root = folder.parent.parent
    return project_root / FINAL_DIR_NAME / folder.name


def render_video(folder, burn_subtitles_flag=False, force=False):
    """Render edit_manifest.json from `folder` into final.mp4,
    subtitles.srt, and render_report.md under final/<folder-name>/.
    Returns a result dict for the CLI to report."""
    folder = Path(folder)
    manifest = _load_edit_manifest(folder)
    timeline = manifest["timeline"]

    output_dir = output_folder_for(folder)
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / "final.mp4"
    srt_path = output_dir / "subtitles.srt"
    report_path = output_dir / "render_report.md"

    if final_path.exists() and not force:
        return {
            "skipped": True,
            "final_path": final_path,
            "srt_path": srt_path,
            "report_path": report_path,
        }

    ffmpeg_path()  # fail fast with a clear, actionable error if ffmpeg isn't on PATH

    work_dir = Path(tempfile.mkdtemp(prefix="ffmpeg_render_agent_"))
    try:
        clip_paths = []
        scene_infos = []
        for i, entry in enumerate(timeline):
            clip_path, info = prepare_scene_clip(
                entry, folder, manifest["final_resolution"], manifest["framerate_fps"], work_dir, i, force=force
            )
            clip_paths.append(clip_path)
            scene_infos.append(info)

        assembled_path = work_dir / "assembled.mp4"
        assemble_timeline(clip_paths, timeline, manifest["export_settings"], assembled_path)

        effective_durations = [info["effective_duration_seconds"] for info in scene_infos]
        srt_content = build_srt(timeline, effective_durations)
        save_srt(srt_content, srt_path)

        if burn_subtitles_flag:
            burn_subtitles(assembled_path, srt_path, manifest["export_settings"], final_path)
        else:
            shutil.copyfile(assembled_path, final_path)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    report_path.write_text(
        build_report(manifest, scene_infos, final_path, srt_path, burn_subtitles_flag), encoding="utf-8"
    )

    return {
        "skipped": False,
        "final_path": final_path,
        "srt_path": srt_path,
        "report_path": report_path,
        "scene_infos": scene_infos,
    }
