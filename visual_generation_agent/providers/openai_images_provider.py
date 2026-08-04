"""OpenAI Images (gpt-image-1) implementation of the VisualProvider interface.

Calls OpenAI's Images API once per scene, building the prompt from the
scene's already art-directed `visual_prompt` (plus lighting/mood/
environment context) straight out of production_manifest.json - no
change to any other file in this agent. The image OpenAI returns is
normalized to this project's standard 1920x1080 with ffmpeg (the same
resolution PlaceholderProvider produces), so every scene is a consistent
size in the final render no matter which provider generated it.
"""

import base64
import binascii
import os
from pathlib import Path

from visual_generation_agent.ffmpeg_utils import run_ffmpeg

from .base import VisualProvider

DEFAULT_MODEL = "gpt-image-1"
DEFAULT_SIZE = "1536x1024"  # closest gpt-image-1 landscape size to this project's 16:9 output
DEFAULT_QUALITY = "medium"
OUTPUT_RESOLUTION = "1920x1080"  # matches PlaceholderProvider.RESOLUTION

STYLE_SUFFIX = (
    " Cinematic painterly realism, soft and calming, dark ambient sleep-story mood. "
    "No text, no watermark, no logos, no visible human faces in close-up."
)


def _build_prompt(scene):
    parts = [scene["visual_prompt"]]
    if scene.get("lighting"):
        parts.append(f"Lighting: {scene['lighting']}.")
    if scene.get("mood"):
        parts.append(f"Mood: {scene['mood']}.")
    if scene.get("environment"):
        parts.append(f"Environment: {scene['environment']}.")
    return " ".join(parts) + STYLE_SUFFIX


class OpenAIImagesProvider(VisualProvider):
    def __init__(self):
        try:
            import openai  # noqa: F401 - import check only, client built below
        except ImportError:
            raise RuntimeError(
                "openai is not installed. Install it with:\n"
                "  .venv\\Scripts\\python.exe -m pip install openai"
            )
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not found. Make sure it's set in your .env file."
            )

        import openai as openai_module

        self._client = openai_module.OpenAI(api_key=api_key)
        # All overridable via .env so quality/cost can be tuned without touching code.
        self._model = os.environ.get("OPENAI_IMAGE_MODEL", DEFAULT_MODEL)
        self._size = os.environ.get("OPENAI_IMAGE_SIZE", DEFAULT_SIZE)
        self._quality = os.environ.get("OPENAI_IMAGE_QUALITY", DEFAULT_QUALITY)

    def generate_visual(self, scene, output_path):
        import openai

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Raw API image and the ffmpeg-normalized result each get their own tmp
        # path, and only the final normalized file is ever renamed into place -
        # a crash mid-generation must never leave a corrupt or wrong-resolution
        # file at output_path, matching PlaceholderProvider's approach.
        raw_path = output_path.with_name(output_path.stem + ".raw.tmp.png")
        tmp_path = output_path.with_name(output_path.stem + ".tmp" + output_path.suffix)

        prompt = _build_prompt(scene)

        try:
            response = self._client.images.generate(
                model=self._model,
                prompt=prompt,
                size=self._size,
                quality=self._quality,
                n=1,
            )
        except openai.AuthenticationError:
            raise RuntimeError(
                "OpenAI API key was rejected. Double-check OPENAI_API_KEY in .env."
            )
        except openai.RateLimitError:
            raise RuntimeError(
                "OpenAI API rate limit or quota hit. Wait a bit (or check billing) and try again."
            )
        except openai.BadRequestError as exc:
            raise RuntimeError(
                f"OpenAI rejected scene {scene['scene_number']}'s prompt (likely a content-policy "
                f"block). Try rephrasing visual_prompt in production_manifest.json. Details: {exc}"
            )

        b64_data = response.data[0].b64_json
        if not b64_data:
            raise RuntimeError(f"OpenAI returned no image data for scene {scene['scene_number']}.")

        try:
            image_bytes = base64.b64decode(b64_data)
        except binascii.Error as exc:
            raise RuntimeError(f"Could not decode OpenAI's image response: {exc}")

        raw_path.write_bytes(image_bytes)

        try:
            width, height = OUTPUT_RESOLUTION.split("x")
            run_ffmpeg(
                [
                    "-i", str(raw_path),
                    "-vf",
                    f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}",
                    "-frames:v", "1",
                    str(tmp_path),
                ]
            )
        finally:
            raw_path.unlink(missing_ok=True)

        tmp_path.replace(output_path)

        return {
            "provider": "openai_images",
            "model": self._model,
            "output_path": str(output_path),
            "resolution": OUTPUT_RESOLUTION,
            "requested_size": self._size,
        }
