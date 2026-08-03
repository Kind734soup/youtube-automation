"""ManualProvider - the only publishing provider connected today.

It doesn't call any API and doesn't upload anything itself. It validates
upload_manifest.json against YouTube's basic constraints (see
metadata_builder.validate_upload_manifest) and prints a step-by-step
checklist for uploading the video by hand through YouTube Studio
(studio.youtube.com). Wiring up a real provider (YouTube Data API) is
future work - see README.md, "Adding a publishing provider".
"""

from publishing_agent.metadata_builder import validate_upload_manifest
from publishing_agent.providers.base import PublishProvider


class ManualProvider(PublishProvider):
    def publish(self, upload_manifest, final_folder):
        warnings = validate_upload_manifest(upload_manifest)

        print("\nManual upload checklist (studio.youtube.com):")
        print(f"  1. Upload video: {upload_manifest['source']['final_video_path']}")
        print(f"  2. Title: {upload_manifest['title']}")
        print("  3. Paste the description from upload_manifest.json (includes chapter timestamps).")
        print(f"  4. Tags ({len(upload_manifest['tags'])}): {', '.join(upload_manifest['tags'])}")
        print(f"  5. Category: {upload_manifest['category']['name']}")
        print(f"  6. Playlist: {upload_manifest['playlist']}")
        thumbnail_note = "" if upload_manifest["thumbnail_exists"] else " (missing - add one before publishing)"
        print(f"  7. Thumbnail: {upload_manifest['thumbnail_path']}{thumbnail_note}")
        print(f"  8. Privacy: {upload_manifest['privacy_status']}")
        if upload_manifest["scheduled_publish_time"]:
            print(f"  9. Scheduled publish time: {upload_manifest['scheduled_publish_time']}")

        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"  - {warning}")
        else:
            print("\nNo warnings - manifest looks ready for upload.")

        return {
            "provider": "manual",
            "status": "needs_attention" if warnings else "ready_for_manual_upload",
            "video_id": None,
            "warnings": warnings,
        }
