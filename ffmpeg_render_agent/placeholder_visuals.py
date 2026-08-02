"""Generates a placeholder visual clip for a scene when no real video clip
exists yet.

The Video Production Agent doesn't have a video generation provider
connected (see video_production_agent/providers/), so there is no real
footage to render with today. Rather than block the whole pipeline on
that, this agent generates a simple, calm placeholder clip per scene - a
solid background with the scene title drawn on it - so the full assembly
pipeline (timing, transitions, subtitles, export) can be built and tested
now, and swapped for real clips later with zero changes elsewhere: once
a real file exists at the expected path, it's used automatically instead.
"""

from pathlib import Path

from ffmpeg_render_agent.ffmpeg_utils import escape_drawtext, run_ffmpeg

BACKGROUND_COLOR = "0x0d1b2a"  # calm dark indigo, matching the channel's night-time visual style
TEXT_COLOR = "0xe8c170"  # warm soft gold
FONT_PATH = r"C:\Windows\Fonts\arial.ttf"


def generate_placeholder_clip(text, duration_seconds, resolution, framerate_fps, output_path):
    """Render a solid-background clip with `text` centered on it, exactly
    `duration_seconds` long, at `resolution` (e.g. "1920x1080") and
    `framerate_fps`. Writes a silent video-only file to `output_path`.

    Written to a `.tmp` path first and only renamed into place on success,
    so a crash or timeout mid-render can never leave a corrupt file sitting
    at `output_path` for a later run to mistake for a finished placeholder
    (this happened once while building this agent - ffmpeg failed on a
    truncated leftover file from an interrupted run)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the real extension last (e.g. "scene_01.tmp.mp4") so ffmpeg can still
    # infer the output container/muxer from the filename - "scene_01.mp4.tmp"
    # confuses it ("Unable to choose an output format").
    tmp_path = output_path.with_name(output_path.stem + ".tmp" + output_path.suffix)

    escaped_text = escape_drawtext(text)
    escaped_font = str(FONT_PATH).replace("\\", "/").replace(":", "\\:")

    filter_str = (
        f"drawtext=fontfile='{escaped_font}':text='{escaped_text}':"
        f"fontcolor={TEXT_COLOR}:fontsize=42:x=(w-text_w)/2:y=(h-text_h)/2"
    )

    run_ffmpeg(
        [
            "-f", "lavfi",
            "-i", f"color=c={BACKGROUND_COLOR}:s={resolution}:d={duration_seconds}:r={framerate_fps}",
            "-vf", filter_str,
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            str(tmp_path),
        ]
    )
    tmp_path.replace(output_path)
    return output_path
