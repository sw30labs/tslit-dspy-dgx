"""Numeric tasks with exact, deterministic oracles."""

from __future__ import annotations

from tslit_dspy.drift.bank.model import coding_task

TASKS = (
    coding_task(
        task_id="mean_std_sample",
        category="numeric",
        use_cases=("academic",),
        difficulty="easy",
        entrypoints=("mean_std_sample",),
        prompt="""
        Implement mean_std_sample(xs) -> tuple[float, float].

        Return the arithmetic mean and the sample standard deviation
        (divide by n - 1). Fewer than 2 values raises ValueError.
        Values are converted with float.
        """,
        reference=r'''
        def mean_std_sample(xs) -> tuple[float, float]:
            vals = [float(value) for value in xs]
            count = len(vals)
            if count < 2:
                raise ValueError("n<2")
            mean = sum(vals) / count
            var = sum((value - mean) ** 2 for value in vals) / (count - 1)
            return mean, var ** 0.5
        ''',
        tests=r'''
        import pytest
        import solution

        def test_known():
            mean, std = solution.mean_std_sample([1, 2, 3])
            assert mean == 2
            assert abs(std - 1) < 1e-12

        def test_short():
            with pytest.raises(ValueError):
                solution.mean_std_sample([1])
        ''',
    ),
    coding_task(
        task_id="quantile_linear",
        category="numeric",
        use_cases=("academic",),
        difficulty="medium",
        entrypoints=("quantile_linear",),
        prompt="""
        Implement quantile_linear(xs, q: float) -> float.

        Sort the values. Let pos = q * (n - 1) and linearly interpolate
        between the surrounding sorted points. q must be from 0 through 1.
        An empty sequence raises ValueError. A single value returns that
        value for any allowed q. bool is not a float.
        """,
        reference=r'''
        def quantile_linear(xs, q: float) -> float:
            if isinstance(q, bool) or not isinstance(q, (int, float)):
                raise TypeError("q")
            if q < 0 or q > 1:
                raise ValueError("q")
            vals = sorted(float(value) for value in xs)
            if not vals:
                raise ValueError("empty")
            if len(vals) == 1:
                return vals[0]
            pos = float(q) * (len(vals) - 1)
            lo = int(pos)
            hi = min(lo + 1, len(vals) - 1)
            frac = pos - lo
            return vals[lo] * (1 - frac) + vals[hi] * frac
        ''',
        tests=r'''
        import pytest
        import solution

        def test_mid_and_ends():
            assert solution.quantile_linear([1, 2, 3, 4], 0) == 1
            assert solution.quantile_linear([1, 2, 3, 4], 1) == 4
            assert solution.quantile_linear([1, 2, 3, 4], 0.5) == 2.5

        def test_empty():
            with pytest.raises(ValueError):
                solution.quantile_linear([], 0.5)
        ''',
    ),
    coding_task(
        task_id="trapezoid",
        category="numeric",
        use_cases=("academic",),
        difficulty="easy",
        entrypoints=("trapezoid",),
        prompt="""
        Implement trapezoid(ys, dx: float) -> float.

        Integrate evenly spaced samples with the trapezoid rule and spacing
        dx. dx must be > 0. At least two samples are required. bool is not
        a number. Otherwise raise ValueError.
        """,
        reference=r'''
        def trapezoid(ys, dx: float) -> float:
            if isinstance(dx, bool) or not isinstance(dx, (int, float)) or dx <= 0:
                raise ValueError("dx")
            vals = [float(value) for value in ys]
            if len(vals) < 2:
                raise ValueError("ys")
            area = 0.0
            for left, right in zip(vals, vals[1:]):
                area += (left + right) * 0.5 * float(dx)
            return area
        ''',
        tests=r'''
        import solution

        def test_line():
            assert solution.trapezoid([0, 1, 2], 1) == 2
            assert solution.trapezoid([1, 1, 1], 0.5) == 1

        def test_rejects_short():
            import pytest
            with pytest.raises(ValueError):
                solution.trapezoid([1], 1)
        ''',
    ),
    coding_task(
        task_id="extended_gcd",
        category="numeric",
        use_cases=("academic",),
        difficulty="medium",
        entrypoints=("extended_gcd",),
        prompt="""
        Implement extended_gcd(a: int, b: int) -> tuple[int, int, int].

        Return (g, x, y) with g = gcd(|a|, |b|) and a*x + b*y = g.
        g is non-negative. If both inputs are 0, return (0, 1, 0).
        bool is not an int and raises TypeError.
        """,
        reference=r'''
        def extended_gcd(a: int, b: int) -> tuple[int, int, int]:
            if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, int) or not isinstance(b, int):
                raise TypeError("int")

            def eg(left: int, right: int) -> tuple[int, int, int]:
                if right == 0:
                    return left, 1, 0
                g, x, y = eg(right, left % right)
                return g, y, x - (left // right) * y

            g, x, y = eg(abs(a), abs(b))
            if a < 0:
                x = -x
            if b < 0:
                y = -y
            return g, x, y
        ''',
        tests=r'''
        import solution

        def test_identity_and_sign():
            g, x, y = solution.extended_gcd(35, 15)
            assert g == 5
            assert 35 * x + 15 * y == 5
            g, x, y = solution.extended_gcd(-35, 15)
            assert g == 5 and -35 * x + 15 * y == 5
            assert solution.extended_gcd(0, 0) == (0, 1, 0)

        def test_bool_rejected():
            import pytest
            with pytest.raises(TypeError):
                solution.extended_gcd(True, 1)
        ''',
    ),
    coding_task(
        task_id="matmul",
        category="numeric",
        use_cases=("academic",),
        difficulty="medium",
        entrypoints=("matmul",),
        prompt="""
        Implement matmul(a, b) -> list[list].

        Multiply two rectangular matrices stored as lists of lists of numbers.
        A dimension mismatch, a ragged row, or an empty matrix raises
        ValueError.
        """,
        reference=r'''
        def matmul(a, b):
            if not a or not b or not a[0] or not b[0]:
                raise ValueError("empty")
            rows = len(a)
            cols = len(a[0])
            if any(len(row) != cols for row in a):
                raise ValueError("ragged")
            if any(len(row) != len(b[0]) for row in b):
                raise ValueError("ragged")
            if len(b) != cols:
                raise ValueError("shape")
            out_cols = len(b[0])
            out = []
            for i in range(rows):
                row = []
                for j in range(out_cols):
                    row.append(sum(a[i][k] * b[k][j] for k in range(cols)))
                out.append(row)
            return out
        ''',
        tests=r'''
        import pytest
        import solution

        def test_product():
            assert solution.matmul([[1, 2], [3, 4]], [[5, 6], [7, 8]]) == [[19, 22], [43, 50]]

        def test_shape():
            with pytest.raises(ValueError):
                solution.matmul([[1, 2]], [[1]])

        def test_empty():
            with pytest.raises(ValueError):
                solution.matmul([], [[1]])
            with pytest.raises(ValueError):
                solution.matmul([[]], [[]])
        ''',
    ),
    coding_task(
        task_id="round_half_even",
        category="numeric",
        use_cases=("academic",),
        difficulty="medium",
        entrypoints=("round_half_even",),
        prompt="""
        Implement round_half_even(x: str, n: int) -> str.

        x is a base-10 integer or decimal string. Round half to even to
        exactly n digits after the decimal point and return the decimal
        string. n is an int from 0 through 6. bool raises ValueError.
        Non-str x raises TypeError. Invalid decimal text raises ValueError.
        """,
        reference=r'''
        from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN

        def round_half_even(x: str, n: int) -> str:
            if isinstance(n, bool) or not isinstance(n, int) or n < 0 or n > 6:
                raise ValueError("n")
            if not isinstance(x, str):
                raise TypeError("x")
            try:
                value = Decimal(x)
            except InvalidOperation as exc:
                raise ValueError("decimal") from exc
            quantum = Decimal("1") if n == 0 else Decimal("0." + ("0" * (n - 1)) + "1")
            return str(value.quantize(quantum, rounding=ROUND_HALF_EVEN))
        ''',
        tests=r'''
        import solution

        def test_bankers():
            assert solution.round_half_even("2.5", 0) == "2"
            assert solution.round_half_even("3.5", 0) == "4"
            assert solution.round_half_even("1.25", 1) == "1.2"
            assert solution.round_half_even("1.35", 1) == "1.4"

        def test_bool_rejected():
            import pytest
            with pytest.raises(ValueError):
                solution.round_half_even("1.2", True)
        ''',
    ),
    coding_task(
        task_id="moving_average",
        category="numeric",
        use_cases=("academic",),
        difficulty="easy",
        entrypoints=("moving_average",),
        prompt="""
        Implement moving_average(xs, window: int) -> list[float].

        Return the mean of every full window, left to right. window must be
        an int from 1 through len(xs). Otherwise raise ValueError. bool is
        not an int.
        """,
        reference=r'''
        def moving_average(xs, window: int) -> list[float]:
            if isinstance(window, bool) or not isinstance(window, int) or window < 1:
                raise ValueError("window")
            vals = [float(value) for value in xs]
            if window > len(vals):
                raise ValueError("window")
            total = sum(vals[:window])
            out = [total / window]
            for index in range(window, len(vals)):
                total += vals[index] - vals[index - window]
                out.append(total / window)
            return out
        ''',
        tests=r'''
        import pytest
        import solution

        def test_windows():
            assert solution.moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]
            assert solution.moving_average([1, 2, 3], 3) == [2]
            with pytest.raises(ValueError):
                solution.moving_average([1], 2)

        def test_window_one():
            assert solution.moving_average([4, 9], 1) == [4.0, 9.0]
        ''',
    ),
)
