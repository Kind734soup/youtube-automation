"""Video Production Agent - command line entry point.

Usage example:
  python video_production_agent/main.py build --from-script scripts/<topic-slug>_<date>

Reads script.md, scene_descriptions.md, and metadata.json from a Script
Agent output folder and writes production_manifest.json into that same
folder. Does not call any video generation API - see README.md.
"""

import argparse

from video_production_agent.manifest_builder import build_manifest
from video_production_agent.organizer import save_manifest


def run_build(folder):
    print(f"Building production manifest from: {folder}")
    print("This calls an LLM once per scene to structure the shot plan - it may take a few minutes.")
    manifest = build_manifest(folder)
    manifest_path = save_manifest(manifest, folder)
    print(
        f"\nDone. {manifest['scene_count']} scenes, "
        f"~{round(manifest['total_estimated_duration_seconds'] / 60, 1)} min total. "
        f"Saved to: {manifest_path}"
    )


def main():
    parser = argparse.ArgumentParser(description="Nightfall Atlas Video Production Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser("build", help="Build production_manifest.json from a script folder")
    build_p.add_argument(
        "--from-script",
        required=True,
        help="Path to a Script Agent output folder, e.g. scripts/<topic-slug>_<date>",
    )

    args = parser.parse_args()

    if args.command == "build":
        run_build(args.from_script)


if __name__ == "__main__":
    main()
