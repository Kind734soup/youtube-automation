"""Chains prepared per-scene clips (see scene_renderer.py) into one
assembled video, applying the exact transitions specified in
edit_manifest.json: a fade in from black at the very start, crossfades
(xfade/acrossfade) between every scene, and a fade to black at the very
end.

xfade needs each transition's position ("offset") in the running,
already-overlapping timeline, not just its duration - that offset is
computed here from each clip's own real (ffprobe'd) duration, not the
manifest's estimate, since scene_renderer.py already resized every clip
to its narration's real length.
"""

from ffmpeg_render_agent.ffmpeg_utils import probe_duration_seconds, run_ffmpeg

TRANSITION_XFADE_STYLE = "fade"  # ffmpeg xfade transition name for a plain crossfade/dissolve


def assemble_timeline(clip_paths, timeline_entries, export_settings, output_path):
    """Concatenate `clip_paths` (one prepared clip per timeline entry, same
    order) using the transition_in/transition_out durations from
    `timeline_entries`, encode with `export_settings`, and write the
    result to `output_path`. Returns the total assembled duration in
    seconds."""
    durations = [probe_duration_seconds(p) for p in clip_paths]
    n = len(clip_paths)

    fade_in_duration = timeline_entries[0]["transition_in"]["duration_seconds"]
    fade_out_duration = timeline_entries[-1]["transition_out"]["duration_seconds"]
    # Interior boundary durations: scene i's transition_out (== scene i+1's transition_in
    # by construction in the Video Editor Agent's timeline_builder.py).
    boundary_durations = [timeline_entries[i]["transition_out"]["duration_seconds"] for i in range(n - 1)]

    video_parts = [f"[0:v]fade=t=in:st=0:d={fade_in_duration}[v0f]"]
    audio_parts = [f"[0:a]afade=t=in:st=0:d={fade_in_duration}[a0f]"]

    running_v, running_a = "v0f", "a0f"
    cumulative = durations[0]
    for i in range(1, n):
        transition_duration = boundary_durations[i - 1]
        offset = cumulative - transition_duration
        next_v, next_a = f"vx{i}", f"ax{i}"

        video_parts.append(
            f"[{running_v}][{i}:v]xfade=transition={TRANSITION_XFADE_STYLE}:"
            f"duration={transition_duration}:offset={offset}[{next_v}]"
        )
        audio_parts.append(f"[{running_a}][{i}:a]acrossfade=d={transition_duration}[{next_a}]")

        cumulative = cumulative - transition_duration + durations[i]
        running_v, running_a = next_v, next_a

    fade_out_start = cumulative - fade_out_duration
    video_parts.append(f"[{running_v}]fade=t=out:st={fade_out_start}:d={fade_out_duration}[vout]")
    audio_parts.append(f"[{running_a}]afade=t=out:st={fade_out_start}:d={fade_out_duration}[aout]")

    filter_complex = ";".join(video_parts + audio_parts)

    args = []
    for path in clip_paths:
        args += ["-i", str(path)]
    args += [
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", export_settings["video_codec"],
        "-c:a", export_settings["audio_codec"],
        "-b:v", export_settings["video_bitrate"],
        "-b:a", export_settings["audio_bitrate"],
        "-r", str(export_settings["framerate_fps"]),
        "-pix_fmt", export_settings["pixel_format"],
        str(output_path),
    ]
    run_ffmpeg(args)

    return round(cumulative, 2)
