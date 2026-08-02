"""YouTube Research Agent - command line entry point.

Usage examples:
  python main.py ideas "beginner sourdough bread"
  python main.py competitor "@JoshuaWeissman"
  python main.py full "beginner sourdough bread" --competitors "@JoshuaWeissman" "@BrianLagerstrom"
"""

import argparse

from agent.competitor_analyzer import analyze_competitor
from agent.idea_finder import find_video_ideas
from agent.organizer import save_competitor, save_ideas


def run_ideas(topic, max_results):
    print(f"Searching YouTube for video ideas on: {topic!r} ...")
    ideas = find_video_ideas(topic, max_results=max_results)
    if not ideas:
        print("No results found. Try a different topic.")
        return
    folder = save_ideas(topic, ideas)
    print(f"Found {len(ideas)} ideas. Saved to: {folder}\n")
    print("Top 5 by view velocity (views/day):")
    for idea in ideas[:5]:
        print(f"  - {idea['title'][:70]}  ({idea['views_per_day']:,}/day)")


def run_competitor(channel, max_videos):
    print(f"Analyzing competitor channel: {channel!r} ...")
    data = analyze_competitor(channel, max_videos=max_videos)
    c = data["channel"]

    if c["subscribers"] < 1000:
        print(
            f"WARNING: resolved to '{c['title']}' which has only "
            f"{c['subscribers']:,} subscribers. This might be the wrong "
            f"channel (handles are exact - check for typos, hyphens, or "
            f"copy the handle straight from the channel's YouTube URL)."
        )

    folder = save_competitor(data)
    print(f"Saved to: {folder}\n")
    print(f"{c['title']} — {c['subscribers']:,} subscribers")
    print(f"Avg views (recent uploads): {data['avg_views_recent']:,}")
    print(f"Avg engagement rate: {data['avg_engagement_rate']}%")
    print("Top recent video:", data["top_videos"][0]["title"])


def run_full(topic, competitors, max_results):
    run_ideas(topic, max_results)
    for channel in competitors:
        print()
        run_competitor(channel, max_results)


def main():
    parser = argparse.ArgumentParser(description="YouTube Research Agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ideas_p = subparsers.add_parser("ideas", help="Find video ideas for a topic")
    ideas_p.add_argument("topic", help="Topic or keyword to research")
    ideas_p.add_argument("--max", type=int, default=25, help="Max results to fetch")

    comp_p = subparsers.add_parser("competitor", help="Analyze a competitor channel")
    comp_p.add_argument("channel", help="Channel @handle, name, or URL")
    comp_p.add_argument("--max", type=int, default=15, help="Max recent videos to analyze")

    full_p = subparsers.add_parser("full", help="Find ideas AND analyze competitors")
    full_p.add_argument("topic", help="Topic or keyword to research")
    full_p.add_argument(
        "--competitors", nargs="+", required=True, help="One or more channel handles"
    )
    full_p.add_argument("--max", type=int, default=25, help="Max results to fetch")

    args = parser.parse_args()

    if args.command == "ideas":
        run_ideas(args.topic, args.max)
    elif args.command == "competitor":
        run_competitor(args.channel, args.max)
    elif args.command == "full":
        run_full(args.topic, args.competitors, args.max)


if __name__ == "__main__":
    main()
