"""Builds subtitles.srt from edit_manifest.json's captions, and an
optional pass to burn them into the final video.

edit_manifest.json's caption timestamps assume each scene lasts exactly
its *planned* duration_seconds. The real narration audio rarely matches
that exactly (see scene_renderer.py), so caption timing is rescaled here
to each scene's *real* duration and real position in the assembled
timeline - otherwise captions would drift out of sync with the actual
narration over the course of the video.
"""

from pathlib import Path

from ffmpeg_render_agent.ffmpeg_utils import run_ffmpeg


def _compute_real_start_times(durations, boundary_durations):
    starts = [0.0]
    cumulative = durations[0]
    for i in range(1, len(durations)):
        transition = boundary_durations[i - 1]
        offset = cumulative - transition
        starts.append(offset)
        cumulative = cumulative - transition + durations[i]
    return starts


def _format_srt_time(seconds):
    seconds = max(seconds, 0.0)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis -= 1000
        secs += 1
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt(timeline_entries, effective_durations):
    """Return SRT-formatted subtitle text, with every caption's timing
    rescaled from its scene's planned duration to its real one."""
    n = len(timeline_entries)
    boundary_durations = [timeline_entries[i]["transition_out"]["duration_seconds"] for i in range(n - 1)]
    real_starts = _compute_real_start_times(effective_durations, boundary_durations)

    cues = []
    for i, entry in enumerate(timeline_entries):
        planned_duration = entry["duration_seconds"] or 1.0
        real_duration = effective_durations[i]
        scale = real_duration / planned_duration

        for caption in entry["captions"]:
            rel_start = caption["start_time_seconds"] - entry["start_time_seconds"]
            rel_end = caption["end_time_seconds"] - entry["start_time_seconds"]
            cues.append(
                {
                    "text": caption["text"],
                    "start": real_starts[i] + rel_start * scale,
                    "end": real_starts[i] + rel_end * scale,
                }
            )

    lines = []
    for idx, cue in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{_format_srt_time(cue['start'])} --> {_format_srt_time(cue['end'])}")
        lines.append(cue["text"])
        lines.append("")
    return "\n".join(lines)


def save_srt(content, output_path):
    output_path = Path(output_path)
    output_path.write_text(content, encoding="utf-8")
    return output_path


def burn_subtitles(video_path, srt_path, export_settings, output_path):
    """Hard-burn `srt_path` onto `video_path`, writing the result to
    `output_path`. Runs with cwd set to the subtitle file's own folder and
    references it by bare filename, since ffmpeg's `subtitles` filter is
    notoriously fragile about escaping absolute Windows paths (drive-letter
    colons collide with the filter's own argument syntax)."""
    video_path = Path(video_path).resolve()
    srt_path = Path(srt_path).resolve()
    output_path = Path(output_path).resolve()

    run_ffmpeg(
        [
            "-i", str(video_path),
            "-vf", f"subtitles={srt_path.name}",
            "-c:v", export_settings["video_codec"],
            "-c:a", "copy",
            str(output_path),
        ],
        cwd=str(srt_path.parent),
    )
    return output_path
