"""The contract every publishing provider will implement.

Nothing in this project calls the YouTube Data API, or any other upload
mechanism, yet. This class exists so the shape of that integration is
decided now, while the actual providers (YouTube Data API, manual
upload, and anything else) get plugged in later without touching
organizer.py, metadata_builder.py, or any other part of this agent.

A provider consumes the upload_manifest.json dict this agent already
built (see metadata_builder.py for the exact fields) plus the project
folder it was written into, and is responsible for getting the video
published - or, for a manual provider, for telling a human how to do it.
"""

from abc import ABC, abstractmethod


class PublishProvider(ABC):
    @abstractmethod
    def publish(self, upload_manifest, final_folder):
        """Act on `upload_manifest` (see organizer.py / metadata_builder.py
        for its exact shape) for the video living in `final_folder`.

        Must return a dict describing what happened, at minimum:
          {"provider": ..., "status": ..., "video_id": ... or None}
        """
        raise NotImplementedError
