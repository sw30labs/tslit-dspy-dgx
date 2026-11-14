"""Pull a Python module out of a model response.

Prefer a fence that defines the task's entrypoints. Otherwise concatenate the
fences that parse. ``python``, ``python3``, ``py``, and unlabeled fences all
count. A usage example that happens to be the longest block does not win
when a shorter block actually defines the required functions.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

_FENCE = re.compile(
    r"```(?:python3|python|py)?[ \t]*\r?\n(.*?)```",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class Extraction:
    source: str | None
    method: str
    fence_count: int

    @property
    def found(self) -> bool:
        return self.source is not None


def _parses(source: str) -> bool:
    try:
        ast.parse(source)
    except SyntaxError:
        return False
    return True


def defined_names(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def defines_entrypoints(source: str, entrypoints: tuple[str, ...] | list[str]) -> bool:
    if not entrypoints:
        return _parses(source)
    return set(entrypoints).issubset(defined_names(source))


def extract_python(text: str, entrypoints: tuple[str, ...] | list[str] = ()) -> Extraction:
    """Return the candidate module and how it was chosen."""
    wanted = tuple(entrypoints)
    if not text or not text.strip():
        return Extraction(None, "none", 0)
    fences = [block.strip() for block in _FENCE.findall(text) if block.strip()]
    fence_count = len(fences)
    if fences:
        parsing = [block for block in fences if _parses(block)]
        for block in parsing:
            if defines_entrypoints(block, wanted):
                return Extraction(block + "\n", "entrypoint_fence", fence_count)
        if len(parsing) > 1:
            combined = "\n\n".join(parsing)
            if _parses(combined) and defines_entrypoints(combined, wanted):
                return Extraction(combined + "\n", "concatenated_fences", fence_count)
        if parsing:
            chosen = max(parsing, key=len)
            return Extraction(chosen + "\n", "longest_parsing_fence", fence_count)
        chosen = max(fences, key=len)
        return Extraction(chosen + "\n", "longest_fence", fence_count)
    stripped = text.strip()
    if _parses(stripped):
        return Extraction(stripped + "\n", "bare", 0)
    for marker in ("def ", "async def ", "import ", "from "):
        idx = stripped.find(marker)
        if idx > 0:
            chunk = stripped[idx:]
            if _parses(chunk):
                return Extraction(chunk + "\n", "sliced_bare", 0)
    return Extraction(None, "none", fence_count)


def prose_outside_code(text: str) -> str:
    return _FENCE.sub(" ", text or "")
