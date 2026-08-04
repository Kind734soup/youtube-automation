"""Registry for visual-generation providers.

`placeholder` is a free, offline, no-API-key provider that draws each
scene's number/title/visual_prompt onto a dark cinematic still image
with ffmpeg. `openai_images` is the first real provider - it calls
OpenAI's Images API (gpt-image-1) to render an actual scene image, then
normalizes it to this project's 1920x1080 with ffmpeg. Neither is
required; the other is always available as a fallback via VISUAL_PROVIDER
in .env or --provider on the command line.

To add another real provider later (FLUX, SDXL, Runway, Veo, Kling,
Pika, or anything else):
  1. Write visual_generation_agent/providers/<name>_provider.py
     implementing VisualProvider (see providers/base.py).
  2. Add one line to get_provider() below, e.g.:
       if name == "flux":
           from .flux_provider import FluxProvider
           return FluxProvider()
  3. Feed it scenes straight out of production_manifest.json - no other
     file in this agent needs to change.
"""

SUPPORTED_PROVIDERS = ("placeholder", "openai_images")  # future: flux, sdxl, runway, veo, kling, pika


def get_provider(name):
    if name == "placeholder":
        from .placeholder_provider import PlaceholderProvider

        return PlaceholderProvider()

    if name == "openai_images":
        from .openai_images_provider import OpenAIImagesProvider

        return OpenAIImagesProvider()

    raise NotImplementedError(
        f"No visual provider named '{name}' is connected yet (available: {SUPPORTED_PROVIDERS}). "
        "See README.md, 'Adding a visual provider', to wire one up."
    )
