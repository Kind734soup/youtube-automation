"""Turns a project's inputs (metadata, script excerpt, scene list,
existing scene images) into 3 ranked thumbnail concepts plus one
polished image-generation prompt for the recommended concept, via an
LLM (see llm_client.py).

Pure prompt-building and response-parsing here - no file I/O. See
organizer.py for reading inputs and writing thumbnail_prompt.md /
thumbnail_manifest.json.
"""

import json
import re

from thumbnail_agent import llm_client

CHANNEL_NAME = "Nightfall Atlas"
TEXT_OVERLAY_MAX_WORDS = 4
REQUIRED_CONCEPT_FIELDS = (
    "rank",
    "name",
    "main_subject",
    "background",
    "composition",
    "lighting",
    "colors",
    "focal_emotion",
    "text_overlay",
    "avoid",
)

SYSTEM_PROMPT = (
    f"You are a senior YouTube thumbnail designer for {CHANNEL_NAME}, a cinematic history / "
    "sleep-story channel. Its videos are slow, calming, long-form narrated stories about ancient "
    "history and mythology (Egypt, Rome, Greece, and similar), meant to help viewers relax and fall "
    "asleep. Thumbnails must earn a click while staying tasteful, cinematic, and calm - never "
    "sensational, cluttered, or generic-looking 'AI art'. You always reply with strictly valid JSON "
    "and nothing else - no commentary, no markdown code fences."
)

RESPONSE_SCHEMA_EXAMPLE = """{
  "concepts": [
    {
      "rank": 1,
      "name": "short concept name",
      "main_subject": "the single dominant subject in the frame",
      "background": "what's behind/around the subject",
      "composition": "framing, rule-of-thirds placement, depth",
      "lighting": "light source, direction, mood",
      "colors": "the dominant palette",
      "focal_emotion": "facial expression/emotion if a person appears, otherwise the mood focal point",
      "text_overlay": "3-4 word overlay text",
      "avoid": "what must be avoided for this concept specifically"
    }
  ],
  "recommended_rank": 1,
  "recommended_reason": "one or two sentences on why this concept wins",
  "final_image_prompt": "one polished, ready-to-use prompt for an image generator, describing the recommended concept in full cinematic detail"
}"""


def _format_scenes(scenes):
    lines = []
    for scene in scenes:
        prompt = (scene.get("visual_prompt") or "").strip()
        if len(prompt) > 220:
            prompt = prompt[:220].rsplit(" ", 1)[0].rstrip() + "..."
        lines.append(f"- Scene {scene['scene_number']}: {scene['title']} - {prompt}")
    return "\n".join(lines)


def build_user_prompt(metadata, script_excerpt, scenes, existing_scene_images):
    topic = metadata["topic"]

    parts = [
        f'Video title/topic: "{topic}"',
        "",
        "Opening mood of the script (for tone/setting only):",
        f'"{script_excerpt}"',
        "",
        "Scenes already planned for this video:",
        _format_scenes(scenes),
    ]

    if existing_scene_images:
        parts += [
            "",
            f"Existing generated scene reference images (match their visual style/era for consistency): "
            f"{', '.join(existing_scene_images)}",
        ]

    parts += [
        "",
        "Task: design 3 distinct YouTube thumbnail concepts for this video.",
        "",
        "For each concept, specify: main_subject, background, composition, lighting, colors, "
        "focal_emotion (facial expression or focal emotion if a person is used, otherwise the "
        f"scene's emotional focal point), text_overlay (a short overlay, MAXIMUM {TEXT_OVERLAY_MAX_WORDS} "
        "words), and avoid (what should specifically be avoided for that concept).",
        "",
        "Then rank the 3 concepts from strongest (1) to weakest (3) by likely click-through appeal "
        f"balanced against {CHANNEL_NAME}'s calm, tasteful tone, recommend one, and write one polished "
        "image-generation prompt for the recommended concept - cinematic, painterly or photoreal "
        "historical illustration style, no text baked into the image itself, and explicitly avoiding "
        "clutter, tiny/illegible text, misleading imagery, and generic 'AI art' composition clichés "
        "(warped anatomy, extra fingers, watermarks, stock-photo look).",
        "",
        "Reply with ONLY valid JSON, no commentary, no markdown fences, matching exactly this shape "
        "(3 entries in \"concepts\"):",
        RESPONSE_SCHEMA_EXAMPLE,
    ]
    return "\n".join(parts)


def _extract_json(raw_text):
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            text = text[brace_start : brace_end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse the LLM reply as JSON: {exc}. Raw reply started with: {raw_text[:200]!r}"
        ) from exc


def validate_concepts(parsed):
    """Returns a list of human-readable warning strings - never raises.
    Structural problems (missing keys, wrong concept count) are hard
    errors raised by parse_response(); this only flags soft quality
    issues an LLM might still slip past the schema."""
    warnings = []
    concepts = parsed.get("concepts", [])

    for concept in concepts:
        overlay = concept.get("text_overlay", "")
        word_count = len(overlay.split())
        if word_count > TEXT_OVERLAY_MAX_WORDS:
            warnings.append(
                f"concept '{concept.get('name', '?')}' text_overlay has {word_count} words "
                f"(max {TEXT_OVERLAY_MAX_WORDS}): {overlay!r}"
            )

    recommended_rank = parsed.get("recommended_rank")
    ranks = {c.get("rank") for c in concepts}
    if recommended_rank not in ranks:
        warnings.append(f"recommended_rank {recommended_rank!r} does not match any concept's rank {sorted(ranks)}")

    return warnings


def parse_response(raw_text):
    """Parses and structurally validates one LLM reply. Raises ValueError
    on anything that would make thumbnail_manifest.json unusable (bad
    JSON, wrong number of concepts, missing required fields)."""
    parsed = _extract_json(raw_text)

    concepts = parsed.get("concepts")
    if not isinstance(concepts, list) or len(concepts) != 3:
        raise ValueError(f"Expected exactly 3 thumbnail concepts, got {len(concepts) if concepts else 0}.")

    for concept in concepts:
        missing = [field for field in REQUIRED_CONCEPT_FIELDS if not concept.get(field) and concept.get(field) != 0]
        if missing:
            raise ValueError(f"Concept {concept.get('name', '?')!r} is missing required field(s): {missing}")

    if "recommended_rank" not in parsed or "final_image_prompt" not in parsed:
        raise ValueError("LLM reply is missing 'recommended_rank' and/or 'final_image_prompt'.")

    concepts.sort(key=lambda c: c["rank"])
    parsed["concepts"] = concepts
    return parsed


def generate_concepts(metadata, script_excerpt, scenes, existing_scene_images, provider_name=None):
    """Calls the configured LLM provider and returns (parsed, warnings)."""
    prompt = build_user_prompt(metadata, script_excerpt, scenes, existing_scene_images)
    raw_reply = llm_client.generate(SYSTEM_PROMPT, prompt, provider_name=provider_name)
    parsed = parse_response(raw_reply)
    warnings = validate_concepts(parsed)
    return parsed, warnings
