"""Manual (Claude Pro) provider - no API key or billing required.

Instead of calling an API, generate() prints (and saves) the prompt for
you to paste into Claude Pro yourself, then reads Claude's reply back
from the terminal. Nothing else in thumbnail_agent knows the difference
- swap to a live provider later by changing THUMBNAIL_LLM_PROVIDER in
.env. No code changes.

Kept entirely separate from script_agent/llm_providers/manual_provider.py
on purpose (this agent does not import from script_agent) - it saves its
own prompts under thumbnail_agent/_manual_prompts/ rather than sharing
script_agent's scripts/_manual_prompts/ folder.
"""

from pathlib import Path

from .base import LLMProvider

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "_manual_prompts"


class ManualProvider(LLMProvider):
    def __init__(self):
        self._call_count = 0

    def generate(self, system, prompt, max_tokens=4096):
        self._call_count += 1
        full_prompt = f"{system}\n\n---\n\n{prompt}"

        PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
        prompt_path = PROMPTS_DIR / f"prompt_{self._call_count:02d}.txt"
        prompt_path.write_text(full_prompt, encoding="utf-8")

        print("\n" + "=" * 70)
        print(f"MANUAL STEP {self._call_count} - paste this into Claude Pro")
        print(f"(also saved to: {prompt_path})")
        print("=" * 70)
        print(full_prompt)
        print("=" * 70)
        print("Paste Claude's FULL reply below (JSON only).")
        print("When done pasting, type END on its own line and press Enter.\n")

        lines = []
        while True:
            line = input()
            if line.strip() == "END":
                break
            lines.append(line)

        response = "\n".join(lines).strip()
        if not response:
            raise RuntimeError("No response was entered - cannot continue without Claude's reply.")
        return response
