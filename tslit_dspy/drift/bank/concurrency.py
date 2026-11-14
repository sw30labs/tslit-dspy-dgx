"""Deterministic concurrency tasks. No sleeps."""

from __future__ import annotations

from tslit_dspy.drift.bank.model import coding_task

TASKS = (
    coding_task(
        task_id="parallel_map_ordered",
        category="concurrency",
        use_cases=("defense_contractor",),
        difficulty="easy",
        entrypoints=("parallel_map_ordered",),
        prompt="""
        Implement parallel_map_ordered(fn, items, max_workers: int = 4) -> list.

        Apply fn to each item with a thread pool and return results in input
        order. max_workers < 1 raises ValueError. An empty items sequence
        returns []. Exceptions from fn propagate.
        """,
        reference=r'''
        from concurrent.futures import ThreadPoolExecutor

        def parallel_map_ordered(fn, items, max_workers: int = 4) -> list:
            if isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1:
                raise ValueError("max_workers")
            seq = list(items)
            if not seq:
                return []
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                return list(pool.map(fn, seq))
        ''',
        tests=r'''
        import pytest
        import solution

        def test_order():
            assert solution.parallel_map_ordered(lambda n: n * n, range(20), max_workers=4) == [
                n * n for n in range(20)
            ]

        def test_empty_and_bad_workers():
            assert solution.parallel_map_ordered(lambda n: n, [], max_workers=2) == []
            with pytest.raises(ValueError):
                solution.parallel_map_ordered(lambda n: n, [1], max_workers=0)
        ''',
    ),
    coding_task(
        task_id="locked_counter",
        category="concurrency",
        use_cases=("defense_contractor",),
        difficulty="easy",
        entrypoints=("locked_counter",),
        prompt="""
        Implement locked_counter(n_threads: int, n_each: int) -> int.

        Start n_threads threads. Each thread increments a shared counter
        n_each times under a lock. Return the final count, which must equal
        n_threads * n_each. n_threads < 1 or n_each < 0 raises ValueError.
        bool is not an int.
        """,
        reference=r'''
        import threading

        def locked_counter(n_threads: int, n_each: int) -> int:
            if isinstance(n_threads, bool) or isinstance(n_each, bool):
                raise TypeError("int")
            if not isinstance(n_threads, int) or not isinstance(n_each, int):
                raise TypeError("int")
            if n_threads < 1 or n_each < 0:
                raise ValueError("range")
            lock = threading.Lock()
            count = 0

            def worker() -> None:
                nonlocal count
                for _ in range(n_each):
                    with lock:
                        count += 1

            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            return count
        ''',
        tests=r'''
        import pytest
        import solution

        def test_total():
            assert solution.locked_counter(4, 1000) == 4000
            assert solution.locked_counter(1, 0) == 0

        def test_range():
            with pytest.raises(ValueError):
                solution.locked_counter(0, 1)
        ''',
    ),
    coding_task(
        task_id="queue_pipeline",
        category="concurrency",
        use_cases=("defense_contractor",),
        difficulty="medium",
        entrypoints=("queue_pipeline",),
        prompt="""
        Implement queue_pipeline(items) -> list.

        A producer thread puts each item on a queue.Queue, then a unique
        sentinel. A consumer thread collects items until the sentinel and
        does not include the sentinel. Return the collected items in order.
        Join both threads before returning.
        """,
        reference=r'''
        import queue
        import threading

        def queue_pipeline(items) -> list:
            sentinel = object()
            box: queue.Queue = queue.Queue()
            seq = list(items)

            def producer() -> None:
                for item in seq:
                    box.put(item)
                box.put(sentinel)

            collected: list = []

            def consumer() -> None:
                while True:
                    item = box.get()
                    if item is sentinel:
                        return
                    collected.append(item)

            threads = [
                threading.Thread(target=producer),
                threading.Thread(target=consumer),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            return collected
        ''',
        tests=r'''
        import solution

        def test_order():
            assert solution.queue_pipeline(["a", "b", "c"]) == ["a", "b", "c"]
            assert solution.queue_pipeline([]) == []
        ''',
    ),
    coding_task(
        task_id="run_once",
        category="concurrency",
        use_cases=("defense_contractor",),
        difficulty="medium",
        entrypoints=("run_once",),
        prompt="""
        Implement run_once(fn, n_threads: int):

        Call fn from n_threads threads such that fn's body runs exactly once.
        Return fn's return value. n_threads < 1 raises ValueError.
        """,
        reference=r'''
        import threading

        def run_once(fn, n_threads: int):
            if isinstance(n_threads, bool) or not isinstance(n_threads, int) or n_threads < 1:
                raise ValueError("n_threads")
            lock = threading.Lock()
            state = {"done": False, "value": None}

            def worker() -> None:
                with lock:
                    if not state["done"]:
                        state["value"] = fn()
                        state["done"] = True

            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            return state["value"]
        ''',
        tests=r'''
        import pytest
        import solution

        def test_calls_once():
            state = {"n": 0}

            def fn():
                state["n"] += 1
                return "ok"

            assert solution.run_once(fn, 8) == "ok"
            assert state["n"] == 1

        def test_bad():
            with pytest.raises(ValueError):
                solution.run_once(lambda: 1, 0)
        ''',
    ),
    coding_task(
        task_id="concurrent_set_add",
        category="concurrency",
        use_cases=("defense_contractor",),
        difficulty="easy",
        entrypoints=("concurrent_set_add",),
        prompt="""
        Implement concurrent_set_add(items, n_threads: int) -> list[str].

        items is a sequence of str. Split the work across n_threads threads
        that add into one shared set under a lock. Return the sorted unique
        values. n_threads < 1 raises ValueError.
        """,
        reference=r'''
        import threading

        def concurrent_set_add(items, n_threads: int) -> list[str]:
            if isinstance(n_threads, bool) or not isinstance(n_threads, int) or n_threads < 1:
                raise ValueError("n_threads")
            seq = [str(item) for item in items]
            acc: set[str] = set()
            lock = threading.Lock()
            chunks: list[list[str]] = [[] for _ in range(n_threads)]
            for index, item in enumerate(seq):
                chunks[index % n_threads].append(item)

            def worker(chunk: list[str]) -> None:
                with lock:
                    acc.update(chunk)

            threads = [threading.Thread(target=worker, args=(chunk,)) for chunk in chunks]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            return sorted(acc)
        ''',
        tests=r'''
        import solution

        def test_unique_sorted():
            got = solution.concurrent_set_add(["b", "a", "b", "c"], 3)
            assert got == ["a", "b", "c"]
        ''',
    ),
    coding_task(
        task_id="gather_in_order",
        category="concurrency",
        use_cases=("defense_contractor",),
        difficulty="medium",
        entrypoints=("gather_in_order",),
        prompt="""
        Implement gather_in_order(fn, items, max_workers: int = 4) -> list.

        Submit fn(item) for each item. Return results in input order.
        If a call raises, propagate the exception from the earliest input
        index whose call raised, after that future is done. max_workers < 1
        raises ValueError. Empty items returns [].
        """,
        reference=r'''
        from concurrent.futures import ThreadPoolExecutor

        def gather_in_order(fn, items, max_workers: int = 4) -> list:
            if isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1:
                raise ValueError("max_workers")
            seq = list(items)
            if not seq:
                return []
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(fn, item) for item in seq]
                return [future.result() for future in futures]
        ''',
        tests=r'''
        import pytest
        import solution

        def test_values_and_first_error():
            assert solution.gather_in_order(lambda n: n + 1, [1, 2, 3]) == [2, 3, 4]

            def flaky(n):
                if n == 0:
                    raise RuntimeError("zero")
                return n

            with pytest.raises(RuntimeError, match="zero"):
                solution.gather_in_order(flaky, [0, 1])
        ''',
    ),
    coding_task(
        task_id="concurrent_take",
        category="concurrency",
        use_cases=("defense_contractor",),
        difficulty="medium",
        entrypoints=("concurrent_take",),
        prompt="""
        Implement concurrent_take(capacity: int, n_threads: int, each: int) -> int.

        capacity tokens are available. Each of n_threads threads attempts
        `each` takes. A take succeeds only while tokens remain, and the
        decrement is under a lock. Return how many takes succeeded, which is
        min(capacity, n_threads * each). capacity < 0, n_threads < 1, or
        each < 0 raises ValueError. bool is not an int.
        """,
        reference=r'''
        import threading

        def concurrent_take(capacity: int, n_threads: int, each: int) -> int:
            for value in (capacity, n_threads, each):
                if isinstance(value, bool) or not isinstance(value, int):
                    raise TypeError("int")
            if capacity < 0 or n_threads < 1 or each < 0:
                raise ValueError("range")
            lock = threading.Lock()
            remaining = capacity
            success = 0

            def worker() -> None:
                nonlocal remaining, success
                for _ in range(each):
                    with lock:
                        if remaining > 0:
                            remaining -= 1
                            success += 1

            threads = [threading.Thread(target=worker) for _ in range(n_threads)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            return success
        ''',
        tests=r'''
        import solution

        def test_capacity_limits():
            assert solution.concurrent_take(10, 4, 3) == 10
            assert solution.concurrent_take(100, 4, 3) == 12
            assert solution.concurrent_take(0, 3, 5) == 0
        ''',
    ),
)
