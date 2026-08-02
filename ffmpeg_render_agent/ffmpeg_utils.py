"""Low-level FFmpeg/ffprobe helpers shared by the rest of this agent.

Nothing here knows about edit_manifest.json or scenes - it only knows how
to find the ffmpeg/ffprobe binaries, run them, and read basic media
properties back. Every other module in this agent calls into here rather
than shelling out to ffmpeg directly.
"""

import shutil
import subprocess

# Common install location left behind by `winget install Gyan.FFmpeg` before
# a shell restart picks up the updated PATH - used only as a fallback if
# `ffmpeg`/`ffprobe` aren't already on PATH.
_WINGET_FALLBACK_GLOB = (
    r"C:\Users\*\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*-full_build\bin"
)


def _find_binary(name):
    found = shutil.which(name)
    if found:
        return found

    import glob
    import os

    for bin_dir in glob.glob(_WINGET_FALLBACK_GLOB):
        candidate = os.path.join(bin_dir, f"{name}.exe")
        if os.path.exists(candidate):
            return candidate

    raise RuntimeError(
        f"'{name}' was not found on PATH. Install FFmpeg (e.g. `winget install "
        f"Gyan.FFmpeg`), then restart your shell so PATH picks it up, and try again."
    )


def ffmpeg_path():
    return _find_binary("ffmpeg")


def ffprobe_path():
    return _find_binary("ffprobe")


def run_ffmpeg(args, cwd=None):
    """Run ffmpeg with `args` (everything after the binary name), always
    non-interactive and quiet except for real errors. Raises RuntimeError
    with the captured stderr if ffmpeg exits non-zero."""
    cmd = [ffmpeg_path(), "-y", "-loglevel", "error"] + args
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{result.stderr}\nCommand: {cmd}")
    return result


def probe_duration_seconds(path):
    """Return a media file's duration in seconds via ffprobe."""
    cmd = [
        ffprobe_path(),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path} (exit {result.returncode}):\n{result.stderr}")
    return float(result.stdout.strip())


def escape_drawtext(text):
    """Escape text for safe use inside an ffmpeg drawtext filter argument."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\u2019")  # drawtext's quoting is fragile with literal apostrophes - use a typographic one
        .replace("%", "\\%")
    )
