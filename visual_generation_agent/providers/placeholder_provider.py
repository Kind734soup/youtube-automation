"""Free, offline visual provider - no image/video API required.

Draws each scene's number, title, and visual_prompt onto a single
1920x1080 still image with ffmpeg's drawtext filter, in the same dark
cinematic palette the FFmpeg Render Agent's own placeholder video clips
use (see ffmpeg_render_agent/placeholder_visuals.py - not imported here,
just matched by eye) - so the channel's Nightfall Atlas look stays
consistent whether a scene is using this placeholder or a real
generated image later.

This is the only provider wired up in providers/__init__.py today. Real
image/video providers (OpenAI Images, FLUX, SDXL, Runway, Veo, Kling,
Pika) are future work - see providers/base.py and README.md.
"""

import textwrap
from pathlib import Path

from visual_generation_agent.ffmpeg_utils import escape_drawtext, run_ffmpeg

from .base import VisualProvider

RESOLUTION = "1920x1080"
BACKGROUND_COLOR = "0x0d1b2a"  # calm dark indigo - matches the channel's other placeholder visuals
NUMBER_COLOR = "0x8fa3bf"  # muted slate blue
TITLE_COLOR = "0xe8c170"  # warm soft gold
PROMPT_COLOR = "0xc9d3e0"  # soft pale blue-grey
FONT_PATH = r"C:\Windows\Fonts\arial.ttf"
PROMPT_WRAP_WIDTH = 62
PROMPT_MAX_LINES = 8


def _wrapped_prompt(text):
    lines = textwrap.wrap(text, width=PROMPT_WRAP_WIDTH)
    if len(lines) > PROMPT_MAX_LINES:
        lines = lines[:PROMPT_MAX_LINES]
        lines[-1] = lines[-1].rstrip() + " ..."
    return "\n".join(lines)


def _escaped_font_path():
    return str(FONT_PATH).replace("\\", "/").replace(":", "\\:")


class PlaceholderProvider(VisualProvider):
    def generate_visual(self, scene, output_path):
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Written to a `.tmp` path first and only renamed into place on success,
        # matching ffmpeg_render_agent/placeholder_visuals.py's approach - a
        # crash mid-render must never leave a corrupt file at output_path for
        # a later run (or the FFmpeg Render Agent) to mistake for a real one.
        tmp_path = output_path.with_name(output_path.stem + ".tmp" + output_path.suffix)

        number_text = escape_drawtext(f"SCENE {scene['scene_number']:02d}")
        title_text = escape_drawtext(scene["title"])
        prompt_text = escape_drawtext(_wrapped_prompt(scene["visual_prompt"]))
        font = _escaped_font_path()

        filter_str = (
            f"vignette=PI/5,"
            f"drawtext=fontfile='{font}':text='{number_text}':"
            f"fontcolor={NUMBER_COLOR}:fontsize=34:x=(w-text_w)/2:y=180,"
            f"drawtext=fontfile='{font}':text='{title_text}':"
            f"fontcolor={TITLE_COLOR}:fontsize=64:x=(w-text_w)/2:y=250,"
            f"drawbox=x=(w-640)/2:y=370:w=640:h=2:color={TITLE_COLOR}@0.5,"
            f"drawtext=fontfile='{font}':text='{prompt_text}':"
            f"fontcolor={PROMPT_COLOR}:fontsize=30:line_spacing=14:text_align=C:"
            f"x=(w-text_w)/2:y=440"
        )

        run_ffmpeg(
            [
                "-f", "lavfi",
                "-i", f"color=c={BACKGROUND_COLOR}:s={RESOLUTION}:d=1:r=1",
                "-vf", filter_str,
                "-frames:v", "1",
                "-update", "1",
                str(tmp_path),
            ]
        )
        tmp_path.replace(output_path)

        return {
            "provider": "placeholder",
            "output_path": str(output_path),
            "resolution": RESOLUTION,
        }
