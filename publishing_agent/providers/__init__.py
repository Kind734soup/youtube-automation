"""Registry for publishing providers.

Only `manual` exists today - it doesn't call any API. It validates
upload_manifest.json and prints a checklist for uploading the video by
hand through YouTube Studio (see manual_provider.py).

To add a real provider later (YouTube Data API, or anything else):
  1. Write publishing_agent/providers/<name>_provider.py implementing
     PublishProvider (see providers/base.py).
  2. Add one line to get_provider() below, e.g.:
       if name == "youtube_data_api":
           from .youtube_data_api_provider import YouTubeDataAPIProvider
           return YouTubeDataAPIProvider()
  3. Feed it upload_manifest.json straight out of organizer.py - no other
     file in this agent needs to change.
"""

SUPPORTED_PROVIDERS = ("manual",)  # future: youtube_data_api


def get_provider(name):
    if name == "manual":
        from .manual_provider import ManualProvider

        return ManualProvider()

    raise NotImplementedError(
        f"No publishing provider named '{name}' is connected yet (available: {SUPPORTED_PROVIDERS}). "
        "See README.md, 'Adding a publishing provider', to wire one up."
    )
