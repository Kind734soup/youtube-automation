"""Registry for visual-generation providers.

Only `placeholder` exists today - a free, offline, no-API-key provider
that draws each scene's number/title/visual_prompt onto a dark cinematic
still image with ffmpeg, so every scene has a real per-scene image before
any paid image/video API is connected.

To add a real provider later (OpenAI Images, FLUX, SDXL, Runway, Veo,
Kling, Pika, or anything else):
  1. Write visual_generation_agent/providers/<name>_provider.py
     implementing VisualProvider (see providers/base.py).
  2. Add one line to get_provider() below, e.g.:
       if name == "openai_images":
           from .openai_images_provider import OpenAIImagesProvider
           return OpenAIImagesProvider()
  3. Feed it scenes straight out of production_manifest.json - no other
     file in this agent needs to change.
"""

SUPPORTED_PROVIDERS = ("placeholder",)  # future: openai_images, flux, sdxl, runway, veo, kling, pika


def get_provider(name):
    if name == "placeholder":
        from .placeholder_provider import PlaceholderProvider

        return PlaceholderProvider()

    raise NotImplementedError(
        f"No visual provider named '{name}' is connected yet (available: {SUPPORTED_PROVIDERS}). "
        "See README.md, 'Adding a visual provider', to wire one up."
    )
