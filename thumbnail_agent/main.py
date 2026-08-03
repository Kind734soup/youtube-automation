"""Thumbnail Agent - command line entry point.

Usage examples:
  python thumbnail_agent/main.py generate --from-script scripts/<topic-slug>_<date>
  python thumbnail_agent/main.py generate --from-script scripts/<topic-slug>_<date> --force
  python thumbnail_agent/main.py generate --from-script scripts/<topic-slug>_<date> --provider manual

Reads metadata.json, script.md, and production_manifest.json (plus any
existing assets/visuals/ scene images) from a Script Agent output
folder, generates 3 ranked thumbnail concepts via an LLM, and writes
thumbnail_prompt.md and thumbnail_manifest.json into the matching
final/ folder - see README.md.
"""

import argparse

from thumbnail_agent.organizer import default_provider_name, generate_thumbnail_package


def run_generate(folder, provider_name, force):
    provider_name = provider_name or default_provider_name()
    print(f"Generating thumbnail concepts from: {folder}")
    print(f"Thumbnail LLM provider: {provider_name}")

    result = generate_thumbnail_package(folder, provider_name=provider_name, force=force)

    if result["skipped"]:
        print(
            f"\n{result['manifest_path'].name} already exists at {result['manifest_path']} "
            "- skipped (use --force to rebuild)."
        )
        return

    manifest = result["thumbnail_manifest"]
    print(f"\nDone. Wrote:")
    print(f"  {result['prompt_md_path']}")
    print(f"  {result['manifest_path']}")
    print(f"\nRecommended concept: {manifest['recommended_concept']} (rank {manifest['recommended_rank']})")
    print(f"Thumbnail will belong at: {manifest['thumbnail_path']} "
          f"({'found' if manifest['thumbnail_exists'] else 'not found yet'})")

    if result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print(f"  - {warning}")


def main():
    parser = argparse.ArgumentParser(description="Nightfall Atlas Thumbnail Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_p = subparsers.add_parser(
        "generate", help="Generate 3 ranked thumbnail concepts and a recommended image prompt"
    )
    generate_p.add_argument(
        "--from-script",
        required=True,
        help="Path to a project folder with metadata.json, script.md, and production_manifest.json, "
        "e.g. scripts/<topic-slug>_<date>",
    )
    generate_p.add_argument(
        "--provider",
        default=None,
        help="Thumbnail LLM provider to use (default: THUMBNAIL_LLM_PROVIDER in .env, or manual)",
    )
    generate_p.add_argument(
        "--force", action="store_true", help="Regenerate thumbnail_manifest.json even if it already exists"
    )

    args = parser.parse_args()

    if args.command == "generate":
        run_generate(args.from_script, args.provider, args.force)


if __name__ == "__main__":
    main()
