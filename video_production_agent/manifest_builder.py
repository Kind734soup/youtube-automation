"""Turns a Script Agent output folder into a production_manifest.json.

script.md and scene_descriptions.md give us narration and a rough,
free-form visual description per scene, but that description mixes
setting, lighting, camera framing and mood into one paragraph of prose.
Video providers need those pulled apart into distinct fields, so each
scene is passed through an LLM once to structure it into the shape any
future video provider (Veo, Runway, Kling, Pika, ...) can consume the
same way. No video API is called here - this only produces the manifest.
"""

import json
import re

from video_production_agent.llm_client import generate
from video_production_agent.scene_parser import load_source_files

WORDS_PER_MINUTE_FALLBACK = 135  # only used if metadata.json is missing word/runtime data
DEFAULT_ASPECT_RATIO = "16:9"  # standard for long-form YouTube; the LLM may override per scene

SYSTEM_PROMPT = (
    "You are the shot-planning step of a Video Production Agent for the Nightfall Atlas "
    "YouTube channel. You take a scene's narration and a rough visual description and turn "
    "them into a concrete, structured shot plan for AI video generation tools (for example "
    "Google Veo, Runway, Kling, or Pika). Be concrete and specific, not poetic - these fields "
    "feed a JSON manifest that a video model or a human storyboard artist will read, not a "
    "viewer. Keep the calm, slow, non-jarring tone of the channel in mind: prefer slow camera "
    "moves, avoid anything frantic or jump-cut."
)


def _parse_json_object(text):
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _structure_scene(topic, scene, previous_scene, next_scene):
    context_lines = [f"Story topic: {topic}"]
    if previous_scene:
        context_lines.append(
            f'Previous scene ("{previous_scene["title"]}") visual description: '
            f'{previous_scene["visual_description"]}'
        )
    if next_scene:
        context_lines.append(
            f'Next scene ("{next_scene["title"]}") visual description: '
            f'{next_scene["visual_description"]}'
        )
    context = "\n".join(context_lines)

    prompt = (
        f"{context}\n\n"
        f'Current scene {scene["scene_number"]}, "{scene["title"]}"\n\n'
        f"Narration for this scene:\n{scene['narration']}\n\n"
        f"Rough visual description for this scene:\n{scene['visual_description']}\n\n"
        "Respond with ONLY a JSON object, no other text, in this exact shape:\n"
        "{\n"
        '  "visual_prompt": "a concrete, self-contained prompt describing this scene for a '
        'video generation model - setting, subject, action, style",\n'
        '  "camera_movement": "e.g. slow forward drift, static wide shot, slow aerial descent",\n'
        '  "lighting": "e.g. warm lantern glow against deep blue night",\n'
        '  "environment": "the physical setting/location",\n'
        '  "characters": ["list of any characters or figures present, empty array if none"],\n'
        '  "mood": "the emotional tone of the shot",\n'
        '  "continuity_notes": "how this scene should visually connect to the scene before and '
        'after it - recurring colors, objects, framing, or figures to keep consistent",\n'
        '  "recommended_aspect_ratio": "e.g. 16:9",\n'
        '  "recommended_shot_type": "e.g. wide establishing shot, slow aerial, medium tracking shot"\n'
        "}\n\n"
        f'Default recommended_aspect_ratio to "{DEFAULT_ASPECT_RATIO}" unless this specific shot '
        "has a strong cinematic reason to differ."
    )
    raw = generate(SYSTEM_PROMPT, prompt, max_tokens=800)
    return _parse_json_object(raw)


def _scene_durations_seconds(scenes, metadata):
    word_counts = [len(scene["narration"].split()) for scene in scenes]
    total_words = sum(word_counts)

    total_seconds = metadata.get("estimated_minutes", 0) * 60
    if not total_seconds:
        total_seconds = total_words / WORDS_PER_MINUTE_FALLBACK * 60

    if total_words == 0:
        return [0 for _ in scenes]
    return [round(total_seconds * count / total_words, 1) for count in word_counts]


def build_manifest(folder):
    """Read a Script Agent output folder and return a production manifest dict.
    Does not write anything to disk - see organizer.save_manifest() for that."""
    metadata, scenes = load_source_files(folder)
    durations = _scene_durations_seconds(scenes, metadata)

    manifest_scenes = []
    for i, scene in enumerate(scenes):
        previous_scene = scenes[i - 1] if i > 0 else None
        next_scene = scenes[i + 1] if i + 1 < len(scenes) else None
        structured = _structure_scene(metadata["topic"], scene, previous_scene, next_scene)

        manifest_scenes.append(
            {
                "scene_number": scene["scene_number"],
                "title": scene["title"],
                "narration": scene["narration"],
                "visual_prompt": structured.get("visual_prompt", scene["visual_description"]),
                "camera_movement": structured.get("camera_movement", ""),
                "lighting": structured.get("lighting", ""),
                "environment": structured.get("environment", ""),
                "characters": structured.get("characters", []),
                "mood": structured.get("mood", ""),
                "estimated_duration_seconds": durations[i],
                "continuity_notes": structured.get("continuity_notes", ""),
                "recommended_aspect_ratio": structured.get(
                    "recommended_aspect_ratio", DEFAULT_ASPECT_RATIO
                ),
                "recommended_shot_type": structured.get("recommended_shot_type", ""),
            }
        )

    return {
        "topic": metadata["topic"],
        "source_metadata": metadata,
        "scene_count": len(manifest_scenes),
        "total_estimated_duration_seconds": round(sum(durations), 1),
        "scenes": manifest_scenes,
    }
