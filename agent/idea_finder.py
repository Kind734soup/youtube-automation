"""Finds video ideas for a topic by searching YouTube and ranking results
by view velocity (views per day since publish) instead of raw view count.

A video with 1M views over 2 years is old news. A video with 50K views in
3 days is a sign the topic is resonating *right now* - that's a better
signal for "what should I make a video about."
"""

from agent.youtube_client import days_since, get_video_stats, search_videos


def find_video_ideas(topic, max_results=25):
    candidates = search_videos(topic, max_results=max_results, order="relevance")
    if not candidates:
        return []

    stats = get_video_stats([c["video_id"] for c in candidates])

    ideas = []
    for c in candidates:
        s = stats.get(c["video_id"])
        if not s:
            continue
        age_days = days_since(c["published_at"])
        velocity = round(s["views"] / age_days, 1)
        ideas.append(
            {
                "title": c["title"],
                "channel": c["channel_title"],
                "video_id": c["video_id"],
                "url": f"https://www.youtube.com/watch?v={c['video_id']}",
                "published_at": c["published_at"],
                "age_days": round(age_days, 1),
                "views": s["views"],
                "likes": s["likes"],
                "comments": s["comments"],
                "views_per_day": velocity,
            }
        )

    ideas.sort(key=lambda x: x["views_per_day"], reverse=True)
    return ideas
