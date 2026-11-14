"""Task record. The hidden tests are pytest source, not imported at collection."""

from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass


@dataclass(frozen=True)
class CodingTask:
    task_id: str
    category: str
    use_cases: tuple[str, ...]
    difficulty: str
    entrypoints: tuple[str, ...]
    prompt: str
    reference_source: str
    hidden_test_source: str

    def entrypoints_defined(self) -> bool:
        tree = ast.parse(self.reference_source)
        names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        return set(self.entrypoints).issubset(names)


def coding_task(
    *,
    task_id: str,
    category: str,
    use_cases: tuple[str, ...],
    difficulty: str,
    entrypoints: tuple[str, ...],
    prompt: str,
    reference: str,
    tests: str,
) -> CodingTask:
    return CodingTask(
        task_id=task_id,
        category=category,
        use_cases=use_cases,
        difficulty=difficulty,
        entrypoints=entrypoints,
        prompt=textwrap.dedent(prompt).strip() + "\n",
        reference_source=textwrap.dedent(reference).strip() + "\n",
        hidden_test_source=textwrap.dedent(tests).strip() + "\n",
    )
