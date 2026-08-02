"""Video Editor Agent - command line entry point.

Usage example:
  python video_editor_agent/main.py build --from-script scripts/<topic-slug>_<date>

Reads production_manifest.json, narration_manifest.json, script.md, and
metadata.json from a project folder and writes edit_manifest.json into
that same folder. Does not require real video clips, audio files, or any
paid API - see README.md.
"""

import argparse

from video_editor_agent.manifest_builder import build_manifest
from video_editor_agent.organizer import save_manifest


def run_build(folder):
    print(f"Building edit manifest from: {folder}")
    print("This calls an LLM once per scene for music/ambient sound design - it may take a few minutes.")
    manifest = build_manifest(folder)
    manifest_path = save_manifest(manifest, folder)
    print(
        f"\nDone. {manifest['scene_count']} scenes, "
        f"~{round(manifest['total_duration_seconds'] / 60, 1)} min total, "
        f"{manifest['final_resolution']} ({manifest['final_aspect_ratio']}). "
        f"Saved to: {manifest_path}"
    )


def main():
    parser = argparse.ArgumentParser(description="Nightfall Atlas Video Editor Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser("build", help="Build edit_manifest.json from a project folder")
    build_p.add_argument(
        "--from-script",
        required=True,
        help="Path to a project folder, e.g. scripts/<topic-slug>_<date>, that already has "
        "production_manifest.json and narration_manifest.json",
    )

    args = parser.parse_args()

    if args.command == "build":
        run_build(args.from_script)


if __name__ == "__main__":
    main()
