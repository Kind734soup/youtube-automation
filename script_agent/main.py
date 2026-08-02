"""Script Agent - command line entry point.

Usage examples:
  Write from a manual topic:
    python script_agent/main.py write --topic "A lighthouse keeper's quiet night watch" --minutes 35

  Write from a Research Agent result (picks the Nth idea from that folder's ideas.csv,
  ranked #1 = highest view velocity):
    python script_agent/main.py write --from-research research/ideas/sleep-stories_2026-08-01 --pick 1
"""

import argparse
import csv
from pathlib import Path

from script_agent.organizer import save_script
from script_agent.script_writer import write_script


def _topic_from_research(folder, pick):
    csv_path = Path(folder) / "ideas.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"No ideas.csv found in {folder}")

    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if pick < 1 or pick > len(rows):
        raise ValueError(f"--pick must be between 1 and {len(rows)} for this folder")

    return rows[pick - 1]["title"]


def run_write(topic, minutes):
    print(f"Writing a ~{minutes}-minute Nightfall Atlas script for: {topic!r}")
    print("This calls Claude multiple times (outline + each scene) - it may take a few minutes.")
    result = write_script(topic, target_minutes=minutes)
    folder = save_script(result)
    print(f"\nDone. {result['word_count']} words (~{result['estimated_minutes']} min). Saved to: {folder}")


def main():
    parser = argparse.ArgumentParser(description="Nightfall Atlas Script Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_p = subparsers.add_parser("write", help="Generate a sleep story script")
    write_p.add_argument("--topic", help="Manual topic to write about")
    write_p.add_argument(
        "--from-research", help="Path to a Research Agent ideas folder, e.g. research/ideas/<topic>_<date>"
    )
    write_p.add_argument(
        "--pick", type=int, default=1, help="Which ranked idea to use from --from-research (default: 1)"
    )
    write_p.add_argument("--minutes", type=int, default=35, help="Target runtime in minutes (30-45 recommended)")

    args = parser.parse_args()

    if args.command == "write":
        if args.topic and args.from_research:
            parser.error("Use either --topic or --from-research, not both")
        if not args.topic and not args.from_research:
            parser.error("Provide --topic or --from-research")

        topic = args.topic or _topic_from_research(args.from_research, args.pick)
        run_write(topic, args.minutes)


if __name__ == "__main__":
    main()
