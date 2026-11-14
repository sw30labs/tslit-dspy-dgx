"""Pull a Python module out of a model response."""

from __future__ import annotations

import ast
import re

_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)


def _parses(source: str) -> bool:
    try:
        ast.parse(source)
    except SyntaxError:
        return False
    return True


def extract_python(text: str) -> str | None:
    """Return module source, or None when the response has no Python module."""
    if not text or not text.strip():
        return None
    fences = [block.strip() for block in _FENCE.findall(text) if block.strip()]
    if fences:
        parsed = [block for block in fences if _parses(block)]
        chosen = max(parsed or fences, key=len)
        return chosen + "\n"
    stripped = text.strip()
    if _parses(stripped):
        return stripped + "\n"
    for marker in ("def ", "async def ", "import ", "from "):
        idx = stripped.find(marker)
        if idx > 0:
            chunk = stripped[idx:]
            if _parses(chunk):
                return chunk + "\n"
    return None


def prose_outside_code(text: str) -> str:
    return _FENCE.sub(" ", text or "")
