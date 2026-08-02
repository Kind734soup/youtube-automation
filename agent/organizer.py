"""Saves research results into organized folders under research/.

Layout:
  research/
    ideas/
      <topic-slug>_<date>/
        ideas.csv
        ideas.md
    competitors/
      <channel-slug>_<date>/
        overview.md
        videos.csv

Every run gets its own dated folder, so nothing overwrites previous research.
"""

import csv
import re
from datetime import date
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent.parent / "research"


def _slugify(text):
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "untitled"


def save_ideas(topic, ideas):
    """Save video ideas for a topic. Returns the folder path they were saved to."""
    folder = RESEARCH_DIR / "ideas" / f"{_slugify(topic)}_{date.today()}"
    folder.mkdir(parents=True, exist_ok=True)

    csv_path = folder / "ideas.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "channel",
                "views",
                "views_per_day",
                "age_days",
                "likes",
                "comments",
                "url",
            ],
        )
        writer.writeheader()
        for idea in ideas:
            writer.writerow({k: idea[k] for k in writer.fieldnames})

    md_path = folder / "ideas.md"
    lines = [f"# Video Ideas: {topic}", f"_Generated {date.today()}_", ""]
    for i, idea in enumerate(ideas, start=1):
        lines.append(f"## {i}. {idea['title']}")
        lines.append(
            f"- Channel: {idea['channel']}\n"
            f"- Views: {idea['views']:,} ({idea['views_per_day']:,}/day, {idea['age_days']} days old)\n"
            f"- Likes: {idea['likes']:,} | Comments: {idea['comments']:,}\n"
            f"- Link: {idea['url']}\n"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return folder


def save_competitor(analysis):
    """Save a competitor analysis. Returns the folder path they were saved to."""
    channel = analysis["channel"]
    folder = (
        RESEARCH_DIR
        / "competitors"
        / f"{_slugify(channel['title'])}_{date.today()}"
    )
    folder.mkdir(parents=True, exist_ok=True)

    csv_path = folder / "videos.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "views",
                "likes",
                "comments",
                "engagement_rate",
                "published_at",
                "url",
            ],
        )
        writer.writeheader()
        for v in analysis["all_recent_videos"]:
            writer.writerow({k: v[k] for k in writer.fieldnames})

    md_path = folder / "overview.md"
    lines = [
        f"# Competitor: {channel['title']}",
        f"_Generated {date.today()}_",
        "",
        f"- Subscribers: {channel['subscribers']:,}",
        f"- Total channel views: {channel['total_views']:,}",
        f"- Total videos: {channel['video_count']:,}",
        f"- Avg views (recent uploads): {analysis['avg_views_recent']:,}",
        f"- Avg engagement rate: {analysis['avg_engagement_rate']}%",
        "",
        "## Top performing recent videos",
        "",
    ]
    for i, v in enumerate(analysis["top_videos"], start=1):
        lines.append(
            f"{i}. **{v['title']}** — {v['views']:,} views, "
            f"{v['engagement_rate']}% engagement — {v['url']}"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return folder
