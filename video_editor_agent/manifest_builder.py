"""Turns a Script Agent + Video Production Agent + Voice Generation Agent
output folder into an edit_manifest.json - the assembly plan the eventual
FFmpeg step (see ffmpeg_assembler.py) will read.

timeline_builder.py handles everything that can be computed directly from
the existing manifests (timing, matching narration, placeholder asset
filenames, transitions, volume levels, fades, captions). The one thing
that isn't already captured anywhere upstream is what a scene should sound
like underneath the narration - a music bed and an ambient sound cue - so
each scene is passed through an LLM once for that, using the scene's own
environment/mood/visual prompt (already written by the Video Production
Agent) as context.

No video, audio, or FFmpeg work happens here - this only produces the
manifest.
"""

import json
import re

from video_editor_agent.llm_client import generate
from video_editor_agent.timeline_builder import build_timeline

FINAL_ASPECT_RATIO_FALLBACK = "16:9"
FINAL_RESOLUTION_BY_ASPECT_RATIO = {
    "16:9": "1920x1080",
    "9:16": "1080x1920",
    "21:9": "2560x1080",
    "1:1": "1080x1080",
}
FRAMERATE_FPS = 24

SYSTEM_PROMPT = (
    "You are the sound-design step of a Video Editor Agent for the Nightfall Atlas YouTube "
    "channel, a premium sleep storytelling channel. Given a scene's environment, mood, and "
    "visual description, you choose a music bed and an ambient sound cue to sit quietly "
    "underneath the narration. Everything must stay calm, slow, and unobtrusive - never "
    "energetic, rhythmic, or attention-grabbing. Be concrete and concise; these fields feed "
    "a JSON manifest for a human sound editor or an automated mixing step, not a listener."
)


def _parse_json_object(text):
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _sound_design_for_scene(topic, scene):
    prompt = (
        f"Story topic: {topic}\n\n"
        f'Scene: "{scene["title"]}"\n'
        f"Environment: {scene.get('environment', '')}\n"
        f"Mood: {scene.get('mood', '')}\n"
        f"Visual prompt: {scene.get('visual_prompt', '')}\n\n"
        "Respond with ONLY a JSON object, no other text, in this exact shape:\n"
        "{\n"
        '  "music_cue": "a short description of the music bed for this scene, e.g. '
        '\\"sparse, slow solo harp, no percussion\\" - or \\"None\\" if the scene should '
        'have no music",\n'
        '  "ambient_sound_cue": "a short description of the ambient/foley sound bed, e.g. '
        '\\"gentle river water and distant crickets\\" - or \\"None\\" if silence is best"\n'
        "}"
    )
    raw = generate(SYSTEM_PROMPT, prompt, max_tokens=300)
    return _parse_json_object(raw)


def build_manifest(folder):
    """Read a Script Agent + Video Production Agent + Voice Generation Agent
    output folder and return an edit manifest dict. Does not write anything
    to disk - see organizer.save_manifest() for that."""
    metadata, production_manifest, narration_manifest, timeline = build_timeline(folder)
    production_scenes = production_manifest["scenes"]

    for entry, scene in zip(timeline, production_scenes):
        sound = _sound_design_for_scene(metadata["topic"], scene)
        entry["music_cue"] = sound.get("music_cue", "None")
        entry["ambient_sound_cue"] = sound.get("ambient_sound_cue", "None")

    aspect_ratios = [s.get("recommended_aspect_ratio", FINAL_ASPECT_RATIO_FALLBACK) for s in production_scenes]
    final_aspect_ratio = (
        max(set(aspect_ratios), key=aspect_ratios.count) if aspect_ratios else FINAL_ASPECT_RATIO_FALLBACK
    )
    final_resolution = FINAL_RESOLUTION_BY_ASPECT_RATIO.get(final_aspect_ratio, "1920x1080")

    total_duration = round(sum(e["duration_seconds"] for e in timeline), 1)

    return {
        "topic": metadata["topic"],
        "source_metadata": metadata,
        "scene_count": len(timeline),
        "total_duration_seconds": total_duration,
        "final_resolution": final_resolution,
        "final_aspect_ratio": final_aspect_ratio,
        "framerate_fps": FRAMERATE_FPS,
        "export_settings": {
            "container": "mp4",
            "video_codec": "libx264",
            "audio_codec": "aac",
            "video_bitrate": "8M",
            "audio_bitrate": "192k",
            "framerate_fps": FRAMERATE_FPS,
            "resolution": final_resolution,
            "aspect_ratio": final_aspect_ratio,
            "pixel_format": "yuv420p",
        },
        "timeline": timeline,
    }
