"""Saves an edit manifest back into its source Script Agent folder.

Layout (added to an existing scripts/<topic-slug>_<date>/ folder):
  scripts/
    <topic-slug>_<date>/
      script.md                  <- from the Script Agent (untouched)
      scene_descriptions.md      <- from the Script Agent (untouched)
      metadata.json               <- from the Script Agent (untouched)
      production_manifest.json    <- from the Video Production Agent (untouched)
      narration_manifest.json     <- from the Voice Generation Agent (untouched)
      edit_manifest.json          <- written by this agent

Written alongside the source files rather than into a separate tree,
since an edit manifest only makes sense paired with the project it was
built from.
"""

import json
from pathlib import Path


def save_manifest(manifest, folder):
    """Write edit_manifest.json into `folder`. Returns the file path."""
    folder = Path(folder)
    manifest_path = folder / "edit_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path
