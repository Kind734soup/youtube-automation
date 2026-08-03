"""Builds upload_manifest.json for a project and writes it into
final/<topic-slug>_<date>/, alongside final.mp4 and subtitles.srt - the
same folder the FFmpeg Render Agent already writes to, since an upload
manifest only makes sense paired with the video it describes.

Kept separate from manifest_reader.py and metadata_builder.py on
purpose, the same way every other agent in this pipeline splits reading
from building from orchestration: reading input files never needs a
provider, building manifest content is pure and provider-agnostic, and
only actually publishing needs one.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv

from publishing_agent.manifest_reader import (
    final_folder_for,
    load_edit_manifest,
    load_metadata,
    load_production_manifest,
    locate_final_assets,
    project_root_for,
)
from publishing_agent.metadata_builder import build_upload_manifest
from publishing_agent.providers import get_provider

load_dotenv()

MANIFEST_FILENAME = "upload_manifest.json"


def default_provider_name():
    return os.environ.get("PUBLISHING_PROVIDER", "manual").lower()


def prepare_upload_manifest(
    scripts_folder,
    *,
    privacy_status=None,
    scheduled_publish_time=None,
    playlist=None,
    category=None,
    force=False,
):
    """Reads metadata.json (required), edit_manifest.json and
    production_manifest.json (both optional, used for chapters) from
    `scripts_folder`, locates final.mp4/subtitles.srt/thumbnail.png in
    the matching final/ folder, and writes upload_manifest.json there.

    If upload_manifest.json already exists, it is left alone and
    reported as skipped rather than rebuilt - pass force=True to rebuild
    it anyway, matching the same idempotency convention as every other
    agent in this project."""
    scripts_folder = Path(scripts_folder)
    final_folder = final_folder_for(scripts_folder)
    manifest_path = final_folder / MANIFEST_FILENAME

    if manifest_path.exists() and not force:
        return {"skipped": True, "manifest_path": manifest_path}

    metadata = load_metadata(scripts_folder)
    edit_manifest = load_edit_manifest(scripts_folder)
    production_manifest = load_production_manifest(scripts_folder)
    final_assets = locate_final_assets(final_folder, project_root_for(scripts_folder))

    upload_manifest = build_upload_manifest(
        metadata,
        edit_manifest,
        production_manifest,
        final_assets,
        privacy_status=privacy_status,
        scheduled_publish_time=scheduled_publish_time,
        playlist=playlist,
        category=category,
    )

    manifest_path.write_text(json.dumps(upload_manifest, indent=2), encoding="utf-8")

    return {"skipped": False, "manifest_path": manifest_path, "upload_manifest": upload_manifest}


def load_upload_manifest(scripts_folder):
    final_folder = final_folder_for(scripts_folder)
    manifest_path = final_folder / MANIFEST_FILENAME
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Expected {MANIFEST_FILENAME} in {final_folder}, but it was not found. "
            "Run the Publishing Agent's `prepare` command first."
        )
    return json.loads(manifest_path.read_text(encoding="utf-8")), final_folder


def run_provider(scripts_folder, provider_name=None):
    upload_manifest, final_folder = load_upload_manifest(scripts_folder)
    provider = get_provider(provider_name or default_provider_name())
    return provider.publish(upload_manifest, final_folder)
