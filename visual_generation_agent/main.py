"""Visual Generation Agent - command line entry point.

Usage examples:
  python visual_generation_agent/main.py generate --from-script scripts/<topic-slug>_<date>
  python visual_generation_agent/main.py generate --from-script scripts/<topic-slug>_<date> --force
  python visual_generation_agent/main.py generate --from-script scripts/<topic-slug>_<date> --publish

Reads production_manifest.json and metadata.json from a Video Production
Agent output folder and writes one still image per scene to
<folder>/assets/visuals/scene_NN.png - see README.md.
"""

import argparse

from visual_generation_agent.organizer import default_provider_name, generate_scene_visuals


def run_generate(folder, provider_name, force, publish):
    provider_name = provider_name or default_provider_name()
    print(f"Generating scene visuals from: {folder}")
    print(f"Visual provider: {provider_name}")

    results = generate_scene_visuals(folder, provider_name=provider_name, force=force, publish=publish)

    generated, skipped = 0, 0
    for result in results:
        status = "skipped (already exists)" if result["skipped"] else "generated"
        generated += 0 if result["skipped"] else 1
        skipped += 1 if result["skipped"] else 0
        line = f"  Scene {result['scene_number']:02d}: {result['output_path']} - {status}"
        if "published_path" in result:
            line += f" -> published to {result['published_path']}"
        print(line)

    print(
        f"\nDone. {len(results)} scene(s) total - {generated} generated, {skipped} already existed "
        "and were left alone."
    )


def main():
    parser = argparse.ArgumentParser(description="Nightfall Atlas Visual Generation Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_p = subparsers.add_parser("generate", help="Generate one image per scene from production_manifest.json")
    generate_p.add_argument(
        "--from-script",
        required=True,
        help="Path to a project folder with production_manifest.json and metadata.json",
    )
    generate_p.add_argument(
        "--provider", default=None, help="Visual provider to use (default: VISUAL_PROVIDER in .env, or placeholder)"
    )
    generate_p.add_argument(
        "--force", action="store_true", help="Regenerate every scene's image even if it already exists"
    )
    generate_p.add_argument(
        "--publish",
        action="store_true",
        help=(
            "Also copy each generated image into assets/video/scene_NN.png - the path the FFmpeg "
            "Render Agent already reads real visual assets from, so a render picks these up instead "
            "of its own fallback title cards"
        ),
    )

    args = parser.parse_args()

    if args.command == "generate":
        run_generate(args.from_script, args.provider, args.force, args.publish)


if __name__ == "__main__":
    main()
