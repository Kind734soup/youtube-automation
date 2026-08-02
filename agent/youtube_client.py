"""Thin wrapper around the YouTube Data API v3.

Every other module talks to YouTube through the functions in this file,
so there's only one place that knows about API request/response shapes.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from googleapiclient.discovery import build

load_dotenv()

_service = None


def get_client():
    """Return a cached YouTube API client, building it on first use."""
    global _service
    if _service is None:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "YOUTUBE_API_KEY not found. Make sure it's set in your .env file."
            )
        _service = build("youtube", "v3", developerKey=api_key)
    return _service


def search_videos(query, max_results=25, order="relevance"):
    """Search YouTube for videos matching `query`.

    order can be: relevance, date, rating, viewCount, title
    Returns a list of dicts with basic info (no stats yet).
    """
    youtube = get_client()
    response = (
        youtube.search()
        .list(
            q=query,
            part="snippet",
            type="video",
            maxResults=min(max_results, 50),
            order=order,
        )
        .execute()
    )

    results = []
    for item in response.get("items", []):
        results.append(
            {
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "channel_title": item["snippet"]["channelTitle"],
                "channel_id": item["snippet"]["channelId"],
                "published_at": item["snippet"]["publishedAt"],
            }
        )
    return results


def get_video_stats(video_ids):
    """Fetch view/like/comment counts and duration for a batch of video IDs.

    Returns a dict keyed by video_id.
    The API allows up to 50 IDs per request, so we chunk automatically.
    """
    youtube = get_client()
    stats = {}

    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        response = (
            youtube.videos()
            .list(part="statistics,contentDetails", id=",".join(chunk))
            .execute()
        )
        for item in response.get("items", []):
            s = item.get("statistics", {})
            stats[item["id"]] = {
                "views": int(s.get("viewCount", 0)),
                "likes": int(s.get("likeCount", 0)),
                "comments": int(s.get("commentCount", 0)),
                "duration": item.get("contentDetails", {}).get("duration", ""),
            }
    return stats


def resolve_channel_id(channel_input):
    """Turn a channel handle, name, or URL into a channel ID.

    Accepts things like:
      "@mkbhd", "mkbhd", "https://www.youtube.com/@mkbhd"
    """
    youtube = get_client()
    handle = channel_input.strip()

    # Pull the @handle out of a full URL if one was pasted in.
    if "youtube.com/" in handle:
        handle = handle.rstrip("/").split("/")[-1]

    if handle.startswith("@"):
        response = youtube.channels().list(part="id", forHandle=handle).execute()
        items = response.get("items", [])
        if items:
            return items[0]["id"]

    # Fall back to a channel name search. Search-by-name can return small,
    # unrelated lookalike channels, so pull a few candidates and pick the
    # one with the most subscribers - that's almost always the channel
    # the user actually meant.
    search_term = handle.lstrip("@")
    response = (
        youtube.search()
        .list(q=search_term, part="snippet", type="channel", maxResults=5)
        .execute()
    )
    items = response.get("items", [])
    if not items:
        raise ValueError(f"Could not find a channel matching '{channel_input}'.")

    candidate_ids = [item["snippet"]["channelId"] for item in items]
    stats_response = (
        youtube.channels()
        .list(part="statistics", id=",".join(candidate_ids))
        .execute()
    )
    by_subs = sorted(
        stats_response.get("items", []),
        key=lambda c: int(c.get("statistics", {}).get("subscriberCount", 0)),
        reverse=True,
    )
    if not by_subs:
        raise ValueError(f"Could not find a channel matching '{channel_input}'.")
    return by_subs[0]["id"]


def get_channel_details(channel_id):
    """Fetch title, subscriber/view/video counts, and uploads playlist ID."""
    youtube = get_client()
    response = (
        youtube.channels()
        .list(part="snippet,statistics,contentDetails", id=channel_id)
        .execute()
    )
    items = response.get("items", [])
    if not items:
        raise ValueError(f"Channel ID '{channel_id}' not found.")

    item = items[0]
    stats = item.get("statistics", {})
    return {
        "channel_id": channel_id,
        "title": item["snippet"]["title"],
        "subscribers": int(stats.get("subscriberCount", 0)),
        "total_views": int(stats.get("viewCount", 0)),
        "video_count": int(stats.get("videoCount", 0)),
        "uploads_playlist_id": item["contentDetails"]["relatedPlaylists"]["uploads"],
    }


def get_channel_recent_videos(uploads_playlist_id, max_results=15):
    """List a channel's most recent uploads (video_id + title + published_at)."""
    youtube = get_client()
    response = (
        youtube.playlistItems()
        .list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=min(max_results, 50),
        )
        .execute()
    )

    videos = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        videos.append(
            {
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "published_at": snippet["publishedAt"],
            }
        )
    return videos


def days_since(published_at_iso):
    """How many days old is a video, given its published_at ISO timestamp."""
    published = datetime.fromisoformat(published_at_iso.replace("Z", "+00:00"))
    delta = datetime.now(timezone.utc) - published
    return max(delta.total_seconds() / 86400, 0.1)  # avoid divide-by-zero for brand-new videos
