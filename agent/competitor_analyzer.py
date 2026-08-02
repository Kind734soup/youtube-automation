"""Analyzes a competitor channel: overview stats + how their recent videos
are actually performing (not just subscriber count).
"""

from agent.youtube_client import (
    get_channel_details,
    get_channel_recent_videos,
    get_video_stats,
    resolve_channel_id,
)


def analyze_competitor(channel_input, max_videos=15):
    channel_id = resolve_channel_id(channel_input)
    channel = get_channel_details(channel_id)

    recent = get_channel_recent_videos(
        channel["uploads_playlist_id"], max_results=max_videos
    )
    stats = get_video_stats([v["video_id"] for v in recent])

    videos = []
    total_views = 0
    total_engagement = 0
    for v in recent:
        s = stats.get(v["video_id"])
        if not s:
            continue
        engagement = s["likes"] + s["comments"]
        videos.append(
            {
                "title": v["title"],
                "video_id": v["video_id"],
                "url": f"https://www.youtube.com/watch?v={v['video_id']}",
                "published_at": v["published_at"],
                "views": s["views"],
                "likes": s["likes"],
                "comments": s["comments"],
                "engagement_rate": round(engagement / s["views"] * 100, 2)
                if s["views"]
                else 0,
            }
        )
        total_views += s["views"]
        total_engagement += engagement

    videos.sort(key=lambda x: x["views"], reverse=True)
    video_count = len(videos) or 1

    return {
        "channel": channel,
        "avg_views_recent": round(total_views / video_count),
        "avg_engagement_rate": round(total_engagement / total_views * 100, 2)
        if total_views
        else 0,
        "top_videos": videos[:5],
        "all_recent_videos": videos,
    }
