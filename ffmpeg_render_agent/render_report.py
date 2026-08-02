"""Builds render_report.md - a human-readable account of what a render
actually did: which scenes had real narration vs. silence, which used
real visuals vs. generated placeholders, and what got left out (music
and ambient cues, since no audio source for those is connected yet).
"""

from datetime import datetime


def build_report(manifest, scene_infos, final_path, srt_path, burned_subtitles):
    lines = [
        f"# Render Report: {manifest['topic']}",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        f"- Scenes: {len(scene_infos)}",
        f"- Output: `{final_path}`",
        f"- Subtitles: `{srt_path}` "
        f"({'burned into final.mp4' if burned_subtitles else 'separate file, not burned in'})",
        f"- Resolution: {manifest['final_resolution']} ({manifest['final_aspect_ratio']}) "
        f"@ {manifest['framerate_fps']}fps",
        "",
        "## Scenes",
        "",
        "| # | Title | Planned (s) | Actual (s) | Narration | Visual |",
        "|---|---|---|---|---|---|",
    ]
    for info in scene_infos:
        narration = "OK" if info["audio_ok"] else "MISSING - silent placeholder used"
        lines.append(
            f"| {info['scene_number']} | {info['scene_title']} | {info['planned_duration_seconds']} | "
            f"{info['effective_duration_seconds']} | {narration} | {info['visual_source']} |"
        )

    total_planned = sum(i["planned_duration_seconds"] for i in scene_infos)
    total_actual = sum(i["effective_duration_seconds"] for i in scene_infos)
    missing = [i for i in scene_infos if not i["audio_ok"]]
    placeholders = [i for i in scene_infos if "placeholder" in i["visual_source"]]

    lines += [
        "",
        f"**Total planned duration:** {round(total_planned, 1)}s ({round(total_planned / 60, 1)} min)",
        f"**Total actual narration duration (before crossfades shrink the assembled total slightly):** "
        f"{round(total_actual, 1)}s ({round(total_actual / 60, 1)} min)",
        "",
        "## Notes",
        "",
    ]
    if missing:
        lines.append(
            f"- {len(missing)} section(s) had no narration audio file and were rendered with silence: "
            + ", ".join(str(i["scene_number"]) for i in missing)
        )
    else:
        lines.append("- All scenes had real narration audio.")

    if placeholders:
        lines.append(
            f"- {len(placeholders)} scene(s) used a generated placeholder visual (no video generation "
            "provider is connected yet - see video_production_agent/providers/): "
            + ", ".join(str(i["scene_number"]) for i in placeholders)
        )
    else:
        lines.append("- All scenes used existing visual asset files.")

    lines.append(
        "- Music/ambient sound cues from edit_manifest.json (`music_cue`, `ambient_sound_cue`) are "
        "descriptive text only - no music/ambient audio asset source is connected yet, so they were not "
        "mixed into this render."
    )

    return "\n".join(lines)
