# Voice Generation Agent

Turns a finished Script Agent output into a structured `narration_manifest.json`
that splits the script into manageable, TTS-ready audio sections with voice
direction for each one. It is a completely separate agent from the Research
Agent (`agent/`), Script Agent (`script_agent/`), and Video Production Agent
(`video_production_agent/`) - it does not import from any of them, and does
not modify anything they produce.

**This agent does not require any paid voice API.** Building
`narration_manifest.json` never calls a voice provider at all - it only
calls an LLM for voice direction (see "How it works" below). Rendering
real audio uses `windows_sapi` (free, offline, local Windows
text-to-speech, no API key) by default - see "Rendering real audio"
below. Paid providers (OpenAI TTS, ElevenLabs, ...) can be added later
behind the same `VoiceProvider` interface - see "Adding a voice provider".

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

Separately, once a voice provider renders real audio (see "Rendering real
audio" below), the actual audio files are written to
`<project folder>/assets/audio/`, alongside (not inside) the other
manifests.

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

## Rendering real audio

Once `narration_manifest.json` exists (see "Usage" above), a separate
step renders real audio files from it using a connected `VoiceProvider`.
This never needs an LLM - it only needs the manifest and a voice
provider.

### Setup (windows_sapi - the default, free, offline provider)

`windows_sapi` uses whatever voices are already installed in Windows
Speech via [pyttsx3](https://pypi.org/project/pyttsx3/), Windows' own
SAPI5 text-to-speech engine. No API key, no account, no internet
connection, no cost. It needs two packages that aren't in this agent's
base `requirements.txt` (they're Windows-only and optional - only
installed if you actually want local audio rendering):

```
.venv\Scripts\python.exe -m pip install pyttsx3 pywin32
```

You can check which voices are available on your machine with:
```
.venv\Scripts\python.exe -c "import pyttsx3; [print(v.id, '|', v.name) for v in pyttsx3.init().getProperty('voices')]"
```
Windows ships with at least one voice (e.g. "Microsoft David Desktop" /
"Microsoft Zira Desktop") out of the box; more can be added in Windows
Settings → Time & Language → Speech.

Which provider gets used is controlled by `VOICE_PROVIDER` in `.env`
(see `.env.example`) - it defaults to `windows_sapi` even if unset, so no
`.env` change is required to use it.

### Commands

```
python voice_generation_agent/main.py test-first --from-script scripts/<topic-slug>_<date>
python voice_generation_agent/main.py narrate --from-script scripts/<topic-slug>_<date>
```

- **`test-first`** renders only section 1's audio - use this first, to
  sanity-check narration text and voice settings before committing to a
  full render.
- **`narrate`** renders every section.

Both write `.wav` files into `<project folder>/assets/audio/`, named
after each section's manifest entry - e.g. `narration_manifest.json`'s
`output_filename: "section_01.mp3"` becomes
`assets/audio/section_01.wav`. The `.wav` extension (not `.mp3`) is
because that's the real format `windows_sapi` produces; a future
provider like OpenAI TTS or ElevenLabs would produce `.mp3` instead - see
"Adding a voice provider" below for why the extension is decided by the
provider, not hardcoded.

Both commands accept `--provider <name>` to override `VOICE_PROVIDER` for
a single run (currently only `windows_sapi` is implemented).

### Tested (real audio)

Ran `test-first` against the Ancient Egypt script's real section 1
narration: produced a valid mono 16-bit 22050Hz WAV file at
`assets/audio/section_01.wav`, confirmed both by the CLI's own report and
by reading the file back with Python's `wave` module - `171.25` seconds,
matching exactly between the provider's self-reported duration and the
file's actual frame count ÷ sample rate.

### Implementation note: a fresh engine per section

`windows_sapi_provider.py` creates a brand-new `pyttsx3` engine for every
section instead of reusing one engine across a whole story. This was
discovered the hard way while building this provider: calling
`runAndWait()` repeatedly on one reused engine instance hung indefinitely
on Windows SAPI5 (confirmed - it hung on the very first iteration of a
reuse loop). A fresh engine per section is slightly slower to start up
but reliable; `narrate` (rendering a full ~9-section story) will take
noticeably longer than a single `test-first` call as a result.

## Adding a voice provider

`voice_generation_agent/providers/` is where text-to-speech integrations
live. `windows_sapi_provider.py` (see "Rendering real audio" above) is
the first one, implementing `providers/base.py`'s interface:

```python
class VoiceProvider(ABC):
    @abstractmethod
    def synthesize_section(self, section, output_path_stem):
        """Render one narration_manifest.json section to an audio file.

        output_path_stem has no extension - the provider appends whatever
        extension its own output format actually is (.wav, .mp3, ...) and
        returns the real path in its result dict.
        """
```

To wire up a paid/hosted provider later (OpenAI TTS, ElevenLabs, or
anything else):

1. Write `voice_generation_agent/providers/<name>_provider.py`
   implementing `VoiceProvider`, using whatever that provider's API needs
   (its own auth, its own request/response shape) - it just has to accept
   one manifest section dict and produce a rendered audio file.
2. Add one line to `get_provider()` in `providers/__init__.py` mapping the
   provider's name to that class (see how `windows_sapi` is registered
   there already).
3. Set `VOICE_PROVIDER=<name>` in `.env` (or pass `--provider <name>` on
   the command line) - no other part of this agent needs to change, since
   `narration_manifest.json` is the stable contract between "what to say
   and how" and "how to render it".

Because every section already carries `narration`, `voice_tone`,
`speaking_pace`, `pause_guidance`, `pronunciation_notes`, and
`output_filename`, a new provider only needs to map those fields onto its
own API parameters (for example ElevenLabs' stability/style sliders, or
OpenAI TTS's `voice` and `speed` parameters) - it doesn't need to
re-derive them from the original script.
