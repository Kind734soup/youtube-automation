# Video Editor Agent

Turns a project that has already been through the Script Agent, Video
Production Agent, and Voice Generation Agent into a structured
`edit_manifest.json` - a complete assembly timeline ready for FFmpeg to
render, once real video clips and narration audio exist. It is a
completely separate agent from the Research Agent (`agent/`), Script
Agent (`script_agent/`), Video Production Agent (`video_production_agent/`),
and Voice Generation Agent (`voice_generation_agent/`) - it does not
import from any of them, and does not modify anything they produce.

**This agent does not require real video clips, audio files, or any paid
API.** It only produces a manifest full of placeholders and computed
timing. Actually running FFmpeg happens later - see "Assembling the final
video (future work)" below.

## What it consumes

Four files from a project folder (`scripts/<topic-slug>_<date>/`) that has
already been through all three upstream agents:

- `production_manifest.json` - from the Video Production Agent (per-scene visual prompt, camera, lighting, environment, mood, recommended aspect ratio, ...)
- `narration_manifest.json` - from the Voice Generation Agent (per-section narration, duration, voice direction, output filename)
- `script.md` - the original narration text, used to generate on-screen captions
- `metadata.json` - topic and project metadata

It never modifies any of these, and never reads or writes anything under
`research/`, `script_agent/`, `video_production_agent/`, or
`voice_generation_agent/`.

## What it produces

`edit_manifest.json`, written into the same project folder. Top-level
fields:

| Field | Description |
|---|---|
| `topic` | The story's topic, carried over from `metadata.json` |
| `source_metadata` | The original `metadata.json`, carried over verbatim |
| `scene_count` | Number of entries in `timeline` |
| `total_duration_seconds` | Sum of every timeline entry's `duration_seconds` |
| `final_resolution` / `final_aspect_ratio` | Derived from the most common `recommended_aspect_ratio` across the Video Production Agent's scenes (e.g. `1920x1080` / `16:9`) |
| `framerate_fps` | Target framerate for the final render (currently a fixed default of 24) |
| `export_settings` | Container, video/audio codec, bitrates, framerate, pixel format - an FFmpeg-ready encode target |
| `timeline` | Ordered list of scene entries, see below |

Each entry in `timeline` has:

| Field | Description |
|---|---|
| `timeline_index` | 1-indexed position in the final video |
| `start_time_seconds` / `end_time_seconds` | This scene's position on the overall timeline |
| `narration_section_numbers` | Which `narration_manifest.json` section(s) this scene corresponds to (usually one - see "Multi-section scenes" below) |
| `visual_asset_filename` | Placeholder filename for this scene's rendered clip, e.g. `scene_05.mp4` |
| `audio_asset_filenames` | The matching narration section(s)' `output_filename` values from `narration_manifest.json` |
| `transition_in` / `transition_out` | Type + duration, e.g. `crossfade` at 2s between scenes, `fade_from_black`/`fade_to_black` at the very start/end |
| `volume_levels_db` | Default mix levels for narration/music/ambient tracks |
| `music_cue` | A short description of the music bed for this scene, or `"None"` |
| `ambient_sound_cue` | A short description of the ambient/foley sound bed, or `"None"` |
| `captions` | A list of `{text, start_time_seconds, end_time_seconds}` cues, chunked from `script.md`'s narration for this scene |

## How it works

1. **`timeline_builder.py`** - pure computation, no AI, no FFmpeg. Loads
   all four input files, matches each Video Production Agent scene to its
   Voice Generation Agent narration section(s) by scene title, and
   computes:
   - timeline order and start/end times (the audio's own estimated
     duration drives timing, since the narration - not the as-yet-unmade
     visuals - is what will actually determine final video length)
   - placeholder `visual_asset_filename` / real `audio_asset_filenames`
   - transitions, default volume levels, and fade timing (a fixed
     convention: crossfades between scenes, a slow fade in from black at
     the start and a slower fade to black at the end, matching the
     channel's wind-down ending)
   - captions, by splitting each scene's `script.md` narration into short
     lines and spacing them proportionally across the scene's duration
2. **`manifest_builder.py`** - the one thing that can't be computed from
   timing data alone is what a scene should sound like underneath the
   narration. For each scene, it calls an LLM once with that scene's
   environment/mood/visual prompt (already written by the Video
   Production Agent) and asks for a `music_cue` and `ambient_sound_cue`.
   It also picks `final_resolution`/`final_aspect_ratio` and assembles
   `export_settings`.
3. **`organizer.py`** - writes the assembled manifest to
   `edit_manifest.json` in the project folder.

The LLM call goes through the same provider-agnostic pattern as the other
three agents: `llm_client.py` picks a provider (`manual` or `anthropic`)
based on `LLM_PROVIDER` in `.env`. This is its own independent copy under
`video_editor_agent/llm_providers/` - it shares no code with the other
agents' copies, only the same `.env` settings.

### Multi-section scenes

A scene can span more than one narration section if the Voice Generation
Agent had to split it for TTS length limits (see that agent's
`MAX_CHARS_PER_SECTION`). When that happens, `narration_section_numbers`
and `audio_asset_filenames` list more than one entry, in order - the
eventual FFmpeg step concatenates them into one continuous narration
track for that scene, still under a single visual clip and a single
timeline entry.

### Duration precedence

The Video Production Agent and Voice Generation Agent each estimate scene/section duration independently (proportional word-count split of the script's total runtime, vs. word count ÷ 135 wpm), so their totals can differ slightly - about 0.1% in testing against the Ancient Egypt script. This agent always uses the Voice Generation Agent's narration-based durations for `start_time_seconds`/`end_time_seconds`/`duration_seconds`, since narration length is what will actually determine the final video's runtime once real audio exists. `production_manifest.json`'s own `estimated_duration_seconds` is informational only past this point.

## Usage

```
python video_editor_agent/main.py build --from-script scripts/<topic-slug>_<date>
```

The target folder must already contain `production_manifest.json` (from
the Video Production Agent) and `narration_manifest.json` (from the Voice
Generation Agent), in addition to `script.md` and `metadata.json`.

With `LLM_PROVIDER=manual` (the default, no API key needed), it will print
one prompt per scene for you to paste into Claude Pro and read the reply
back from the terminal - the same workflow as the other agents' manual
mode. Prompts are also saved to `video_editor_agent/_manual_prompts/`.

With `LLM_PROVIDER=anthropic` set in `.env`, it calls the Anthropic API
directly instead.

### Tested against

Built a `production_manifest.json` and `narration_manifest.json` for the
existing Nightfall Atlas Ancient Egypt script and ran this agent against
them: 8 video scenes matched up correctly against the Voice Generation
Agent's 9 narration sections (scene 5, "The Barque of Ra", correctly spans
two narration sections), producing a `1735.6`-second (~28.9 min) timeline
with `1920x1080` / `16:9` output settings, per-scene captions chunked from
`script.md`, and a music/ambient cue for every scene.

## Assembling the final video (future work)

`ffmpeg_assembler.py` documents, but does not implement, the FFmpeg
assembly step. It isn't implemented yet because there's nothing real to
assemble: `production_manifest.json` and `narration_manifest.json` only
exist as manifests until `video_production_agent/providers/` and
`voice_generation_agent/providers/` each have a real provider connected
(Veo/Runway/Kling/Pika for video, OpenAI TTS/ElevenLabs for voice).

Once real files exist in an assets folder next to `edit_manifest.json`,
named exactly per each timeline entry's `visual_asset_filename` /
`audio_asset_filenames`, `assemble_video(edit_manifest, assets_dir,
output_path)` is where that command gets built:

1. For each timeline entry, take its visual clip and concatenate its
   `audio_asset_filenames` into that entry's narration track.
2. Chain entries together in timeline order with FFmpeg's `xfade` (video)
   and `acrossfade` (audio) filters, using each entry's `transition_in` /
   `transition_out` type and duration.
3. Mix in `music_cue` / `ambient_sound_cue` as additional audio inputs
   (once real music/ambience files are chosen for each cue), scaled with
   a `volume` filter from `volume_levels_db` and faded with the same
   durations as the visual transitions.
4. Turn `captions` into burned-in `drawtext` filters or a sidecar
   `.srt`/`.vtt` file.
5. Scale/pad to `final_resolution` and encode with `export_settings`.

Every value that step needs is already in `edit_manifest.json` - implementing
`assemble_video()` is then just translating that data into an FFmpeg
command, which is exactly the kind of concrete, well-specified task Claude
Code can pick up directly once real assets exist.
