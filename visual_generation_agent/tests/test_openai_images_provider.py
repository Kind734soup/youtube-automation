"""Automated, mocked tests for OpenAIImagesProvider and its surrounding
safety net (provider defaults, atomic writes, PlaceholderProvider
regression).

These tests make ZERO real network calls and ZERO real OpenAI API calls.
`openai.OpenAI` is monkeypatched with a fake class before the provider
ever touches it, so no billing/paid request can occur even if a real
OPENAI_API_KEY happens to be present in the environment when this suite
runs.

Run from the repo root:
    .venv\\Scripts\\python.exe -m unittest visual_generation_agent.tests.test_openai_images_provider -v
or:
    .venv\\Scripts\\python.exe -m unittest discover -s visual_generation_agent/tests -v
"""

import base64
import json
import shutil
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import httpx
import openai

from visual_generation_agent.ffmpeg_utils import ffmpeg_path, run_ffmpeg
from visual_generation_agent.organizer import default_provider_name, generate_scene_visuals
from visual_generation_agent.providers.openai_images_provider import OpenAIImagesProvider

FAKE_API_KEY = "sk-FAKE-NOT-REAL-KEY-000"  # never sent anywhere - openai.OpenAI is always mocked below

FAKE_SCENE = {
    "scene_number": 1,
    "title": "Mock Scene",
    "visual_prompt": "A calm indigo river at night, for provider mock testing only.",
    "lighting": "soft moonlight",
    "mood": "calm",
    "environment": "riverbank",
}

FAKE_METADATA = {"topic": "mock-test-topic", "target_runtime_minutes": 30}

FAKE_PRODUCTION_MANIFEST = {
    "topic": "mock-test-topic",
    "source_metadata": {},
    "scene_count": 1,
    "total_estimated_duration_seconds": 60,
    "scenes": [
        {
            **FAKE_SCENE,
            "narration": "A quiet mock narration for testing only.",
            "camera_movement": "static",
            "characters": [],
            "estimated_duration_seconds": 60,
            "continuity_notes": "",
            "recommended_aspect_ratio": "16:9",
            "recommended_shot_type": "wide",
        }
    ],
}


def _ffprobe_path():
    """Locate ffprobe the same way ffmpeg_utils locates ffmpeg - it ships
    alongside ffmpeg.exe in the same bin directory."""
    found = shutil.which("ffprobe")
    if found:
        return found
    candidate = Path(ffmpeg_path()).with_name("ffprobe.exe")
    if candidate.exists():
        return str(candidate)
    raise RuntimeError("ffprobe not found (expected alongside ffmpeg on PATH).")


def _ffprobe_resolution(path):
    result = subprocess.run(
        [
            _ffprobe_path(), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", str(path),
        ],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def _write_fake_project(root):
    """Write a minimal Script Agent + Video Production Agent output folder
    (metadata.json + production_manifest.json) under `root`, matching the
    exact input contract manifest_reader.py validates."""
    project_dir = Path(root) / "fake_project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "metadata.json").write_text(json.dumps(FAKE_METADATA), encoding="utf-8")
    (project_dir / "production_manifest.json").write_text(
        json.dumps(FAKE_PRODUCTION_MANIFEST), encoding="utf-8"
    )
    return project_dir


class FakeImageObj:
    def __init__(self, b64_json):
        self.b64_json = b64_json


class FakeResponse:
    def __init__(self, b64_json):
        self.data = [FakeImageObj(b64_json)]


class FakeImagesEndpoint:
    """Stands in for client.images - .generate() never makes an HTTP call,
    it just returns (or raises) whatever this test configured."""

    def __init__(self, b64_to_return, calls_log):
        self._b64 = b64_to_return
        self._calls = calls_log

    def generate(self, **kwargs):
        self._calls.append(kwargs)
        return FakeResponse(self._b64)


def make_fake_openai_class(b64_to_return, calls_log):
    class FakeOpenAI:
        def __init__(self, api_key=None):
            calls_log.append(("__init__", api_key))
            self.images = FakeImagesEndpoint(b64_to_return, calls_log)

    return FakeOpenAI


class FakeAuthErrorImages:
    """Simulates an OpenAI-side rejection (e.g. a bad key) without ever
    performing network I/O - httpx.Request/Response are just local Python
    objects here, nothing is sent."""

    def generate(self, **kwargs):
        request = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
        response = httpx.Response(status_code=401, request=request)
        raise openai.AuthenticationError(message="invalid api key", response=response, body=None)


class FakeAuthErrorOpenAI:
    def __init__(self, api_key=None):
        self.images = FakeAuthErrorImages()


def _make_fake_source_png_b64():
    """Build a real, tiny, valid PNG via ffmpeg to stand in for what OpenAI
    would return - exercises the real ffmpeg scale/crop normalization path
    instead of feeding it meaningless bytes for the success-path tests."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "fake_openai_output.png"
        run_ffmpeg(
            ["-f", "lavfi", "-i", "color=c=0x224466:s=300x200:d=1:r=1", "-frames:v", "1", str(src)]
        )
        return base64.b64encode(src.read_bytes()).decode("ascii")


class OpenAIImagesProviderTests(unittest.TestCase):
    """All tests mock openai.OpenAI directly - no real client is ever
    constructed, so no real HTTP call (and no billing) is possible."""

    @classmethod
    def setUpClass(cls):
        cls.fake_png_b64 = _make_fake_source_png_b64()

    def test_provider_instantiates_with_mocked_client_and_fake_key(self):
        calls_log = []
        with mock.patch.object(openai, "OpenAI", make_fake_openai_class(self.fake_png_b64, calls_log)):
            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": FAKE_API_KEY}):
                provider = OpenAIImagesProvider()

        self.assertIsInstance(provider, OpenAIImagesProvider)
        self.assertEqual(
            calls_log, [("__init__", FAKE_API_KEY)],
            "constructing the provider should not call the API yet, only __init__",
        )

    def test_missing_api_key_raises_clear_runtime_error(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("OPENAI_API_KEY", None)
            with self.assertRaises(RuntimeError) as ctx:
                OpenAIImagesProvider()

        message = str(ctx.exception)
        self.assertIn("OPENAI_API_KEY", message)
        self.assertIn(".env", message)

    def test_successful_generation_produces_normalized_image_with_no_leftovers(self):
        calls_log = []
        with mock.patch.object(openai, "OpenAI", make_fake_openai_class(self.fake_png_b64, calls_log)):
            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": FAKE_API_KEY}):
                import tempfile

                with tempfile.TemporaryDirectory() as td:
                    out_dir = Path(td)
                    out_path = out_dir / "scene_01.png"
                    provider = OpenAIImagesProvider()
                    info = provider.generate_visual(FAKE_SCENE, out_path)

                    self.assertTrue(out_path.exists(), "output PNG should exist after success")
                    self.assertEqual(_ffprobe_resolution(out_path), "1920x1080")
                    leftovers = sorted(p.name for p in out_dir.iterdir() if p != out_path)
                    self.assertEqual(leftovers, [], f"no tmp/raw files should remain, found: {leftovers}")
                    self.assertEqual(info["provider"], "openai_images")
                    self.assertEqual(info["resolution"], "1920x1080")

        # exactly one API call (__init__ + one generate() call, no retries/dupes)
        self.assertEqual(len(calls_log), 2)
        sent_prompt = calls_log[1]["prompt"]
        self.assertIn("calm indigo river", sent_prompt)
        self.assertIn("No text, no watermark", sent_prompt)

    def test_invalid_image_bytes_leave_no_partial_or_corrupt_files(self):
        garbage_b64 = base64.b64encode(b"this is not a real png, just text bytes").decode("ascii")
        calls_log = []
        with mock.patch.object(openai, "OpenAI", make_fake_openai_class(garbage_b64, calls_log)):
            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": FAKE_API_KEY}):
                import tempfile

                with tempfile.TemporaryDirectory() as td:
                    out_dir = Path(td)
                    out_path = out_dir / "scene_01.png"
                    provider = OpenAIImagesProvider()

                    with self.assertRaises(RuntimeError):
                        provider.generate_visual(FAKE_SCENE, out_path)

                    self.assertFalse(out_path.exists(), "output_path must not exist after a failed generation")
                    self.assertEqual(
                        list(out_dir.iterdir()), [],
                        "no partial/tmp files should remain in the output dir after failure",
                    )

    def test_api_level_authentication_error_leaves_no_partial_files(self):
        with mock.patch.object(openai, "OpenAI", FakeAuthErrorOpenAI):
            with mock.patch.dict("os.environ", {"OPENAI_API_KEY": FAKE_API_KEY}):
                import tempfile

                with tempfile.TemporaryDirectory() as td:
                    out_dir = Path(td)
                    out_path = out_dir / "scene_01.png"
                    provider = OpenAIImagesProvider()

                    with self.assertRaises(RuntimeError) as ctx:
                        provider.generate_visual(FAKE_SCENE, out_path)

                    self.assertIn("API key was rejected", str(ctx.exception))
                    self.assertFalse(out_path.exists())
                    self.assertEqual(list(out_dir.iterdir()), [])


class VisualProviderDefaultTests(unittest.TestCase):
    """Guards against accidentally opting the project into paid generation."""

    def test_default_provider_name_falls_back_to_placeholder_when_unset(self):
        with mock.patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("VISUAL_PROVIDER", None)
            self.assertEqual(default_provider_name(), "placeholder")

    def test_env_example_documents_placeholder_as_the_default(self):
        env_example = Path(__file__).resolve().parents[2] / ".env.example"
        contents = env_example.read_text(encoding="utf-8")
        self.assertIn("VISUAL_PROVIDER=placeholder", contents)


class PlaceholderProviderRegressionTests(unittest.TestCase):
    """Confirms adding openai_images did not change PlaceholderProvider's
    free/offline behavior - no --provider flag still means placeholder."""

    def test_placeholder_still_generates_and_then_skips(self):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            project_dir = _write_fake_project(td)

            first = generate_scene_visuals(project_dir, provider_name="placeholder")
            out_path = project_dir / "assets" / "visuals" / "scene_01.png"
            self.assertTrue(out_path.exists())
            self.assertFalse(first[0]["skipped"])
            self.assertEqual(_ffprobe_resolution(out_path), "1920x1080")

            second = generate_scene_visuals(project_dir, provider_name="placeholder")
            self.assertTrue(second[0]["skipped"], "rerunning without force should skip, not regenerate")


if __name__ == "__main__":
    unittest.main()
