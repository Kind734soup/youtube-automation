"""Prepares one normalized, self-contained clip per timeline entry: real
narration audio (or silence, if missing) combined with a real visual clip
(or a generated placeholder), at the final resolution/framerate, trimmed
or looped to match the audio's actual duration.

Audio - not the as-yet-ungenerated visuals - is what actually determines
each scene's real length (see the Video Editor Agent's own "duration
precedence" notes), so every prepared clip is sized to the real,
probed duration of its narration audio, not the edit_manifest.json
estimate.
"""

from pathlib import Path

from ffmpeg_render_agent.ffmpeg_utils import probe_duration_seconds, run_ffmpeg
from ffmpeg_render_agent.placeholder_visuals import generate_placeholder_clip

AUDIO_SUBDIR = "assets/audio"
VIDEO_SUBDIR = "assets/video"


def _find_existing(asset_dir, stem):
    matches = sorted(p for p in asset_dir.glob(f"{stem}.*") if ".tmp" not in p.suffixes)
    return matches[0] if matches else None


def _build_audio_track(folder, audio_filenames, fallback_duration, work_dir, index):
    audio_dir = folder / AUDIO_SUBDIR
    resolved = []
    for name in audio_filenames:
        stem = Path(name).stem
        found = _find_existing(audio_dir, stem)
        if found:
            resolved.append(found)

    audio_track_path = work_dir / f"audio_{index:02d}.wav"

    if len(resolved) != len(audio_filenames):
        # One or more narration files are missing - fall back to silence so the
        # scene still renders (with a placeholder visual) instead of aborting.
        run_ffmpeg(
            [
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                "-t", str(fallback_duration),
                "-c:a", "pcm_s16le",
                str(audio_track_path),
            ]
        )
        return audio_track_path, False

    if len(resolved) == 1:
        run_ffmpeg(["-i", str(resolved[0]), "-c:a", "pcm_s16le", str(audio_track_path)])
    else:
        inputs = []
        for path in resolved:
            inputs += ["-i", str(path)]
        concat_inputs = "".join(f"[{i}:a]" for i in range(len(resolved)))
        filter_complex = f"{concat_inputs}concat=n={len(resolved)}:v=0:a=1[a]"
        run_ffmpeg(inputs + ["-filter_complex", filter_complex, "-map", "[a]", "-c:a", "pcm_s16le", str(audio_track_path)])

    return audio_track_path, True


def _build_visual_track(folder, visual_filename, title, duration_seconds, resolution, framerate_fps, work_dir, index, force):
    video_dir = folder / VIDEO_SUBDIR
    video_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(visual_filename).stem

    existing = None if force else _find_existing(video_dir, stem)
    was_placeholder = False

    if existing is None:
        placeholder_path = video_dir / f"{stem}.mp4"
        generate_placeholder_clip(title, duration_seconds, resolution, framerate_fps, placeholder_path)
        source = placeholder_path
        was_placeholder = True
    else:
        source = existing

    normalized_path = work_dir / f"visual_{index:02d}.mp4"
    width, height = resolution.split("x")
    scale_pad = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={framerate_fps}"
    )
    run_ffmpeg(
        [
            "-stream_loop", "-1",
            "-i", str(source),
            "-t", str(duration_seconds),
            "-vf", scale_pad,
            "-an",
            "-pix_fmt", "yuv420p",
            "-c:v", "libx264",
            str(normalized_path),
        ]
    )
    return normalized_path, was_placeholder, source


def prepare_scene_clip(entry, folder, resolution, framerate_fps, work_dir, index, force=False):
    """Build one fully-prepared scene clip (visual + audio, normalized to
    `resolution`/`framerate_fps`) for a single edit_manifest.json timeline
    entry. Returns (clip_path, info) where info describes what was used,
    for render_report.md."""
    folder = Path(folder)
    work_dir = Path(work_dir)

    audio_track, audio_ok = _build_audio_track(
        folder, entry["audio_asset_filenames"], entry["duration_seconds"], work_dir, index
    )
    effective_duration = probe_duration_seconds(audio_track)

    visual_track, was_placeholder, visual_source = _build_visual_track(
        folder, entry["visual_asset_filename"], entry["scene_title"], effective_duration,
        resolution, framerate_fps, work_dir, index, force,
    )

    clip_path = work_dir / f"scene_{index:02d}.mp4"
    run_ffmpeg(
        [
            "-i", str(visual_track),
            "-i", str(audio_track),
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(clip_path),
        ]
    )

    info = {
        "scene_number": entry["scene_number"],
        "scene_title": entry["scene_title"],
        "planned_duration_seconds": entry["duration_seconds"],
        "effective_duration_seconds": round(effective_duration, 2),
        "audio_ok": audio_ok,
        "visual_source": "placeholder (generated)" if was_placeholder else f"existing file ({visual_source.name})",
    }
    return clip_path, info
