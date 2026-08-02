# Voice Generation Agent

Turns a finished Script Agent output into a structured `narration_manifest.json`
that splits the script into manageable, TTS-ready audio sections with voice
direction for each one. It is a completely separate agent from the Research
Agent (`agent/`), Script Agent (`script_agent/`), and Video Production Agent
(`video_production_agent/`) - it does not import from any of them, and does
not modify anything they produce.

**This agent does not call any paid voice API.** It only produces a
manifest. Wiring up an actual voice provider (OpenAI TTS, ElevenLabs, ...)
is future work - see "Adding a voice provider" below.

## What it consumes

Exactly two files from a Script Agent output folder
(`scripts/<topic-slug>_<date>/`):

- `script.md` - narration text, one `##` section per scene
- `metadata.json` - topic, target/estimated runtime, word count

It never reads `scene_descriptions.md`, and never reads or writes anything
under `research/`, `script_agent/`, or `video_production_agent/`.

## What it produces

`narration_manifest.json`, written into the same source folder, alongside
`script.md`. Each entry in its `sections` array has:

| Field | Description |
|---|---|
| `section_number` | 1-indexed position across the whole script |
| `scene_title` | Which scene (from `script.md`) this section came from |
| `narration` | The narration text for this section |
| `estimated_duration_seconds` | Estimated speaking time, at the channel's ~135 words/minute pace |
| `voice_tone` | e.g. "warm, hushed, gently reassuring" |
| `speaking_pace` | e.g. "slow, unhurried, with generous space between sentences" |
| `pause_guidance` | Concrete pause placement - after sentences, between paragraphs, section boundaries |
| `pronunciation_notes` | Unusual proper nouns or invented words in this section and how to say them, or "None" |
| `output_filename` | Suggested filename for the rendered clip, e.g. `section_01.mp3` |

The manifest also carries the original `metadata.json` verbatim under
`source_metadata`, plus `topic`, `section_count`, and
`total_estimated_duration_seconds`.

**Duration precedence:** this agent's `estimated_duration_seconds` is what the Video Editor Agent treats as authoritative when it builds the final timeline - narration length is what actually determines a video's runtime, not the Video Production Agent's separate (and slightly different) per-scene estimate.

## How it works

1. **`section_parser.py`** - pure parsing, no AI, no voice API. Splits
   `script.md` on `##` scene headers, then further splits any scene whose
   narration exceeds `MAX_CHARS_PER_SECTION` (3000 characters) on
   paragraph boundaries, so no single section is too large for a TTS
   provider to handle well (OpenAI's TTS endpoint caps input at 4096
   characters; ElevenLabs recommends shorter chunks for more consistent
   prosody). Most scenes in a Nightfall Atlas script fit in one section;
   a longer scene becomes two or more, still tagged with the same
   `scene_title` so they can be recombined later.
2. **`manifest_builder.py`** - for each section, calls an LLM once with
   the narration text (and a note of which scene it continues from, for
   tonal consistency) and asks it to return voice direction as JSON:
   tone, pace, pause guidance, and pronunciation notes.
   `estimated_duration_seconds` and `output_filename` are computed in
   code, not by the LLM.
3. **`organizer.py`** - writes the assembled manifest to
   `narration_manifest.json` in the source folder.

The LLM call goes through the same provider-agnostic pattern as
`script_agent` and `video_production_agent`: `llm_client.py` picks a
provider (`manual` or `anthropic`) based on `LLM_PROVIDER` in `.env`. This
is its own independent copy under `voice_generation_agent/llm_providers/`
- it shares no code with the other agents' copies, only the same `.env`
settings.

## Usage

```
python voice_generation_agent/main.py build --from-script scripts/<topic-slug>_<date>
```

With `LLM_PROVIDER=manual` (the default, no API key needed), it will print
one prompt per section for you to paste into Claude Pro and read the reply
back from the terminal - the same workflow as the other agents' manual
mode. Prompts are also saved to `voice_generation_agent/_manual_prompts/`.

With `LLM_PROVIDER=anthropic` set in `.env`, it calls the Anthropic API
directly instead.

### Tested against

Run against the existing Nightfall Atlas script at
`scripts/fall-asleep-to-the-entire-story-of-ancient-egypt-pyramids-pharaohs-and-gods-ancient-history_2026-08-01/`:
the 8 scenes there produced 9 sections (one scene, "The Barque of Ra", was
just over the 3000-character limit and was split in two), summing to
~28.9 minutes of estimated narration - matching that script's own
`metadata.json`.

## Adding a voice provider

`voice_generation_agent/providers/` is where future text-to-speech
integrations live. Nothing is implemented there yet - `providers/base.py`
defines the interface every provider will implement, and
`providers/__init__.py` documents the registration pattern:

```python
class VoiceProvider(ABC):
    @abstractmethod
    def synthesize_section(self, section, output_path):
        """Render one narration_manifest.json section to an audio file."""
```

To wire up a real provider later (OpenAI TTS, ElevenLabs, or anything
else):

1. Write `voice_generation_agent/providers/<name>_provider.py`
   implementing `VoiceProvider`, using whatever that provider's API needs
   (its own auth, its own request/response shape) - it just has to accept
   one manifest section dict and produce a rendered audio file.
2. Add one line to `get_provider()` in `providers/__init__.py` mapping the
   provider's name to that class.
3. Feed it sections straight out of `narration_manifest.json` - no other
   part of this agent needs to change, since the manifest format is the
   stable contract between "what to say and how" and "how to render it".

Because every section already carries `narration`, `voice_tone`,
`speaking_pace`, `pause_guidance`, `pronunciation_notes`, and
`output_filename`, a new provider only needs to map those fields onto its
own API parameters (for example ElevenLabs' stability/style sliders, or
OpenAI TTS's `voice` and `speed` parameters) - it doesn't need to
re-derive them from the original script.
