"""The contract every video-generation provider will implement.

Nothing in this project calls a video API yet. This class exists so the
shape of that integration is decided now, while the actual providers
(Google Veo, Runway, Kling, Pika, ...) get plugged in later without
touching the manifest builder or any other part of this agent.

A future provider consumes one scene dict from production_manifest.json
(see manifest_builder.py for the exact fields) and is responsible for
turning it into a rendered video clip.
"""

from abc import ABC, abstractmethod


class VideoProvider(ABC):
    @abstractmethod
    def render_scene(self, scene, output_path):
        """Render a single manifest scene to a video clip at output_path.

        `scene` is one entry from production_manifest.json's "scenes" list.
        `output_path` is where the rendered clip should be written.
        Should return metadata about the render (e.g. provider job id,
        actual duration, file path) as a dict.
        """
        raise NotImplementedError
