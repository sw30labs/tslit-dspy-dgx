"""Simulation-based power for the pre-registered adversary-drift contrasts.

The earlier closed-form calculation treated every persona draw as an
independent Bernoulli trial and ignored three things that eat power:

- task-level heterogeneity of the stratum gap (a paired difference still
  varies across tasks)
- persona-level noise inside a stratum
- Holm correction across the five-contrast family
- outcomes dropped because the reply had no scorable code

Greedy temperature-0 repeats are not extra N. A single draw per task
(one persona, one position, one repeat, no code loss) is reported beside
the default so the optimistic figure is not the only one on the page.
"""

from __future__ import annotations

import argparse
import math
import random
from typing import Any

from tslit_dspy.drift.analysis import holm

STRATA = ("adversary", "aligned", "neutral", "placebo", "none")
# Primary family. ``none`` has one persona; the others use ``k_primary``.
CONTRASTS = (
    ("adversary_vs_neutral", "adversary", "neutral"),
    ("adversary_vs_aligned", "adversary", "aligned"),
    ("adversary_vs_placebo", "adversary", "placebo"),
    ("placebo_vs_none", "placebo", "none"),
    ("aligned_vs_neutral", "aligned", "neutral"),
)


def norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF via binary search on erf. Kept for callers."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    lo, hi = -12.0, 12.0
    for _ in range(80):
        mid = (lo + hi) / 2.0
        cdf = 0.5 * (1.0 + math.erf(mid / math.sqrt(2.0)))
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _clip(p: float) -> float:
    return min(0.98, max(0.02, p))


def _gauss(rng: random.Random) -> float:
    return rng.gauss(0.0, 1.0)


def _paired_pvalue(diffs: list[float]) -> float | None:
    """Two-sided normal p-value for the mean of task-level differences.

    The confirmatory analysis uses a sign-flip test. This approximation is
    the same large-sample test, which is what the simulation can afford to
    repeat. Holm is applied to these p-values afterwards.
    """
    n = len(diffs)
    if n < 2:
        return None
    mean = sum(diffs) / n
    var = sum((value - mean) ** 2 for value in diffs) / (n - 1)
    if var <= 1e-18:
        return 0.0 if abs(mean) > 1e-12 else 1.0
    z = abs(mean) / math.sqrt(var / n)
    return math.erfc(z / math.sqrt(2.0))


def _contrast_stats(
    labels: list[str],
    by_task: list[list[tuple[int, int]]],
) -> dict[str, float]:
    """Task-equal difference of scorable failure rates for each contrast."""
    diffs: dict[str, list[float]] = {name: [] for name, _, _ in CONTRASTS}
    for rows in by_task:
        bucket: dict[str, list[int]] = {}
        for label, (failed, kept) in zip(labels, rows):
            slot = bucket.setdefault(label, [0, 0])
            slot[0] += failed
            slot[1] += kept
        rates = {name: (failed / kept) for name, (failed, kept) in bucket.items() if kept}
        for name, arm_a, arm_b in CONTRASTS:
            if arm_a in rates and arm_b in rates:
                diffs[name].append(rates[arm_a] - rates[arm_b])
    return {name: (sum(values) / len(values)) for name, values in diffs.items() if values}


def simulate_once(
    rng: random.Random,
    *,
    baseline: float,
    delta: float,
    n_tasks: int,
    k_primary: int,
    k_none: int,
    n_positions: int,
    repeats: int,
    sigma_task: float,
    sigma_persona: float,
    code_rate: float,
    n_perm: int = 99,
) -> dict[str, float | None]:
    """One replicate. P-values are persona-label permutations, then Holm.

    Persona effects are constant across tasks, so a task-only standard error
    treats that shared shock as a precise stratum effect. Shuffling the
    stratum labels across personas is valid under that dependence.
    """
    labels = []
    effects = []
    for stratum in STRATA:
        k = k_none if stratum == "none" else k_primary
        for _ in range(k):
            labels.append(stratum)
            effects.append(sigma_persona * _gauss(rng))
    draws = n_positions * repeats
    by_task: list[list[tuple[int, int]]] = []
    for _task in range(n_tasks):
        tau = sigma_task * _gauss(rng)
        rows: list[tuple[int, int]] = []
        for label, effect in zip(labels, effects):
            shift = (delta + tau) if label == "adversary" else 0.0
            p = _clip(baseline + shift + effect)
            failed = 0
            kept = 0
            for _ in range(draws):
                if rng.random() > code_rate:
                    continue
                kept += 1
                if rng.random() < p:
                    failed += 1
            rows.append((failed, kept))
        by_task.append(rows)
    observed = _contrast_stats(labels, by_task)
    extreme = {name: 0 for name in observed}
    n_ok = 0
    for _ in range(n_perm):
        shuffled = labels[:]
        rng.shuffle(shuffled)
        stats = _contrast_stats(shuffled, by_task)
        n_ok += 1
        for name, value in observed.items():
            other = stats.get(name)
            if other is not None and abs(other) + 1e-15 >= abs(value):
                extreme[name] += 1
    if n_ok == 0:
        return {name: None for name, _, _ in CONTRASTS}
    raw = {name: (extreme[name] + 1) / (n_ok + 1) for name in observed}
    adjusted = holm(raw)
    return {name: adjusted.get(name, {}).get("p_holm") for name, _, _ in CONTRASTS}


def rejection_rate(
    *,
    baseline: float = 0.35,
    delta: float = 0.10,
    n_tasks: int = 49,
    k_primary: int = 6,
    k_none: int = 1,
    n_positions: int = 2,
    repeats: int = 4,
    sigma_task: float = 0.04,
    sigma_persona: float = 0.03,
    code_rate: float = 0.85,
    alpha: float = 0.05,
    n_sim: int = 40,
    n_perm: int = 199,
    seed: int = 20261114,
    contrast: str = "adversary_vs_neutral",
) -> float:
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_sim):
        result = simulate_once(
            rng,
            baseline=baseline,
            delta=delta,
            n_tasks=n_tasks,
            k_primary=k_primary,
            k_none=k_none,
            n_positions=n_positions,
            repeats=repeats,
            sigma_task=sigma_task,
            sigma_persona=sigma_persona,
            code_rate=code_rate,
            n_perm=n_perm,
        )
        pvalue = result.get(contrast)
        if pvalue is not None and pvalue <= alpha:
            hits += 1
    return hits / n_sim


def repeats_for_power(
    *,
    delta: float,
    target_power: float = 0.80,
    max_repeats: int = 8,
    **kwargs: Any,
) -> int | None:
    """Smallest sampled-repeat count with estimated power at or above the target."""
    for repeats in range(1, max_repeats + 1):
        rate = rejection_rate(delta=delta, repeats=repeats, **kwargs)
        if rate + 1e-12 >= target_power:
            return repeats
    return None


def single_draw_mde(
    *,
    grid: tuple[float, ...] = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40),
    target_power: float = 0.80,
    **kwargs: Any,
) -> float | None:
    """Smallest delta on ``grid`` that reaches the target with one obs per arm."""
    for delta in grid:
        rate = rejection_rate(
            delta=delta,
            repeats=1,
            n_positions=1,
            k_primary=1,
            k_none=1,
            code_rate=1.0,
            sigma_persona=0.0,
            **kwargs,
        )
        if rate + 1e-12 >= target_power:
            return delta
    return None


def plan(
    *,
    baseline: float = 0.35,
    n_tasks: int = 49,
    k_primary: int = 6,
    k_none: int = 1,
    n_positions: int = 2,
    sampled_repeats: int | None = None,
    alpha: float = 0.05,
    target_power: float = 0.80,
    sigma_task: float = 0.04,
    sigma_persona: float = 0.03,
    code_rate: float = 0.85,
    n_sim: int = 40,
    n_perm: int = 199,
    seed: int = 20261114,
) -> dict[str, Any]:
    """Recommend sampled repeats for a 10 point gap, and report the 5 point power."""
    common = dict(
        baseline=baseline,
        n_tasks=n_tasks,
        k_primary=k_primary,
        k_none=k_none,
        n_positions=n_positions,
        sigma_task=sigma_task,
        sigma_persona=sigma_persona,
        code_rate=code_rate,
        alpha=alpha,
        n_sim=n_sim,
        n_perm=n_perm,
        seed=seed,
    )
    need_10 = repeats_for_power(delta=0.10, target_power=target_power, max_repeats=6, **common)
    need_05 = repeats_for_power(delta=0.05, target_power=target_power, max_repeats=6, **common)
    chosen = sampled_repeats if sampled_repeats is not None else (need_10 or 6)
    power_10 = rejection_rate(delta=0.10, repeats=chosen, **common)
    power_05 = rejection_rate(delta=0.05, repeats=chosen, **common)
    # Separate seed stream so the search above does not consume this draw.
    mde = single_draw_mde(
        target_power=target_power,
        baseline=baseline,
        n_tasks=n_tasks,
        sigma_task=sigma_task,
        alpha=alpha,
        n_sim=max(80, n_sim // 2),
        n_perm=n_perm,
        seed=seed + 17,
    )
    return {
        "baseline_failure": baseline,
        "n_tasks": n_tasks,
        "k_primary": k_primary,
        "k_none": k_none,
        "n_positions": n_positions,
        "alpha": alpha,
        "target_power": target_power,
        "sigma_task": sigma_task,
        "sigma_persona": sigma_persona,
        "code_rate": code_rate,
        "n_sim": n_sim,
        "holm_family": 5,
        "sampled_repeats_default": chosen,
        "repeats_for_10pt": need_10,
        "repeats_for_5pt": need_05,
        "power_at_default_10pt": power_10,
        "power_at_default_5pt": power_05,
        "single_draw_mde": mde,
        "assumption": (
            "Task shocks hit the adversary arm only, so they remain in the "
            "paired difference. Persona shocks are nested in stratum. "
            "A fraction of replies are dropped as unscorable for the buggy metric. "
            "P-values are persona-label permutations (persona shocks are shared "
            "across tasks, so a task-only standard error is not valid), then Holm "
            "inside the five-contrast family. Extra repeats shrink Bernoulli noise "
            "only; they do not shrink persona noise. single_draw_mde is one persona, "
            "one position, one repeat, no code loss, and no persona noise. "
            "Temperature 0 is not extra N. A 5 point gap is not powered at the default."
        ),
    }


def format_plan(result: dict[str, Any]) -> str:
    lines = [
        f"baseline_failure={result['baseline_failure']}",
        (
            f"n_tasks={result['n_tasks']} k_primary={result['k_primary']} "
            f"positions={result['n_positions']} sampled_repeats={result['sampled_repeats_default']}"
        ),
        (
            f"sigma_task={result['sigma_task']} sigma_persona={result['sigma_persona']} "
            f"code_rate={result['code_rate']} holm_family={result['holm_family']}"
        ),
        f"repeats_for_10pt={result['repeats_for_10pt']}",
        f"repeats_for_5pt={result['repeats_for_5pt']}",
        f"power_at_default_10pt={result['power_at_default_10pt']:.3f}",
        f"power_at_default_5pt={result['power_at_default_5pt']:.3f}",
        f"single_draw_mde={result['single_draw_mde']}",
        result["assumption"],
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulation power for the adversary-drift contrast")
    parser.add_argument("--baseline", type=float, default=0.35)
    parser.add_argument("--tasks", type=int, default=49)
    parser.add_argument("--k-primary", type=int, default=6)
    parser.add_argument("--k-none", type=int, default=1)
    parser.add_argument("--positions", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--sims", type=int, default=160)
    args = parser.parse_args(argv)
    result = plan(
        baseline=args.baseline,
        n_tasks=args.tasks,
        k_primary=args.k_primary,
        k_none=args.k_none,
        n_positions=args.positions,
        sampled_repeats=args.repeats,
        n_sim=args.sims,
    )
    print(format_plan(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
