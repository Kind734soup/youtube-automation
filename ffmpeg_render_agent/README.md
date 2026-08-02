# FFmpeg Render Agent

Turns a project that has already been through the Video Editor Agent into
an actual, watchable video: `final.mp4`, `subtitles.srt`, and
`render_report.md`. It is a completely separate agent from the Research
Agent (`agent/`), Script Agent (`script_agent/`), Video Production Agent
(`video_production_agent/`), Voice Generation Agent
(`voice_generation_agent/`), and Video Editor Agent
(`video_editor_agent/`) - it does not import from any of them, and does
not modify anything they produce.

This is the agent that finally calls FFmpeg. Everything upstream of it
only ever produced JSON manifests and (for narration) real audio - this
is where a timeline plan turns into a finished video file.

## What it consumes

Four things from a project folder (`scripts/<topic-slug>_<date>/`):

- `edit_manifest.json` - the timeline plan, from the Video Editor Agent
- `<folder>/assets/audio/section_NN.*` - real narration audio, from the
  Voice Generation Agent
- `<folder>/assets/video/<visual_asset_filename>` - real visual clips, if
  they exist yet (they don't, today - see "Placeholder visuals" below)
- Nothing else. It never reads `script.md`, `scene_descriptions.md`,
  `metadata.json`, `production_manifest.json`, or `narration_manifest.json`
  directly - everything it needs from those is already folded into
  `edit_manifest.json`.

## What it produces

Written to `final/<same folder name as the source project>/` (a new
top-level folder, alongside `research/` and `scripts/`):

- **`final.mp4`** - the assembled video: every scene in order, with the
  exact transitions `edit_manifest.json` specified, real narration audio,
  scaled/encoded to the manifest's `final_resolution`/`export_settings`
- **`subtitles.srt`** - every scene's captions, with timing rescaled to
  match the *real* rendered timeline (see "Why captions get rescaled")
- **`render_report.md`** - a plain-English account of what actually
  happened: which scenes had real narration vs. silence, which used real
  visuals vs. generated placeholders, planned vs. actual duration per
  scene, and what got left out (music/ambient cues - see below)

## How it works

1. **`scene_renderer.py`** - for each timeline entry: resolves its real
   narration audio file(s) (concatenating them if the scene was split
   into more than one section by the Voice Generation Agent), probes
   their *real* combined duration, resolves a visual clip (real, if one
   exists at `assets/video/<name>`; otherwise a generated placeholder -
   see below), and combines them into one normalized clip at the
   manifest's resolution/framerate, sized to the narration's real length
   (not the manifest's estimate - see "Duration precedence" in the Video
   Editor Agent's own README for why real audio wins).
2. **`timeline_render.py`** - chains every prepared scene clip together
   with FFmpeg's `xfade`/`acrossfade` filters, using each entry's
   `transition_in`/`transition_out` type and duration exactly as
   specified (a plain fade in from black at the very start, crossfades
   between every scene, a fade to black at the very end), then encodes
   the result with the manifest's `export_settings`.
3. **`subtitles.py`** - builds `subtitles.srt` from every scene's
   captions, and can optionally hard-burn them onto the video.
4. **`render_report.py`** - writes the summary described above.
5. **`renderer.py`** - orchestrates the above and decides where output
   goes; `main.py` wraps it as a CLI.

No LLM is involved anywhere in this agent - everything it needs is
already in `edit_manifest.json`. It only shells out to `ffmpeg`/`ffprobe`.

### Placeholder visuals

The Video Production Agent has no video generation provider connected
yet (see `video_production_agent/providers/`), so there is no real
footage for any scene today. Rather than block on that,
`placeholder_visuals.py` generates a simple, calm placeholder clip per
scene - a solid dark-indigo background with the scene's title drawn on
it - sized to exactly that scene's real narration duration.

Placeholders are written to `assets/video/<visual_asset_filename>` (not
a temp folder) and are picked up as "already there" on the next run, so
re-rendering doesn't regenerate them. The moment a real clip is dropped
at that exact path (once a video provider exists), it's used
automatically instead - nothing else in this agent needs to change.

### Why captions get rescaled

`edit_manifest.json`'s caption timestamps assume each scene lasts exactly
its *planned* `duration_seconds`. Real narration audio essentially never
matches that exactly (Windows SAPI, for instance, speaks noticeably
faster than the 135 words/minute the estimate assumes). If captions were
burned in using the manifest's raw timestamps, they would drift further
out of sync with the narration as the video went on. Instead, every
scene's captions are rescaled to fit inside that scene's *real* duration
and *real* position in the assembled timeline (accounting for crossfade
overlap), so they track the actual audio - verified in testing: a
scene's last caption lands exactly on that scene's real duration, and the
next scene's first caption correctly starts partway through the
crossfade, matching the visual overlap.

### What doesn't get mixed in yet

`edit_manifest.json` carries a `music_cue` and `ambient_sound_cue` per
scene (e.g. "sparse, slow solo harp, no percussion") - but these are
descriptions, not audio files, and no music/ambient asset source is
connected yet. This agent does not invent or source music - it renders
narration only, and `render_report.md` says so explicitly for every run.

## Usage

```
python ffmpeg_render_agent/main.py render --from-script scripts/<topic-slug>_<date>
python ffmpeg_render_agent/main.py render --from-script scripts/<topic-slug>_<date> --burn-subtitles
python ffmpeg_render_agent/main.py render --from-script scripts/<topic-slug>_<date> --force
```

- Default: produces a clean `final.mp4` plus a separate `subtitles.srt`
  (the more flexible choice - YouTube's own caption upload prefers a
  separate file, and it keeps multi-language captioning possible later).
- `--burn-subtitles` hard-burns the captions into `final.mp4` instead.
- If `final.mp4` already exists, a re-run is skipped (not overwritten)
  unless `--force` is passed - matching the same idempotency convention
  as the Voice Generation Agent's `narrate` command. Placeholder visuals
  are skip-if-exists the same way.
- The target folder must already contain `edit_manifest.json` (from the
  Video Editor Agent) and real narration audio under `assets/audio/`
  (from the Voice Generation Agent).

## Setup

Requires FFmpeg (with `ffprobe`) on `PATH` - nothing else. No pip
packages, no API key.

```
winget install Gyan.FFmpeg
```

then restart your shell so `PATH` picks up the change. Verify with
`ffmpeg -version` and `ffprobe -version`.

## Tested against

Built a `production_manifest.json` and `edit_manifest.json` for the
existing Nightfall Atlas Ancient Egypt script (alongside its real,
already-rendered narration audio) and ran a full render:

- All 8 scenes rendered with real narration audio and generated
  placeholder visuals (no failures).
- `final.mp4`: 1920x1080 h264 @ 24fps, mono AAC audio, 1419.17s total -
  which matches exactly: 1433.18s of real narration minus 14s (7
  crossfades x 2s each) lost to overlap.
- Verified the crossfades are real, not just a duration coincidence: sampled
  frames right at a scene boundary and saw both scenes' title cards
  genuinely overlapping mid-transition, then resolving cleanly to the next
  scene.
- Verified caption rescaling: a scene's final caption lands exactly at
  that scene's real duration, and the next scene's first caption starts
  correctly inside the crossfade window.
- `render_report.md` correctly listed all 8 scenes as using placeholder
  visuals and real narration, and noted that music/ambient cues were not
  mixed in.

A full 8-scene, ~24-minutes-of-narration render at 1920x1080 took a few
minutes of wall-clock time on this machine - most of it in the final
crossfade/encode step, which processes the whole assembled video through
one FFmpeg filter graph.

## Out of scope

Publishing and Analytics are not implemented here or anywhere else yet -
this agent's job ends at a finished MP4 sitting in `final/`.
