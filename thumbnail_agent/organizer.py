"""Runs thumbnail_writer.py's LLM call over one project's inputs and
writes the two files this agent produces - thumbnail_prompt.md (human-
readable) and thumbnail_manifest.json (machine-readable) - into that
project's final/ folder, alongside where thumbnail.png will eventually
go and where the Publishing Agent already looks for it.

Kept separate from manifest_reader.py and thumbnail_writer.py on
purpose, the same way every other agent in this pipeline splits reading
from generating from orchestration.
"""

import json
from datetime import date
from pathlib import Path

from thumbnail_agent import llm_client
from thumbnail_agent.manifest_reader import load_project_inputs
from thumbnail_agent.thumbnail_writer import generate_concepts

FINAL_DIR_NAME = "final"
PROMPT_FILENAME = "thumbnail_prompt.md"
MANIFEST_FILENAME = "thumbnail_manifest.json"
THUMBNAIL_FILENAME = "thumbnail.png"


def default_provider_name():
    return llm_client.default_provider_name()


def _project_root_for(scripts_folder):
    """The repository root - the parent of both scripts/ and final/."""
    return Path(scripts_folder).resolve().parent.parent


def final_folder_for(scripts_folder):
    """final/<same folder name as scripts_folder> - matches the exact
    convention every other agent in this pipeline uses (see
    publishing_agent/manifest_reader.py's final_folder_for, reimplemented
    here rather than imported so this agent stays completely separate)."""
    scripts_folder = Path(scripts_folder).resolve()
    return _project_root_for(scripts_folder) / FINAL_DIR_NAME / scripts_folder.name


def _build_markdown(topic, parsed, thumbnail_path, warnings):
    concepts = parsed["concepts"]
    recommended = next(c for c in concepts if c["rank"] == parsed["recommended_rank"])

    lines = [
        f"# Thumbnail Concepts: {topic}",
        f"_Generated {date.today()} by the Thumbnail Agent_",
        "",
    ]

    for concept in concepts:
        marker = " (RECOMMENDED)" if concept["rank"] == parsed["recommended_rank"] else ""
        lines.append(f"## {concept['rank']}. {concept['name']}{marker}")
        lines.append(f"- **Main subject:** {concept['main_subject']}")
        lines.append(f"- **Background:** {concept['background']}")
        lines.append(f"- **Composition:** {concept['composition']}")
        lines.append(f"- **Lighting:** {concept['lighting']}")
        lines.append(f"- **Colors:** {concept['colors']}")
        lines.append(f"- **Facial expression / focal emotion:** {concept['focal_emotion']}")
        lines.append(f"- **Text overlay:** {concept['text_overlay']}")
        lines.append(f"- **Avoid:** {concept['avoid']}")
        lines.append("")

    lines.append(f"## Recommended: Concept {parsed['recommended_rank']} - {recommended['name']}")
    lines.append(parsed["recommended_reason"])
    lines.append("")
    lines.append("## Final image-generation prompt")
    lines.append("```")
    lines.append(parsed["final_image_prompt"])
    lines.append("```")
    lines.append("")
    lines.append(f"Place the generated image at: `{thumbnail_path}`")

    if warnings:
        lines.append("")
        lines.append("## Warnings")
        for warning in warnings:
            lines.append(f"- {warning}")

    return "\n".join(lines).strip() + "\n"


def generate_thumbnail_package(scripts_folder, provider_name=None, force=False):
    """Reads metadata.json/script.md/production_manifest.json (and any
    existing assets/visuals/ images) from `scripts_folder`, generates 3
    ranked thumbnail concepts via the configured LLM provider, and writes
    thumbnail_prompt.md + thumbnail_manifest.json into the matching
    final/ folder.

    If thumbnail_manifest.json already exists there, it's left alone and
    reported as skipped rather than rebuilt - pass force=True to rebuild
    it anyway, matching the same idempotency convention as every other
    agent in this project."""
    scripts_folder = Path(scripts_folder)
    final_folder = final_folder_for(scripts_folder)
    manifest_path = final_folder / MANIFEST_FILENAME
    prompt_md_path = final_folder / PROMPT_FILENAME

    if manifest_path.exists() and not force:
        return {"skipped": True, "manifest_path": manifest_path, "prompt_md_path": prompt_md_path}

    inputs = load_project_inputs(scripts_folder)
    metadata = inputs["metadata"]
    topic = metadata["topic"]

    parsed, warnings = generate_concepts(
        metadata,
        inputs["script_excerpt"],
        inputs["scenes"],
        inputs["existing_scene_images"],
        provider_name=provider_name,
    )

    project_root = _project_root_for(scripts_folder)
    thumbnail_path = (final_folder / THUMBNAIL_FILENAME).resolve().relative_to(project_root).as_posix()
    thumbnail_exists = (final_folder / THUMBNAIL_FILENAME).exists()
    recommended = next(c for c in parsed["concepts"] if c["rank"] == parsed["recommended_rank"])

    thumbnail_manifest = {
        "topic": topic,
        "generated": str(date.today()),
        "concepts": parsed["concepts"],
        "recommended_rank": parsed["recommended_rank"],
        "recommended_concept": recommended["name"],
        "recommended_reason": parsed["recommended_reason"],
        "final_image_prompt": parsed["final_image_prompt"],
        "thumbnail_path": thumbnail_path,
        "thumbnail_exists": thumbnail_exists,
        "warnings": warnings,
        "source": {
            "topic": topic,
            "script_path": (scripts_folder.resolve().relative_to(project_root) / "script.md").as_posix(),
            "production_manifest_path": (
                scripts_folder.resolve().relative_to(project_root) / "production_manifest.json"
            ).as_posix(),
            "existing_scene_images": inputs["existing_scene_images"],
        },
    }

    final_folder.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(thumbnail_manifest, indent=2), encoding="utf-8")
    prompt_md_path.write_text(_build_markdown(topic, parsed, thumbnail_path, warnings), encoding="utf-8")

    return {
        "skipped": False,
        "manifest_path": manifest_path,
        "prompt_md_path": prompt_md_path,
        "thumbnail_manifest": thumbnail_manifest,
        "warnings": warnings,
    }
