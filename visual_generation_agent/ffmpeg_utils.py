"""Low-level FFmpeg helpers used by this agent's providers.

An independent copy - this agent shares no code with ffmpeg_render_agent
(see README.md), the same way every other agent in this project keeps
its own copy of any shared-looking utility rather than importing across
agent boundaries.
"""

import shutil
import subprocess

# Common install location left behind by `winget install Gyan.FFmpeg` before
# a shell restart picks up the updated PATH - used only as a fallback if
# `ffmpeg` isn't already on PATH.
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


def run_ffmpeg(args):
    """Run ffmpeg with `args` (everything after the binary name), always
    non-interactive and quiet except for real errors. Raises RuntimeError
    with the captured stderr if ffmpeg exits non-zero."""
    cmd = [ffmpeg_path(), "-y", "-loglevel", "error"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed (exit {result.returncode}):\n{result.stderr}\nCommand: {cmd}")
    return result


def escape_drawtext(text):
    """Escape text for safe use inside an ffmpeg drawtext filter argument.
    Preserves literal newlines - drawtext renders them as line breaks."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\u2019")  # drawtext's quoting is fragile with literal apostrophes - use a typographic one
        .replace("%", "\\%")
    )
