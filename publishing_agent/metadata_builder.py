"""Turns metadata.json (plus edit_manifest.json/production_manifest.json
for chapters, and the located final assets) into the fields
upload_manifest.json needs: title, description, tags, chapters,
category, playlist, privacy status, scheduled publish time, and
thumbnail path.

Pure functions only, no file I/O - see manifest_reader.py for reading
input files and organizer.py for writing upload_manifest.json.

These heuristics (tag extraction, category guessing, description
template) are a reasonable starting point, not real SEO - see README.md,
"What this agent does not do".
"""

from datetime import datetime

CHANNEL_NAME = "Nightfall Atlas"
CHANNEL_BLURB = (
    f"{CHANNEL_NAME} creates long-form sleep stories that blend history, mythology, and peaceful "
    "exploration - perfect for winding down, falling asleep, or relaxing in the background. New "
    "stories are added regularly."
)

YOUTUBE_TITLE_MAX_CHARS = 100
YOUTUBE_DESCRIPTION_MAX_CHARS = 5000
YOUTUBE_TAG_MAX_CHARS = 100
YOUTUBE_TAGS_MAX_TOTAL_CHARS = 460  # stays safely under YouTube's real 500-char cumulative tag limit
MIN_CHAPTERS_FOR_YOUTUBE_TIMESTAMPS = 3
MIN_CHAPTER_GAP_SECONDS = 10

EVERGREEN_TAGS = [
    "sleep story",
    "sleep stories",
    "relaxing sleep story",
    "bedtime story for adults",
    "fall asleep fast",
    "asmr history",
    "calm narration",
    "history for sleep",
    CHANNEL_NAME,
]

CATEGORY_MAP = {
    "education": {"name": "Education", "id": "27"},
    "entertainment": {"name": "Entertainment", "id": "24"},
    "howto_style": {"name": "Howto & Style", "id": "26"},
    "people_blogs": {"name": "People & Blogs", "id": "22"},
    "travel_events": {"name": "Travel & Events", "id": "19"},
    "film_animation": {"name": "Film & Animation", "id": "1"},
}

VALID_PRIVACY_STATUSES = ("private", "unlisted", "public")


def _split_topic(topic):
    """Splits "Hook - Subtitle | Theme" into (hook, subtitle, theme). Any
    part may be None depending on how the topic string was phrased -
    e.g. "Fall Asleep to the ENTIRE Story of Ancient Egypt - Pyramids,
    Pharaohs and Gods | Ancient History" splits into hook="Fall Asleep to
    the ENTIRE Story of Ancient Egypt", subtitle="Pyramids, Pharaohs and
    Gods", theme="Ancient History"."""
    main = topic
    theme = None
    if "|" in topic:
        main, _, theme = topic.partition("|")
        main = main.strip()
        theme = theme.strip() or None

    hook = main
    subtitle = None
    for dash in (" — ", " – ", " - "):
        if dash in main:
            hook, _, subtitle = main.partition(dash)
            hook = hook.strip()
            subtitle = subtitle.strip() or None
            break

    return hook, subtitle, theme


def _format_timestamp(seconds):
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def build_title(topic):
    title = topic.strip()
    if len(title) > YOUTUBE_TITLE_MAX_CHARS:
        title = title[: YOUTUBE_TITLE_MAX_CHARS - 1].rstrip() + "…"
    return title


def build_chapters(edit_manifest, production_manifest):
    """Prefers edit_manifest.json's timeline (actual rendered start
    times); falls back to production_manifest.json's scenes (estimated
    durations, summed) if the edit manifest isn't available. Returns []
    if neither is available - upload_manifest.json still gets written,
    just without chapters."""
    estimated = False

    if edit_manifest and edit_manifest.get("timeline"):
        raw = [
            {"title": entry["scene_title"], "start_time_seconds": entry["start_time_seconds"]}
            for entry in edit_manifest["timeline"]
        ]
    elif production_manifest and production_manifest.get("scenes"):
        estimated = True
        raw = []
        cursor = 0.0
        for scene in production_manifest["scenes"]:
            raw.append({"title": scene["title"], "start_time_seconds": cursor})
            cursor += scene.get("estimated_duration_seconds", 0.0)
    else:
        return []

    chapters = []
    for entry in raw:
        chapter = {
            "title": entry["title"],
            "start_time_seconds": round(entry["start_time_seconds"], 1),
            "start_time_formatted": _format_timestamp(entry["start_time_seconds"]),
        }
        if estimated:
            chapter["estimated"] = True
        chapters.append(chapter)

    if chapters:
        chapters[0]["start_time_seconds"] = 0.0
        chapters[0]["start_time_formatted"] = "0:00"

    return chapters


def build_description(topic, chapters, target_minutes=None):
    _hook, _subtitle, theme = _split_topic(topic)

    lines = [topic.strip(), ""]

    intro = f"A slow, calming journey through {theme.lower()}" if theme else "A slow, calming journey"
    if target_minutes:
        intro += f", roughly {int(round(target_minutes))} minutes long"
    intro += (
        ", crafted for deep, restful sleep. Let your mind drift as the story unfolds - no jump "
        "scares, no sudden shifts, just a long, gentle unwinding into rest."
    )
    lines.append(intro)
    lines.append("")

    if chapters:
        lines.append("Chapters")
        for chapter in chapters:
            lines.append(f"{chapter['start_time_formatted']} {chapter['title']}")
        lines.append("")

    lines.append(f"About {CHANNEL_NAME}")
    lines.append(CHANNEL_BLURB)
    lines.append("")
    lines.append(f"Subscribe for more calming, story-driven sleep content from {CHANNEL_NAME}.")

    return "\n".join(lines).strip() + "\n"


def build_tags(topic):
    hook, subtitle, theme = _split_topic(topic)

    candidates = []
    for part in (hook, subtitle, theme):
        if not part:
            continue
        for chunk in part.split(","):
            chunk = chunk.strip(" .")
            if chunk:
                candidates.append(chunk)
    candidates.extend(EVERGREEN_TAGS)

    tags = []
    seen = set()
    total_chars = 0
    for candidate in candidates:
        tag = candidate.strip()
        if not tag or len(tag) > YOUTUBE_TAG_MAX_CHARS:
            continue
        key = tag.lower()
        if key in seen:
            continue
        added_length = len(tag) + (1 if tags else 0)  # +1 accounts for the joining comma
        if total_chars + added_length > YOUTUBE_TAGS_MAX_TOTAL_CHARS:
            break
        tags.append(tag)
        seen.add(key)
        total_chars += added_length

    return tags


def default_category(topic):
    lowered = topic.lower()
    if any(word in lowered for word in ("history", "mythology", "ancient", "legend", "legendary")):
        return dict(CATEGORY_MAP["education"])
    return dict(CATEGORY_MAP["entertainment"])


def resolve_category(name_or_none, topic):
    if not name_or_none:
        return default_category(topic)
    key = name_or_none.strip().lower().replace(" & ", "_").replace(" ", "_")
    if key in CATEGORY_MAP:
        return dict(CATEGORY_MAP[key])
    # Unknown override - trust the caller's name, no numeric id available for it.
    return {"name": name_or_none.strip(), "id": None}


def default_playlist(topic):
    _hook, _subtitle, theme = _split_topic(topic)
    if theme:
        return f"{CHANNEL_NAME} — {theme}"
    return f"{CHANNEL_NAME} Sleep Stories"


def resolve_playlist(name_or_none, topic):
    return name_or_none.strip() if name_or_none else default_playlist(topic)


def resolve_privacy_status(value):
    value = (value or "unlisted").strip().lower()
    if value not in VALID_PRIVACY_STATUSES:
        raise ValueError(f"privacy status must be one of {VALID_PRIVACY_STATUSES}, got '{value}'")
    return value


def resolve_scheduled_publish_time(value):
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"--publish-at must be an ISO 8601 timestamp, got '{value}'") from exc
    return value


def validate_upload_manifest(upload_manifest):
    """Returns a list of human-readable warning strings describing
    anything that would stop YouTube from accepting the upload cleanly,
    or from treating the description's timestamps as real chapters.
    Never raises - an empty list means no issues found."""
    warnings = []

    title = upload_manifest["title"]
    if len(title) > YOUTUBE_TITLE_MAX_CHARS:
        warnings.append(f"title is {len(title)} chars, over YouTube's {YOUTUBE_TITLE_MAX_CHARS}-char limit")

    description = upload_manifest["description"]
    if len(description) > YOUTUBE_DESCRIPTION_MAX_CHARS:
        warnings.append(
            f"description is {len(description)} chars, over YouTube's {YOUTUBE_DESCRIPTION_MAX_CHARS}-char limit"
        )

    tags = upload_manifest["tags"]
    tags_total = sum(len(t) for t in tags) + max(len(tags) - 1, 0)
    if tags_total > 500:
        warnings.append(f"tags total {tags_total} chars, over YouTube's 500-char limit")

    chapters = upload_manifest["chapters"]
    if chapters:
        if chapters[0]["start_time_seconds"] != 0.0:
            warnings.append("first chapter does not start at 0:00 - YouTube will not treat these as real chapters")
        if len(chapters) < MIN_CHAPTERS_FOR_YOUTUBE_TIMESTAMPS:
            warnings.append(
                f"only {len(chapters)} chapter(s) - YouTube requires at least "
                f"{MIN_CHAPTERS_FOR_YOUTUBE_TIMESTAMPS} to show a chapter list"
            )
        for prev, curr in zip(chapters, chapters[1:]):
            gap = curr["start_time_seconds"] - prev["start_time_seconds"]
            if gap < MIN_CHAPTER_GAP_SECONDS:
                warnings.append(
                    f"chapter '{prev['title']}' is only {gap:.1f}s long - YouTube requires at least "
                    f"{MIN_CHAPTER_GAP_SECONDS}s per chapter"
                )

    if not upload_manifest["thumbnail_exists"]:
        warnings.append(
            f"thumbnail not found at {upload_manifest['thumbnail_path']} - add one before publishing"
        )

    if upload_manifest["scheduled_publish_time"] and upload_manifest["privacy_status"] != "private":
        warnings.append(
            "scheduled_publish_time is set but privacy_status is not 'private' - YouTube only honors "
            "a scheduled publish time when the upload is set to private until then"
        )

    return warnings


def build_upload_manifest(
    metadata,
    edit_manifest,
    production_manifest,
    final_assets,
    *,
    privacy_status=None,
    scheduled_publish_time=None,
    playlist=None,
    category=None,
):
    topic = metadata["topic"]
    chapters = build_chapters(edit_manifest, production_manifest)

    return {
        "title": build_title(topic),
        "description": build_description(topic, chapters, metadata.get("target_minutes")),
        "tags": build_tags(topic),
        "chapters": chapters,
        "category": resolve_category(category, topic),
        "playlist": resolve_playlist(playlist, topic),
        "privacy_status": resolve_privacy_status(privacy_status),
        "scheduled_publish_time": resolve_scheduled_publish_time(scheduled_publish_time),
        "thumbnail_path": final_assets["thumbnail_path"],
        "thumbnail_exists": final_assets["thumbnail_exists"],
        "source": {
            "topic": topic,
            "final_video_path": final_assets["final_video_path"],
            "subtitles_path": final_assets["subtitles_path"],
        },
    }
