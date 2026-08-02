"""Where the real FFmpeg assembly step will live once actual video clips
and narration audio exist.

Nothing in this project shells out to FFmpeg yet: production_manifest.json
comes from the Video Production Agent, which has no video generation
provider connected, and narration_manifest.json comes from the Voice
Generation Agent, which has no TTS provider connected either. Both only
exist as manifests right now, so there's nothing to assemble yet - see
each agent's providers/ folder.

Planned flow, once real files exist in an assets folder next to
edit_manifest.json (named exactly per each timeline entry's
visual_asset_filename / audio_asset_filenames):

  1. For each timeline entry, take its visual clip and concatenate its
     audio_asset_filenames (usually one, occasionally more - see
     narration_section_numbers) into that entry's narration track.
  2. Chain entries together in timeline order using FFmpeg's `xfade`
     filter for video and `acrossfade` for audio, using each entry's
     transition_in / transition_out "type" and "duration_seconds".
  3. Mix in music_cue and ambient_sound_cue as additional audio inputs
     (once real music/ambience files are chosen for each cue), each
     scaled with a `volume` filter from that entry's volume_levels_db,
     and fading in/out with the same durations as the visual transitions.
  4. Turn each entry's captions into either burned-in `drawtext` filters
     or a sidecar .srt/.vtt file - the cue text and
     start_time_seconds/end_time_seconds are already computed.
  5. Scale/pad everything to final_resolution and encode using
     export_settings (container, video_codec, audio_codec, bitrates,
     framerate, pixel_format) - the whole dict maps almost directly onto
     ffmpeg's own output flags.

Every value that step needs is already in edit_manifest.json - this
function's job, once it's implemented, is only to translate that data
into an ffmpeg command / filter graph and run it. See README.md,
"Assembling the final video (future work)".
"""


def assemble_video(edit_manifest, assets_dir, output_path):
    """Build and run the ffmpeg command described by `edit_manifest`, using
    real asset files from `assets_dir`, writing the final video to
    `output_path`.

    Not implemented yet - there are no real video/audio assets to assemble
    until video_production_agent and voice_generation_agent each have a
    connected provider. Once assets_dir contains real files matching
    edit_manifest.json's visual_asset_filename / audio_asset_filenames,
    implement the ffmpeg command described in this module's docstring here.
    """
    raise NotImplementedError(
        "No real video/audio assets exist yet - video_production_agent and "
        "voice_generation_agent don't have a connected provider yet. Once "
        f"'{assets_dir}' contains real files matching edit_manifest.json's "
        "visual_asset_filename / audio_asset_filenames, implement the ffmpeg "
        "command described in this module's docstring here."
    )
