"""Sample-size planning for the paired task-level contrast.

The planning model treats persona-by-position draws inside a task as
independent Bernoulli noise around a shared stratum shift, after task
difficulty cancels by pairing. That is the optimistic bound. If the
within-task contrast is perfectly correlated, extra personas do not help
and the detectable effect is the single-draw figure printed beside it.

Greedy temperature-0 repeats are not counted as extra N. Only the sampled
temperature contributes repeats.
"""

from __future__ import annotations

import argparse
import math
from typing import Any


def norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF via binary search on erf."""
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


def _z_sum(alpha: float, power: float) -> float:
    return norm_ppf(1.0 - alpha / 2.0) + norm_ppf(power)


def variance_pair(baseline: float, delta: float) -> float:
    p0 = baseline
    p1 = baseline + delta
    if not 0.0 < p0 < 1.0 or not 0.0 < p1 < 1.0:
        raise ValueError("rates must stay inside (0, 1)")
    return p0 * (1.0 - p0) + p1 * (1.0 - p1)


def required_repeats(
    *,
    baseline: float,
    delta: float,
    n_tasks: int,
    k_arm_a: int,
    k_arm_b: int,
    n_positions: int = 2,
    alpha: float = 0.05,
    power: float = 0.80,
    rho: float = 0.0,
) -> dict[str, Any]:
    """Repeats of the sampled temperature for a paired task-level difference.

    Each task contributes one paired difference of stratum means.
    n in an arm is k_personas * n_positions * repeats.
    rho is a planning correlation between the two arm means inside a task
    (0 is conservative for the measurement-error term).
    """
    if min(n_tasks, k_arm_a, k_arm_b, n_positions) < 1:
        raise ValueError("counts must be positive")
    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must be in [0, 1)")
    z = _z_sum(alpha, power)
    se2 = (delta / z) ** 2
    var = variance_pair(baseline, delta) * (1.0 - rho)
    # Var(task difference) = (v_a / n_a + v_b / n_b) = weighted / (positions * repeats)
    # Split var back into the two Bernoulli pieces proportionally to the rates.
    p0 = baseline
    p1 = baseline + delta
    v0 = p0 * (1.0 - p0) * (1.0 - rho)
    v1 = p1 * (1.0 - p1) * (1.0 - rho)
    per_repeat = (v0 / k_arm_a + v1 / k_arm_b) / n_positions
    repeats = math.ceil(per_repeat / (se2 * n_tasks) - 1e-12)
    repeats = max(1, repeats)
    return {
        "delta": delta,
        "required_repeats": repeats,
        "variance_sum": var,
        "z": z,
    }


def mde_at_repeats(
    *,
    baseline: float,
    repeats: int,
    n_tasks: int,
    k_arm_a: int,
    k_arm_b: int,
    n_positions: int = 2,
    alpha: float = 0.05,
    power: float = 0.80,
    rho: float = 0.0,
) -> float:
    """Approximate detectable absolute risk difference (same variance at baseline)."""
    z = _z_sum(alpha, power)
    p = baseline
    v = p * (1.0 - p) * (1.0 - rho)
    n_a = k_arm_a * n_positions * repeats
    n_b = k_arm_b * n_positions * repeats
    var_task = v / n_a + v / n_b
    se = math.sqrt(var_task / n_tasks)
    return z * se


def plan(
    *,
    baseline: float = 0.35,
    n_tasks: int = 49,
    k_primary: int = 6,
    k_none: int = 1,
    n_positions: int = 2,
    sampled_repeats: int = 3,
    alpha: float = 0.05,
    power: float = 0.80,
    rho: float = 0.0,
) -> dict[str, Any]:
    primary = {
        str(delta): required_repeats(
            baseline=baseline,
            delta=delta,
            n_tasks=n_tasks,
            k_arm_a=k_primary,
            k_arm_b=k_primary,
            n_positions=n_positions,
            alpha=alpha,
            power=power,
            rho=rho,
        )
        for delta in (0.05, 0.10)
    }
    versus_none = {
        str(delta): required_repeats(
            baseline=baseline,
            delta=delta,
            n_tasks=n_tasks,
            k_arm_a=k_primary,
            k_arm_b=k_none,
            n_positions=n_positions,
            alpha=alpha,
            power=power,
            rho=rho,
        )
        for delta in (0.05, 0.10)
    }
    return {
        "baseline_failure": baseline,
        "n_tasks": n_tasks,
        "k_primary": k_primary,
        "k_none": k_none,
        "n_positions": n_positions,
        "alpha": alpha,
        "power": power,
        "rho": rho,
        "sampled_repeats_default": sampled_repeats,
        "primary_equal_arms": primary,
        "versus_none": versus_none,
        "mde_primary_at_default": mde_at_repeats(
            baseline=baseline,
            repeats=sampled_repeats,
            n_tasks=n_tasks,
            k_arm_a=k_primary,
            k_arm_b=k_primary,
            n_positions=n_positions,
            alpha=alpha,
            power=power,
            rho=rho,
        ),
        "mde_versus_none_at_default": mde_at_repeats(
            baseline=baseline,
            repeats=sampled_repeats,
            n_tasks=n_tasks,
            k_arm_a=k_primary,
            k_arm_b=k_none,
            n_positions=n_positions,
            alpha=alpha,
            power=power,
            rho=rho,
        ),
        "mde_single_draw": mde_at_repeats(
            baseline=baseline,
            repeats=1,
            n_tasks=n_tasks,
            k_arm_a=1,
            k_arm_b=1,
            n_positions=1,
            alpha=alpha,
            power=power,
            rho=rho,
        ),
        "assumption": (
            "Optimistic: independent Bernoulli noise within a task after pairing. "
            "mde_single_draw is the conservative bound if persona replicates are "
            "perfectly correlated. Temperature 0 is not extra N."
        ),
    }


def format_plan(result: dict[str, Any]) -> str:
    lines = [
        f"baseline_failure={result['baseline_failure']}",
        (
            f"n_tasks={result['n_tasks']} k_primary={result['k_primary']} "
            f"positions={result['n_positions']} sampled_repeats={result['sampled_repeats_default']}"
        ),
        f"alpha={result['alpha']} power={result['power']} rho={result['rho']}",
    ]
    for label, block in (
        ("primary_equal_arms", result["primary_equal_arms"]),
        ("versus_none", result["versus_none"]),
    ):
        for delta, row in block.items():
            lines.append(
                f"{label} delta={delta} required_repeats={row['required_repeats']}"
            )
    lines.append(f"mde_primary_at_default={result['mde_primary_at_default']:.4f}")
    lines.append(f"mde_versus_none_at_default={result['mde_versus_none_at_default']:.4f}")
    lines.append(f"mde_single_draw={result['mde_single_draw']:.4f}")
    lines.append(result["assumption"])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Power for the adversary-drift contrast")
    parser.add_argument("--baseline", type=float, default=0.35)
    parser.add_argument("--tasks", type=int, default=49)
    parser.add_argument("--k-primary", type=int, default=6)
    parser.add_argument("--k-none", type=int, default=1)
    parser.add_argument("--positions", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--power", type=float, default=0.80)
    parser.add_argument("--rho", type=float, default=0.0)
    args = parser.parse_args(argv)
    result = plan(
        baseline=args.baseline,
        n_tasks=args.tasks,
        k_primary=args.k_primary,
        k_none=args.k_none,
        n_positions=args.positions,
        sampled_repeats=args.repeats,
        alpha=args.alpha,
        power=args.power,
        rho=args.rho,
    )
    print(format_plan(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
