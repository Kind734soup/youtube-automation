"""The contract every visual-generation provider will implement.

Nothing in this project calls a paid image/video API yet. This class
exists so the shape of that integration is decided now, while the actual
providers (OpenAI Images, FLUX, SDXL, Runway, Veo, Kling, Pika, ...) get
plugged in later without touching manifest_reader.py, organizer.py, or
any other part of this agent.

A future provider consumes one scene dict from production_manifest.json
(see manifest_reader.py for the exact fields) and is responsible for
turning it into one still image.
"""

from abc import ABC, abstractmethod


class VisualProvider(ABC):
    @abstractmethod
    def generate_visual(self, scene, output_path):
        """Generate one still image for `scene` and write it to output_path.

        `scene` is one entry from production_manifest.json's "scenes" list.
        `output_path` is where the image should be written (a .png path).
        Should return metadata about the generation (e.g. provider name,
        resolution, file path) as a dict.
        """
        raise NotImplementedError
