"""Generates a full Nightfall Atlas sleep story: an outline, then narration
and a visual description for each scene.

Two stages, because asking one API call for a whole 30-45 minute script
reliably is unrealistic:
  1. Outline - a short JSON plan of ~8 scenes with a word budget each.
  2. Scene-by-scene - each scene is generated with the ending of the
     previous scene as context, so the story flows continuously instead
     of reading like disconnected chunks.
"""

import json
import re
from pathlib import Path

from script_agent.llm_client import generate

WORDS_PER_MINUTE = 135  # rough estimate for a slow, calming narration pace
SCENE_COUNT = 8

STYLE_GUIDE = (Path(__file__).resolve().parent / "style_guide.md").read_text(encoding="utf-8")


def _parse_json_array(text):
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _build_outline(topic, target_minutes):
    total_words = target_minutes * WORDS_PER_MINUTE
    system = "You are a story outline planner for the Nightfall Atlas YouTube channel.\n\n" + STYLE_GUIDE
    prompt = (
        f'Plan a {SCENE_COUNT}-scene sleep story outline for the topic: "{topic}".\n'
        f"Total narration across all scenes should be about {total_words} words.\n\n"
        "Respond with ONLY a JSON array, no other text, in this shape:\n"
        '[{"title": "...", "summary": "...", "target_words": 500}, ...]\n\n'
        f"There must be exactly {SCENE_COUNT} scenes. target_words values should sum to "
        f"about {total_words}. The first scene must be a gentle, non-demanding opening. "
        "The last scene must wind the listener down toward sleep."
    )
    raw = generate(system, prompt, max_tokens=2000)
    return _parse_json_array(raw)


def _parse_scene_response(text):
    narration_match = re.search(r"===NARRATION===\s*(.*?)\s*===VISUAL===", text, re.DOTALL)
    visual_match = re.search(r"===VISUAL===\s*(.*)", text, re.DOTALL)
    narration = narration_match.group(1).strip() if narration_match else text.strip()
    visual = visual_match.group(1).strip() if visual_match else ""
    return narration, visual


def _generate_scene(topic, outline, index, previous_ending):
    scene = outline[index]
    system = "You are the narration writer for the Nightfall Atlas YouTube channel.\n\n" + STYLE_GUIDE

    position_note = ""
    if index == 0:
        position_note = "This is the OPENING scene - ease the listener in gently, do not demand attention."
    elif index == len(outline) - 1:
        position_note = "This is the FINAL scene - wind the listener down and encourage sleep."

    context = f"Story topic: {topic}\n\n"
    if previous_ending:
        context += (
            f'The previous scene ended with:\n"...{previous_ending}"\n\n'
            "Continue naturally from there with a gentle transition.\n\n"
        )

    prompt = (
        f"{context}"
        f'Write scene {index + 1} of {len(outline)}: "{scene["title"]}"\n'
        f"Scene summary: {scene['summary']}\n"
        f"{position_note}\n"
        f"Target length: approximately {scene['target_words']} words of narration.\n\n"
        "Respond in exactly this format:\n"
        "===NARRATION===\n"
        "<the narration text for this scene only>\n"
        "===VISUAL===\n"
        "<a short, concrete visual description of this scene for an artist: setting, "
        "lighting, mood, key objects>"
    )
    max_tokens = max(int(scene["target_words"] * 2.2), 400)
    raw = generate(system, prompt, max_tokens=max_tokens)
    return _parse_scene_response(raw)


def write_script(topic, target_minutes=35):
    outline = _build_outline(topic, target_minutes)

    scenes = []
    previous_ending = None
    for i in range(len(outline)):
        narration, visual = _generate_scene(topic, outline, i, previous_ending)
        scenes.append(
            {
                "title": outline[i]["title"],
                "narration": narration,
                "visual_description": visual,
            }
        )
        words = narration.split()
        previous_ending = " ".join(words[-150:]) if len(words) > 150 else narration

    full_script = "\n\n".join(s["narration"] for s in scenes)
    word_count = len(full_script.split())

    return {
        "topic": topic,
        "target_minutes": target_minutes,
        "word_count": word_count,
        "estimated_minutes": round(word_count / WORDS_PER_MINUTE, 1),
        "scenes": scenes,
        "full_script": full_script,
    }
