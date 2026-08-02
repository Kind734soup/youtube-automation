"""Turns a Script Agent output folder into a narration_manifest.json.

script.md gives us narration text, split into TTS-sized sections by
section_parser.py. That text alone doesn't say how it should be spoken,
so each section is passed through an LLM once to work out voice tone,
speaking pace, pause placement, and any pronunciation notes (unusual
names or invented words the narrator/voice model should get right). No
voice API is called here - this only produces the manifest.
"""

import json
import re

from voice_generation_agent.llm_client import generate
from voice_generation_agent.section_parser import load_source_files

WORDS_PER_MINUTE = 135  # same slow, calming narration pace assumption as script_agent
OUTPUT_FORMAT = "mp3"  # placeholder for the eventual rendered audio format

SYSTEM_PROMPT = (
    "You are the narration-direction step of a Voice Generation Agent for the Nightfall "
    "Atlas YouTube channel, a premium sleep storytelling channel. You take a chunk of "
    "narration text and turn it into concrete voice direction for a text-to-speech "
    "provider (for example OpenAI's TTS or ElevenLabs). The channel's voice is always "
    "slow, warm, hushed and calming - never energetic, never rushed, never dramatic. "
    "Be concrete and specific; these fields feed a JSON manifest a TTS provider or a "
    "human voice director will read, not a listener."
)


def _parse_json_object(text):
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _direct_section(topic, section, previous_section):
    context = f"Story topic: {topic}\n"
    if previous_section:
        context += (
            f'This section continues from a previous section in the same scene '
            f'("{previous_section["scene_title"]}"). Keep tone and pace consistent with it.\n'
        )

    prompt = (
        f"{context}\n"
        f'Section {section["section_number"]}, from scene "{section["scene_title"]}"\n\n'
        f"Narration text for this section:\n{section['narration']}\n\n"
        "Respond with ONLY a JSON object, no other text, in this exact shape:\n"
        "{\n"
        '  "voice_tone": "e.g. warm, hushed, gently reassuring",\n'
        '  "speaking_pace": "e.g. slow, unhurried, with generous space between sentences",\n'
        '  "pause_guidance": "concrete pause placement - e.g. brief pause after each sentence, '
        'a longer 2-3s pause between paragraphs, extra pause before/after this section",\n'
        '  "pronunciation_notes": "any proper nouns, invented words, or unusual terms in this '
        'text and how to pronounce them - phonetic spelling is fine. Use \\"None\\" if there '
        'are none"\n'
        "}"
    )
    raw = generate(SYSTEM_PROMPT, prompt, max_tokens=500)
    return _parse_json_object(raw)


def build_manifest(folder):
    """Read a Script Agent output folder and return a narration manifest dict.
    Does not write anything to disk - see organizer.save_manifest() for that."""
    metadata, sections = load_source_files(folder)

    manifest_sections = []
    previous_section = None
    for section in sections:
        directed = _direct_section(metadata["topic"], section, previous_section)

        word_count = len(section["narration"].split())
        duration_seconds = round(word_count / WORDS_PER_MINUTE * 60, 1)

        manifest_sections.append(
            {
                "section_number": section["section_number"],
                "scene_title": section["scene_title"],
                "narration": section["narration"],
                "estimated_duration_seconds": duration_seconds,
                "voice_tone": directed.get("voice_tone", ""),
                "speaking_pace": directed.get("speaking_pace", ""),
                "pause_guidance": directed.get("pause_guidance", ""),
                "pronunciation_notes": directed.get("pronunciation_notes", "None"),
                "output_filename": f"section_{section['section_number']:02d}.{OUTPUT_FORMAT}",
            }
        )
        previous_section = section

    total_seconds = round(sum(s["estimated_duration_seconds"] for s in manifest_sections), 1)

    return {
        "topic": metadata["topic"],
        "source_metadata": metadata,
        "section_count": len(manifest_sections),
        "total_estimated_duration_seconds": total_seconds,
        "sections": manifest_sections,
    }
