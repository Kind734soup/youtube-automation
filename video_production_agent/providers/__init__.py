"""Registry for video-generation providers.

Empty on purpose - see README.md, "Adding a video provider" for the plan.
No video API is wired up yet; get_provider() exists so the rest of the
codebase (and future code) has one place to ask for a provider by name,
without needing to know whether it's Veo, Runway, Kling, Pika, or
something else entirely.

To add a provider later:
  1. Write video_production_agent/providers/<name>_provider.py implementing
     VideoProvider (see providers/base.py).
  2. Add one line to get_provider() below, e.g.:
       if name == "veo":
           from .veo_provider import VeoProvider
           return VeoProvider()
  3. Call it with the scenes from production_manifest.json.
No other file in this agent has to change.
"""

SUPPORTED_PROVIDERS = ()  # e.g. will become ("veo", "runway", "kling", "pika")


def get_provider(name):
    raise NotImplementedError(
        f"No video providers are connected yet (requested: '{name}'). "
        "This agent currently only produces production_manifest.json. "
        "See README.md, 'Adding a video provider', to wire one up."
    )
