"""Manual ChatGPT image workflow for the Visual Generation Agent.

A third, completely separate way to fill `assets/visuals/scene_NN.png` -
alongside the automated `placeholder` and `openai_images` VisualProvider
implementations (see `providers/`), for when a human wants to generate
images by hand in the ChatGPT web UI instead of running an API-backed
provider. This module does not implement the VisualProvider interface
and is never selected via VISUAL_PROVIDER - it is invoked directly, and
it does not import from or modify anything in `providers/`.

Three-step human workflow:

1. `export-prompts` - reads production_manifest.json/metadata.json (the
   same read-only manifest_reader.py every provider uses) and writes one
   Markdown prompt file per scene to <folder>/manual_image_prompts/
   (scene_01_prompt.md, scene_02_prompt.md, ...). Each file has a single
   paste-ready prompt plus a human-readable breakdown (style, composition,
   lighting, mood, historical accuracy notes, what to avoid).
2. A human pastes each scene's prompt into ChatGPT, generates an image,
   downloads it, and saves it as <folder>/manual_image_prompts/scene_NN.png
   (exact filename - see each prompt file's "Save the generated image as"
   line).
3. `validate` checks what's been downloaded so far (present scenes only -
   partial progress, e.g. just Scene 1, is expected and not an error);
   `import` copies whatever currently validates cleanly into
   <folder>/assets/visuals/scene_NN.png - the same canonical output
   location every VisualProvider already writes to, so the FFmpeg Render
   Agent and everything downstream needs no changes. Any pre-existing
   file at that path is moved aside into
   assets/visuals/_pre_manual_import/ rather than overwritten, matching
   the same never-delete convention organizer.py already uses for
   assets/video/_pre_visual_generation_agent/.

No API calls of any kind happen anywhere in this module.
"""

import argparse
import shutil
import subprocess
from pathlib import Path

from visual_generation_agent.ffmpeg_utils import ffmpeg_path
from visual_generation_agent.manifest_reader import load_scenes

PROMPTS_SUBDIR = Path("manual_image_prompts")
VISUALS_SUBDIR = Path("assets") / "visuals"
BACKUP_SUBDIR_NAME = "_pre_manual_import"
EXPECTED_RESOLUTION = "1920x1080"

STYLE_GUIDANCE = (
    "Nightfall Atlas house style: cinematic painterly realism (not photoreal, "
    "not cartoon/anime) - soft brushwork, gentle color grading, dark ambient "
    "sleep-story mood. Calm and spacious, never busy or cluttered. Frame for "
    "a 16:9 landscape video still (this project's final render resolution is "
    "1920x1080)."
)


def _historical_accuracy_notes(scene, topic):
    characters = scene.get("characters") or []
    lines = [
        f"This scene is part of \"{topic}\". Keep architecture, materials, tools, "
        f"clothing, and cultural details consistent with the real historical/"
        f"mythological setting implied by the scene description below, not a "
        f"generic fantasy version of it.",
        "Avoid modern anachronisms (contemporary clothing, modern structures, "
        "visible modern technology, modern text of any kind) unless the story "
        "explicitly calls for them.",
    ]
    if characters:
        joined = ", ".join(characters)
        lines.append(
            f"Figure(s) present ({joined}): use traditional, well-documented "
            "iconography for this setting rather than a generic fantasy "
            "reinterpretation - but keep faces soft-focus/obscured/silhouetted "
            "per the \"what to avoid\" note below."
        )
    return " ".join(lines)


def _what_to_avoid(scene):
    return (
        "No on-screen text, watermarks, logos, or UI elements. No visible "
        "detailed human faces in close-up (soft-focus, silhouette, or "
        "obscured only - this is a calming sleep-story channel, not a "
        "portrait). No violence, danger, jump-scare framing, or tense/"
        "unsettling imagery - nothing in this channel's stories is meant to "
        "startle. No modern anachronisms (see historical accuracy notes "
        "above). No visual clutter that fights the scene's stated mood of "
        f"\"{scene.get('mood', 'calm')}\" - keep it spacious and uncluttered."
    )


def _composition(scene):
    parts = []
    if scene.get("recommended_shot_type"):
        parts.append(f"Shot type: {scene['recommended_shot_type']}.")
    if scene.get("camera_movement"):
        parts.append(
            f"This still should read as one frame from: {scene['camera_movement']}."
        )
    parts.append(
        f"Aspect ratio: {scene.get('recommended_aspect_ratio', '16:9')} landscape."
    )
    return " ".join(parts)


def _full_prompt(scene, topic):
    parts = [scene["visual_prompt"]]
    if scene.get("environment"):
        parts.append(f"Setting: {scene['environment']}.")
    if scene.get("lighting"):
        parts.append(f"Lighting: {scene['lighting']}.")
    if scene.get("mood"):
        parts.append(f"Mood: {scene['mood']}.")
    if scene.get("camera_movement"):
        parts.append(f"Framing implied by camera movement: {scene['camera_movement']}.")
    parts.append(
        "Cinematic painterly realism, soft and calming, dark ambient sleep-story "
        "mood, historically/culturally accurate to the setting, no anachronisms. "
        "No text, no watermark, no logos, no visible human faces in close-up. "
        "16:9 landscape composition."
    )
    return " ".join(parts)


def _prompt_markdown(scene, topic):
    scene_number = scene["scene_number"]
    stem = f"scene_{scene_number:02d}"
    lines = [
        f"# Scene {scene_number} - {scene['title']}",
        "",
        f"**Scene number:** {scene_number}",
        f"**Save the generated image as:** `{stem}.png`",
        f"**Save it into:** `manual_image_prompts/{stem}.png` (this folder) - "
        f"run the `import` command afterward to validate it and copy it into "
        f"`assets/visuals/{stem}.png`.",
        "",
        "## Full image-generation prompt",
        "",
        "Paste everything in the box below into ChatGPT as one message:",
        "",
        "```",
        _full_prompt(scene, topic),
        "```",
        "",
        "## Style guidance",
        "",
        STYLE_GUIDANCE,
        "",
        "## Composition",
        "",
        _composition(scene),
        "",
        "## Lighting",
        "",
        scene.get("lighting", "(none specified)"),
        "",
        "## Mood",
        "",
        scene.get("mood", "(none specified)")
        + (f" Continuity: {scene['continuity_notes']}" if scene.get("continuity_notes") else ""),
        "",
        "## Historical accuracy notes",
        "",
        _historical_accuracy_notes(scene, topic),
        "",
        "## What to avoid",
        "",
        _what_to_avoid(scene),
        "",
    ]
    return "\n".join(lines)


def export_prompts(folder, force=False):
    """Write manual_image_prompts/scene_NN_prompt.md for every scene in
    production_manifest.json. Returns one result dict per scene."""
    folder = Path(folder)
    scenes, metadata = load_scenes(folder)
    topic = metadata.get("topic", "")

    prompts_dir = folder / PROMPTS_SUBDIR
    prompts_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for scene in scenes:
        stem = f"scene_{scene['scene_number']:02d}"
        prompt_path = prompts_dir / f"{stem}_prompt.md"

        if prompt_path.exists() and not force:
            results.append(
                {"scene_number": scene["scene_number"], "path": str(prompt_path), "skipped": True}
            )
            continue

        prompt_path.write_text(_prompt_markdown(scene, topic), encoding="utf-8")
        results.append(
            {"scene_number": scene["scene_number"], "path": str(prompt_path), "skipped": False}
        )

    return results


def _ffprobe_path():
    """Locate ffprobe the same way ffmpeg_utils locates ffmpeg - it ships
    alongside ffmpeg.exe in the same bin directory."""
    found = shutil.which("ffprobe")
    if found:
        return found
    candidate = Path(ffmpeg_path()).with_name("ffprobe.exe")
    if candidate.exists():
        return str(candidate)
    raise RuntimeError("ffprobe not found (expected alongside ffmpeg on PATH).")


def _probe_image(path):
    """Return (is_valid_png, resolution_str_or_None) for `path` without
    raising - ffprobe failures just mean "not a valid image"."""
    result = subprocess.run(
        [
            _ffprobe_path(), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height", "-of", "csv=s=x:p=0", str(path),
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return False, None

    fields = result.stdout.strip().split("x")
    if len(fields) != 3:
        return False, None
    codec_name, width, height = fields
    is_png = codec_name.strip().lower() == "png"
    resolution = f"{width}x{height}"
    return is_png, resolution


def validate_downloads(folder):
    """Check manual_image_prompts/scene_NN.png for every scene in
    production_manifest.json. Returns one result dict per scene:
    {scene_number, filename, exists, valid_png, resolution, ok, error}.
    A missing file is reported (not yet downloaded) but is not itself an
    exception - partial progress (e.g. only Scene 1) is expected."""
    folder = Path(folder)
    scenes, _metadata = load_scenes(folder)
    prompts_dir = folder / PROMPTS_SUBDIR

    results = []
    for scene in scenes:
        stem = f"scene_{scene['scene_number']:02d}"
        filename = f"{stem}.png"
        image_path = prompts_dir / filename

        if not image_path.exists():
            results.append(
                {
                    "scene_number": scene["scene_number"],
                    "filename": filename,
                    "exists": False,
                    "valid_png": False,
                    "resolution": None,
                    "ok": False,
                    "error": "not downloaded yet",
                }
            )
            continue

        is_png, resolution = _probe_image(image_path)
        if not is_png:
            results.append(
                {
                    "scene_number": scene["scene_number"],
                    "filename": filename,
                    "exists": True,
                    "valid_png": False,
                    "resolution": resolution,
                    "ok": False,
                    "error": "not a valid PNG file",
                }
            )
            continue

        if resolution != EXPECTED_RESOLUTION:
            results.append(
                {
                    "scene_number": scene["scene_number"],
                    "filename": filename,
                    "exists": True,
                    "valid_png": True,
                    "resolution": resolution,
                    "ok": False,
                    "error": f"resolution is {resolution}, expected {EXPECTED_RESOLUTION}",
                }
            )
            continue

        results.append(
            {
                "scene_number": scene["scene_number"],
                "filename": filename,
                "exists": True,
                "valid_png": True,
                "resolution": resolution,
                "ok": True,
                "error": None,
            }
        )

    return results


def _backup_existing(visuals_dir, target_path):
    if not target_path.exists():
        return
    backup_dir = visuals_dir / BACKUP_SUBDIR_NAME
    backup_dir.mkdir(parents=True, exist_ok=True)
    destination = backup_dir / target_path.name
    if destination.exists():
        destination.unlink()
    target_path.replace(destination)


def import_images(folder):
    """Copy every scene that currently validates cleanly (see
    validate_downloads) from manual_image_prompts/ into
    assets/visuals/scene_NN.png. Scenes not yet downloaded are skipped,
    not errored - this is the mechanism that lets a partial set (e.g.
    just Scene 1) be imported while the rest are still being generated.
    Any pre-existing file at the destination is moved aside into
    assets/visuals/_pre_manual_import/ rather than overwritten."""
    folder = Path(folder)
    validation = validate_downloads(folder)

    prompts_dir = folder / PROMPTS_SUBDIR
    visuals_dir = folder / VISUALS_SUBDIR
    visuals_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for entry in validation:
        if not entry["exists"]:
            results.append({**entry, "imported": False, "reason": "not downloaded yet"})
            continue
        if not entry["ok"]:
            results.append({**entry, "imported": False, "reason": entry["error"]})
            continue

        source_path = prompts_dir / entry["filename"]
        target_path = visuals_dir / entry["filename"]
        _backup_existing(visuals_dir, target_path)
        shutil.copyfile(source_path, target_path)
        results.append({**entry, "imported": True, "reason": None, "target_path": str(target_path)})

    return results


def _print_validation_report(results):
    print(f"{'Scene':<7}{'Filename':<16}{'Status':<12}{'Resolution':<14}Detail")
    for r in results:
        status = "OK" if r["ok"] else ("MISSING" if not r["exists"] else "INVALID")
        print(
            f"{r['scene_number']:<7}{r['filename']:<16}{status:<12}"
            f"{r['resolution'] or '-':<14}{r['error'] or ''}"
        )


def main():
    parser = argparse.ArgumentParser(description="Manual ChatGPT image workflow (Visual Generation Agent)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    export_p = subparsers.add_parser("export-prompts", help="Write one prompt .md per scene")
    export_p.add_argument("--from-script", required=True, help="Path to a project folder with production_manifest.json")
    export_p.add_argument("--force", action="store_true", help="Regenerate every prompt file even if it already exists")

    validate_p = subparsers.add_parser("validate", help="Check manual_image_prompts/ for downloaded scene images")
    validate_p.add_argument("--from-script", required=True, help="Path to the project folder")

    import_p = subparsers.add_parser("import", help="Copy validated images into assets/visuals/")
    import_p.add_argument("--from-script", required=True, help="Path to the project folder")

    args = parser.parse_args()

    if args.command == "export-prompts":
        results = export_prompts(args.from_script, force=args.force)
        for r in results:
            status = "skipped (already exists)" if r["skipped"] else "written"
            print(f"  Scene {r['scene_number']:02d}: {r['path']} - {status}")
        print(f"\nDone. {len(results)} prompt file(s).")

    elif args.command == "validate":
        results = validate_downloads(args.from_script)
        _print_validation_report(results)
        ready = sum(1 for r in results if r["ok"])
        print(f"\n{ready}/{len(results)} scene(s) ready to import.")

    elif args.command == "import":
        results = import_images(args.from_script)
        for r in results:
            if r["imported"]:
                print(f"  Scene {r['scene_number']:02d}: imported -> {r['target_path']}")
            else:
                print(f"  Scene {r['scene_number']:02d}: skipped ({r['reason']})")
        imported = sum(1 for r in results if r["imported"])
        print(f"\nDone. {imported}/{len(results)} scene(s) imported.")


if __name__ == "__main__":
    main()
