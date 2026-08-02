"""Voice Generation Agent - command line entry point.

Usage examples:
  python voice_generation_agent/main.py build --from-script scripts/<topic-slug>_<date>
  python voice_generation_agent/main.py test-first --from-script scripts/<topic-slug>_<date>
  python voice_generation_agent/main.py narrate --from-script scripts/<topic-slug>_<date>

`build` reads script.md and metadata.json and writes narration_manifest.json
(no voice provider involved - see README.md). `test-first` and `narrate`
read an existing narration_manifest.json and render real audio with a
connected VoiceProvider (default: the free, offline windows_sapi provider)
into <folder>/assets/audio/ - `test-first` renders only section 1, to
sanity-check narration/voice settings before rendering the whole story.
"""

import argparse

from voice_generation_agent.manifest_builder import build_manifest
from voice_generation_agent.narrator import default_provider_name, load_narration_manifest, narrate_sections
from voice_generation_agent.organizer import save_manifest


def run_build(folder):
    print(f"Building narration manifest from: {folder}")
    print("This calls an LLM once per section for voice direction - it may take a few minutes.")
    manifest = build_manifest(folder)
    manifest_path = save_manifest(manifest, folder)
    print(
        f"\nDone. {manifest['section_count']} sections, "
        f"~{round(manifest['total_estimated_duration_seconds'] / 60, 1)} min total. "
        f"Saved to: {manifest_path}"
    )


def _run_narrate(folder, provider_name, sections_to_render, label):
    manifest = load_narration_manifest(folder)
    provider_name = provider_name or default_provider_name()
    print(f"Rendering {label} from: {folder}")
    print(f"Voice provider: {provider_name}")

    results = narrate_sections(folder, sections_to_render, provider_name=provider_name)

    for section, result in zip(sections_to_render, results):
        print(
            f"  Section {section['section_number']}: {result['output_path']} "
            f"({result['format']}, {result['duration_seconds']}s)"
        )
    total_seconds = sum(r["duration_seconds"] for r in results if r["duration_seconds"] is not None)
    print(f"\nDone. {len(results)} file(s) written, {round(total_seconds, 1)}s total audio.")


def run_test_first(folder, provider_name):
    manifest = load_narration_manifest(folder)
    first_section = manifest["sections"][0]
    _run_narrate(folder, provider_name, [first_section], "section 1 only (test)")


def run_narrate(folder, provider_name):
    manifest = load_narration_manifest(folder)
    _run_narrate(folder, provider_name, manifest["sections"], f"all {manifest['section_count']} sections")


def main():
    parser = argparse.ArgumentParser(description="Nightfall Atlas Voice Generation Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_p = subparsers.add_parser("build", help="Build narration_manifest.json from a script folder")
    build_p.add_argument(
        "--from-script",
        required=True,
        help="Path to a Script Agent output folder, e.g. scripts/<topic-slug>_<date>",
    )

    test_first_p = subparsers.add_parser(
        "test-first", help="Render only section 1's audio, to sanity-check voice settings"
    )
    test_first_p.add_argument("--from-script", required=True, help="Path to a project folder with narration_manifest.json")
    test_first_p.add_argument(
        "--provider", default=None, help="Voice provider to use (default: VOICE_PROVIDER in .env, or windows_sapi)"
    )

    narrate_p = subparsers.add_parser("narrate", help="Render every section's audio for the whole story")
    narrate_p.add_argument("--from-script", required=True, help="Path to a project folder with narration_manifest.json")
    narrate_p.add_argument(
        "--provider", default=None, help="Voice provider to use (default: VOICE_PROVIDER in .env, or windows_sapi)"
    )

    args = parser.parse_args()

    if args.command == "build":
        run_build(args.from_script)
    elif args.command == "test-first":
        run_test_first(args.from_script, args.provider)
    elif args.command == "narrate":
        run_narrate(args.from_script, args.provider)


if __name__ == "__main__":
    main()
