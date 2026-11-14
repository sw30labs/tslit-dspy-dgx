"""Executable coding-task bank. Prompts and oracles live together."""

from __future__ import annotations

from tslit_dspy.drift.bank.concurrency import TASKS as _CONCURRENCY
from tslit_dspy.drift.bank.crypto_api import TASKS as _CRYPTO
from tslit_dspy.drift.bank.file_io import TASKS as _FILE_IO
from tslit_dspy.drift.bank.model import CodingTask
from tslit_dspy.drift.bank.numeric import TASKS as _NUMERIC
from tslit_dspy.drift.bank.parsing import TASKS as _PARSING
from tslit_dspy.drift.bank.sql_tasks import TASKS as _SQL
from tslit_dspy.drift.bank.validation import TASKS as _VALIDATION

USE_CASES = ("defense_contractor", "soc_analyst", "academic")
CATEGORIES = (
    "parsing",
    "crypto_api",
    "concurrency",
    "validation",
    "sql",
    "file_io",
    "numeric",
)


def load_tasks() -> tuple[CodingTask, ...]:
    tasks = (
        *_PARSING,
        *_CRYPTO,
        *_CONCURRENCY,
        *_VALIDATION,
        *_SQL,
        *_FILE_IO,
        *_NUMERIC,
    )
    ids = [t.task_id for t in tasks]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate task id in the drift bank")
    return tasks


def tasks_by_id() -> dict[str, CodingTask]:
    return {t.task_id: t for t in load_tasks()}
