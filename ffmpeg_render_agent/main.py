"""FFmpeg Render Agent - command line entry point.

Usage:
  python ffmpeg_render_agent/main.py render --from-script scripts/<topic-slug>_<date>
  python ffmpeg_render_agent/main.py render --from-script scripts/<topic-slug>_<date> --burn-subtitles
  python ffmpeg_render_agent/main.py render --from-script scripts/<topic-slug>_<date> --force

Reads edit_manifest.json (from the Video Editor Agent), real narration
audio (assets/audio/, from the Voice Generation Agent), and either real
or generated-placeholder visual assets (assets/video/) to produce
final.mp4, subtitles.srt, and render_report.md under
final/<topic-slug>_<date>/. See README.md.
"""

import argparse

from ffmpeg_render_agent.renderer import render_video


def run_render(folder, burn_subtitles_flag, force):
    print(f"Rendering final video from: {folder}")
    result = render_video(folder, burn_subtitles_flag=burn_subtitles_flag, force=force)

    if result["skipped"]:
        print(f"final.mp4 already exists at {result['final_path']} - skipped (use --force to re-render).")
        return

    print("\nDone.")
    print(f"  final.mp4:        {result['final_path']}")
    print(f"  subtitles.srt:    {result['srt_path']}")
    print(f"  render_report.md: {result['report_path']}")


def main():
    parser = argparse.ArgumentParser(description="Nightfall Atlas FFmpeg Render Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_p = subparsers.add_parser("render", help="Render edit_manifest.json into a finished MP4")
    render_p.add_argument(
        "--from-script",
        required=True,
        help="Path to a project folder with edit_manifest.json, e.g. scripts/<topic-slug>_<date>",
    )
    render_p.add_argument(
        "--burn-subtitles",
        action="store_true",
        help="Hard-burn captions into final.mp4 (default: keep them as a separate .srt only)",
    )
    render_p.add_argument("--force", action="store_true", help="Re-render even if final.mp4 already exists")

    args = parser.parse_args()

    if args.command == "render":
        run_render(args.from_script, args.burn_subtitles, args.force)


if __name__ == "__main__":
    main()
