# Visual Generation Agent

Turns a project's `production_manifest.json` into one still image per
scene. It is a completely separate agent from the Research Agent
(`agent/`), Script Agent (`script_agent/`), Video Production Agent
(`video_production_agent/`), Voice Generation Agent
(`voice_generation_agent/`), Video Editor Agent (`video_editor_agent/`),
and FFmpeg Render Agent (`ffmpeg_render_agent/`) - it does not import
from any of them, and does not modify anything they produce.

Two providers are wired up: the free, offline `PlaceholderProvider`
(still the default), and `OpenAIImagesProvider`, the first real
image-generation provider - see "The `OpenAIImagesProvider`" below.
Wiring up further providers (FLUX, SDXL, Runway, Veo, Kling, Pika, ...)
is future work - see "Adding a visual provider" below.

## What it consumes

Two files from a Video Production Agent output folder
(`scripts/<topic-slug>_<date>/`):

- `production_manifest.json` - every scene's `scene_number`, `title`,
  and `visual_prompt` (plus other fields this agent doesn't need yet)
- `metadata.json` - topic/runtime context, read directly per its own
  input contract, even though `production_manifest.json` already
  carries it under `source_metadata`

It never reads `script.md`, `scene_descriptions.md`,
`narration_manifest.json`, or `edit_manifest.json`.

## What it produces

`<folder>/assets/visuals/scene_NN.png` - one 1920x1080 image per scene,
numbered to match `production_manifest.json`'s `scene_number` (e.g.
scene 1 -> `scene_01.png`). This is this agent's own, canonical output
location.

## How it works

1. **`manifest_reader.py`** - pure parsing, no AI. Reads and validates
   `production_manifest.json` and `metadata.json`.
2. **`providers/`** - `VisualProvider` is the interface every provider
   implements (`generate_visual(scene, output_path)`); `placeholder_provider.py`
   and `openai_images_provider.py` are wired up today.
3. **`organizer.py`** - runs the connected provider over every scene,
   writes `assets/visuals/scene_NN.png`, and (only with `--publish`)
   copies each image on to `assets/video/scene_NN.png` - see "Handing
   images to the FFmpeg Render Agent" below.
4. **`main.py`** - CLI wrapper.

## Usage

```
python visual_generation_agent/main.py generate --from-script scripts/<topic-slug>_<date>
python visual_generation_agent/main.py generate --from-script scripts/<topic-slug>_<date> --force
python visual_generation_agent/main.py generate --from-script scripts/<topic-slug>_<date> --publish
```

- If a scene's image already exists, it's left alone and reported as
  skipped - pass `--force` to regenerate it anyway (matching the same
  idempotency convention as every other agent in this project).
- `--provider` selects a visual provider by name (default:
  `VISUAL_PROVIDER` in `.env`, or `placeholder` if unset).
- `--publish` additionally copies each image to `assets/video/scene_NN.png`
  - see below.

## The `PlaceholderProvider`

Free, offline, no API key. For each scene it draws, with ffmpeg's
`drawtext` filter, onto a 1920x1080 dark-indigo background (matching the
same palette `ffmpeg_render_agent/placeholder_visuals.py` uses for its
own placeholder video clips, so the look is consistent everywhere in
the pipeline before any real image provider is connected):

- the scene number ("SCENE 01")
- the scene title, in warm gold
- the scene's `visual_prompt`, word-wrapped and centered

A subtle `vignette` filter is applied for a dark, cinematic edge falloff
suitable for the channel's Nightfall Atlas style.

## The `OpenAIImagesProvider`

The first real image-generation provider. For each scene it:

1. Builds a prompt from the scene's `visual_prompt` (already art-directed
   by the Video Production Agent) plus its `lighting`, `mood`, and
   `environment` fields when present, with a fixed style suffix keeping
   every image in the channel's calm, painterly, text-free look.
2. Calls OpenAI's Images API (`gpt-image-1` by default) for one image.
3. Normalizes the result to this project's standard `1920x1080` with
   ffmpeg (`scale` + centered `crop`) - gpt-image-1's landscape size
   (`1536x1024`, a 3:2 ratio) doesn't natively match this project's 16:9
   output, so every scene ends up the same resolution as
   `PlaceholderProvider` produces, regardless of which provider ran.

Requires `OPENAI_API_KEY` in `.env` (OpenAI billing must be active - the
Images API has no free tier). Select it with `VISUAL_PROVIDER=openai_images`
in `.env`, or `--provider openai_images` per run. Optional overrides (also
via `.env`, defaults shown): `OPENAI_IMAGE_MODEL=gpt-image-1`,
`OPENAI_IMAGE_SIZE=1536x1024`, `OPENAI_IMAGE_QUALITY=medium`.

Without `OPENAI_API_KEY` set, selecting this provider fails immediately
with a clear `RuntimeError` (matching `AnthropicProvider`'s pattern in
`script_agent`) rather than partway through generation - `placeholder`
remains the default in both `.env.example` and this project's own `.env`,
so nothing about existing (manual/free) runs changes unless you opt in.

## Handing images to the FFmpeg Render Agent

The FFmpeg Render Agent (unmodified, per its own README) looks for real
visual clips at `<folder>/assets/video/<visual_asset_filename>` - not
`assets/visuals/`. `--publish` is the explicit, opt-in step that copies
this agent's canonical output there too, using the same `scene_NN` stem
`edit_manifest.json` already expects (e.g. `scene_01.png` satisfies the
render agent's `_find_existing` glob for `scene_01.*` just as well as a
`.mp4` would).

If a stem already has a file at `assets/video/` (e.g. a previously
generated fallback title-card `.mp4`), `--publish` moves it aside into
`assets/video/_pre_visual_generation_agent/` rather than deleting it,
then copies the new image into place - so a re-render picks up the real
image instead of the old placeholder, and nothing is silently lost.

## Adding a visual provider

`visual_generation_agent/providers/` is where future image/video
integrations live. `providers/base.py` defines the interface:

```python
class VisualProvider(ABC):
    @abstractmethod
    def generate_visual(self, scene, output_path):
        """Generate one still image for a production_manifest.json scene."""
```

To wire one up later (FLUX, SDXL, Runway, Veo, Kling, Pika, or anything
else):

1. Write `visual_generation_agent/providers/<name>_provider.py`
   implementing `VisualProvider`.
2. Add one line to `get_provider()` in `providers/__init__.py`.
3. Feed it scenes straight out of `production_manifest.json` - no other
   file in this agent needs to change.

## Setup

Requires FFmpeg on `PATH` - used by `PlaceholderProvider` to draw its
text-card image, and by `OpenAIImagesProvider` to normalize OpenAI's
returned image to `1920x1080`. Pip packages: `python-dotenv` (project-wide)
plus `openai` (only imported when `openai_images` is actually selected).
`httpx` (a transitive dependency of `openai`, listed explicitly in
`requirements.txt`) is used directly by the test suite below.

## Running the automated tests

`tests/test_openai_images_provider.py` covers `OpenAIImagesProvider`
without ever calling OpenAI - `openai.OpenAI` itself is monkeypatched
with a fake class before the provider can touch it, so **no network
request and no billing is possible**, even if a real `OPENAI_API_KEY` is
set when the suite runs. It checks:

- the provider loads correctly against a mocked client
- a missing `OPENAI_API_KEY` raises a clear `RuntimeError`
- a successful (mocked) generation writes one normalized `1920x1080`
  PNG and leaves no leftover `.tmp`/`.raw.tmp.png` files
- both a decode-level failure (bad image bytes) and an API-level failure
  (simulated `AuthenticationError`) leave **no partial or corrupt file**
  at `output_path`
- `VISUAL_PROVIDER` still defaults to `placeholder` when unset, and
  `.env.example` documents that same default
- `PlaceholderProvider` still generates a fresh image and then correctly
  skips on rerun - unaffected by adding `openai_images`

Run from the repo root:

```
python -m unittest visual_generation_agent.tests.test_openai_images_provider -v
```

## Tested against

Ran against the existing Nightfall Atlas Ancient Egypt project
(`scripts/fall-asleep-to-the-entire-story-of-ancient-egypt-pyramids-pharaohs-and-gods-ancient-history_2026-08-01/`):

- All 8 scenes generated a 1920x1080 PNG at `assets/visuals/scene_NN.png`
  matching `production_manifest.json`'s scene numbering exactly.
- Ran `generate --publish`, which moved the FFmpeg Render Agent's 8
  existing placeholder `.mp4` clips aside into
  `assets/video/_pre_visual_generation_agent/` and copied the 8 new
  PNGs into `assets/video/scene_NN.png`.
- Re-ran the (unmodified) FFmpeg Render Agent. `render_report.md`
  reported every scene as `existing file (scene_NN.png)` instead of
  `placeholder (generated)`, and sampled frames from the rendered
  `final.mp4` at 10s and 250s show the new images on screen, confirmed
  visually.

`OpenAIImagesProvider` (added after the above): confirmed the provider
registry, `.env`/`--provider` selection, and the manual/free `placeholder`
default all still work unchanged - `generate` against the Ancient Egypt
project with no `--provider` flag still resolves to `placeholder` and
correctly skips all 8 already-generated scenes. With `OPENAI_API_KEY`
unset, `--provider openai_images` fails immediately with a clear
`RuntimeError` rather than a partial/corrupt run. All of this is now
covered by the automated, mocked suite in `tests/` - see "Running the
automated tests" above; all 8 tests pass. A real end-to-end generation
run (actual OpenAI image output, viewed against a scene) is still
pending an active `OPENAI_API_KEY`.

## Out of scope

Only one real provider (`OpenAIImagesProvider`) is connected so far -
FLUX, SDXL, Runway, Veo, Kling, and Pika remain future work. Music/ambient
audio, publishing, and analytics remain out of scope for this agent, same
as elsewhere in this project.
