# Video Production Agent

Turns a finished Script Agent output into a structured `production_manifest.json`
that describes exactly what needs to be generated, scene by scene. It is a
completely separate agent from the Research Agent (`agent/`) and Script Agent
(`script_agent/`) - it does not import from either, and does not modify
anything they produce.

**This agent does not call any video generation API.** It only produces a
manifest. Wiring up an actual video provider (Google Veo, Runway, Kling,
Pika, ...) is future work - see "Adding a video provider" below.

## What it consumes

Exactly three files from a Script Agent output folder
(`scripts/<topic-slug>_<date>/`):

- `script.md` - narration text, one `##` section per scene
- `scene_descriptions.md` - a rough, free-form visual description per scene
- `metadata.json` - topic, target/estimated runtime, word count

It never reads or writes anything under `research/` or `script_agent/`.

## What it produces

`production_manifest.json`, written into the same source folder, alongside
`script.md` and `scene_descriptions.md`. Each entry in its `scenes` array has:

| Field | Description |
|---|---|
| `scene_number` | 1-indexed position in the story |
| `title` | Scene title, from `script.md` |
| `narration` | Full narration text for the scene |
| `visual_prompt` | Self-contained prompt describing the scene, for a video model |
| `camera_movement` | e.g. "slow forward drift", "static wide shot" |
| `lighting` | Lighting description |
| `environment` | The physical setting/location |
| `characters` | List of characters/figures present (often empty - this channel is mostly landscapes) |
| `mood` | Emotional tone of the shot |
| `estimated_duration_seconds` | Scene's share of the script's total estimated runtime, split by narration word count |
| `continuity_notes` | How this scene should visually connect to its neighbors (recurring colors, objects, framing) |
| `recommended_aspect_ratio` | e.g. "16:9" |
| `recommended_shot_type` | e.g. "wide establishing shot", "slow aerial", "medium tracking shot" |

The manifest also carries the original `metadata.json` verbatim under
`source_metadata`, plus `topic`, `scene_count`, and
`total_estimated_duration_seconds`.

**Duration precedence:** `estimated_duration_seconds` here is a video-side estimate (proportional to word count), useful for planning shot length before narration exists. Once the Voice Generation Agent and Video Editor Agent have run, the Video Editor Agent's `edit_manifest.json` timing - driven by actual narration duration - is authoritative; this field is not recalculated to match it.

## How it works

1. **`scene_parser.py`** - pure parsing, no AI. Splits `script.md` on `##`
   headers and `scene_descriptions.md` on `## Scene N: ...` headers, and
   pairs them up by position into one dict per scene.
2. **`manifest_builder.py`** - for each scene, calls an LLM once with the
   narration and the rough visual description (plus the neighboring scenes'
   descriptions, for continuity) and asks it to return the structured fields
   above as JSON. `estimated_duration_seconds` is computed in code (not by
   the LLM), by splitting the script's total estimated runtime across scenes
   proportionally to narration word count.
3. **`organizer.py`** - writes the assembled manifest to
   `production_manifest.json` in the source folder.

The LLM call goes through the same provider-agnostic pattern as
`script_agent`: `llm_client.py` picks a provider (`manual` or `anthropic`)
based on `LLM_PROVIDER` in `.env`. This is its own independent copy under
`video_production_agent/llm_providers/` - it shares no code with
`script_agent/llm_providers/`, only the same `.env` settings.

## Usage

```
python video_production_agent/main.py build --from-script scripts/<topic-slug>_<date>
```

With `LLM_PROVIDER=manual` (the default, no API key needed), it will print
one prompt per scene for you to paste into Claude Pro and read the reply
back from the terminal - the same workflow as the Script Agent's manual
mode. Prompts are also saved to `video_production_agent/_manual_prompts/`.

With `LLM_PROVIDER=anthropic` set in `.env`, it calls the Anthropic API
directly instead.

## Adding a video provider

`video_production_agent/providers/` is where future video-generation
integrations live. Nothing is implemented there yet - `providers/base.py`
defines the interface every provider will implement, and
`providers/__init__.py` documents the registration pattern:

```python
class VideoProvider(ABC):
    @abstractmethod
    def render_scene(self, scene, output_path):
        """Render one production_manifest.json scene to a video clip."""
```

To wire up a real provider later (Google Veo, Runway, Kling, Pika, or
anything else):

1. Write `video_production_agent/providers/<name>_provider.py` implementing
   `VideoProvider`, using whatever that provider's API needs (its own auth,
   its own request/response shape) - it just has to accept one manifest
   scene dict and produce a rendered clip.
2. Add one line to `get_provider()` in `providers/__init__.py` mapping the
   provider's name to that class.
3. Feed it scenes straight out of `production_manifest.json` - no other
   part of this agent needs to change, since the manifest format is the
   stable contract between "what to render" and "how to render it".

Because every scene already carries `visual_prompt`, `camera_movement`,
`lighting`, `environment`, `characters`, `mood`,
`estimated_duration_seconds`, `continuity_notes`, `recommended_aspect_ratio`,
and `recommended_shot_type`, a new provider only needs to map those fields
onto its own API parameters - it doesn't need to re-derive them from the
original script.
