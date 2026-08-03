"""Publishing Agent - command line entry point.

Usage examples:
  python publishing_agent/main.py prepare --from-script scripts/<topic-slug>_<date>
  python publishing_agent/main.py prepare --from-script scripts/<topic-slug>_<date> --privacy unlisted
  python publishing_agent/main.py prepare --from-script scripts/<topic-slug>_<date> --publish-at 2026-08-10T18:00:00Z
  python publishing_agent/main.py prepare --from-script scripts/<topic-slug>_<date> --force
  python publishing_agent/main.py publish --from-script scripts/<topic-slug>_<date>

Reads final.mp4 and subtitles.srt (from a FFmpeg Render Agent output
folder) plus metadata.json, edit_manifest.json, and
production_manifest.json (from the matching scripts/ folder) to write
upload_manifest.json - see README.md.
"""

import argparse

from publishing_agent.organizer import default_provider_name, prepare_upload_manifest, run_provider


def run_prepare(folder, privacy_status, scheduled_publish_time, playlist, category, force):
    print(f"Preparing upload manifest from: {folder}")
    result = prepare_upload_manifest(
        folder,
        privacy_status=privacy_status,
        scheduled_publish_time=scheduled_publish_time,
        playlist=playlist,
        category=category,
        force=force,
    )

    if result["skipped"]:
        print(f"upload_manifest.json already exists at {result['manifest_path']} - skipped (use --force to rebuild).")
        return

    manifest = result["upload_manifest"]
    print(f"\nDone. upload_manifest.json written to {result['manifest_path']}")
    print(f"  Title:      {manifest['title']}")
    print(f"  Chapters:   {len(manifest['chapters'])}")
    print(f"  Tags:       {len(manifest['tags'])}")
    print(f"  Category:   {manifest['category']['name']}")
    print(f"  Playlist:   {manifest['playlist']}")
    print(f"  Privacy:    {manifest['privacy_status']}")
    print(f"  Thumbnail:  {manifest['thumbnail_path']} ({'found' if manifest['thumbnail_exists'] else 'not found yet'})")


def run_publish(folder, provider_name):
    resolved_provider = provider_name or default_provider_name()
    print(f"Publishing from: {folder}")
    print(f"Publishing provider: {resolved_provider}")
    result = run_provider(folder, provider_name)
    print(f"\nStatus: {result['status']}")


def main():
    parser = argparse.ArgumentParser(description="Nightfall Atlas Publishing Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_p = subparsers.add_parser(
        "prepare", help="Build upload_manifest.json from a project's script and final folders"
    )
    prepare_p.add_argument(
        "--from-script",
        required=True,
        help="Path to a project folder with metadata.json, e.g. scripts/<topic-slug>_<date>",
    )
    prepare_p.add_argument(
        "--privacy",
        default=None,
        choices=["private", "unlisted", "public"],
        help="Privacy status to record (default: unlisted)",
    )
    prepare_p.add_argument(
        "--publish-at",
        default=None,
        help="ISO 8601 scheduled publish time, e.g. 2026-08-10T18:00:00Z (default: none)",
    )
    prepare_p.add_argument(
        "--playlist", default=None, help="Playlist name to record (default: derived from the topic)"
    )
    prepare_p.add_argument(
        "--category", default=None, help="YouTube category name to record (default: derived from the topic)"
    )
    prepare_p.add_argument(
        "--force", action="store_true", help="Rebuild upload_manifest.json even if it already exists"
    )

    publish_p = subparsers.add_parser(
        "publish", help="Run a publishing provider against an existing upload_manifest.json"
    )
    publish_p.add_argument(
        "--from-script",
        required=True,
        help="Path to a project folder with metadata.json, e.g. scripts/<topic-slug>_<date>",
    )
    publish_p.add_argument(
        "--provider", default=None, help="Publishing provider to use (default: PUBLISHING_PROVIDER in .env, or manual)"
    )

    args = parser.parse_args()

    if args.command == "prepare":
        run_prepare(args.from_script, args.privacy, args.publish_at, args.playlist, args.category, args.force)
    elif args.command == "publish":
        run_publish(args.from_script, args.provider)


if __name__ == "__main__":
    main()
