"""Benchmark the C++ forecasting core against the pure-Python fallback.

Run from the repo root:
    python scripts/benchmark.py

Reports per-prediction latency and throughput for each engine, and confirms the
two implementations agree numerically. Absolute numbers are machine-dependent;
on a modern laptop the C++ core runs at roughly ~2 us/prediction
(~500K predictions/sec).
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from edgepulse.core.predictor import CppPredictor, PyPredictor

WINDOW = 60
N = 200_000


def bench(predictor, window) -> float:
    """Return microseconds per prediction (best of 3 runs)."""
    def one_run() -> float:
        t0 = time.perf_counter()
        for _ in range(N):
            predictor.predict_next(window)
        return (time.perf_counter() - t0) / N * 1e6

    for _ in range(1000):          # warm up
        predictor.predict_next(window)
    return min(one_run() for _ in range(3))


def main() -> None:
    rng = np.random.default_rng(0)
    window = list(rng.normal(100, 5, size=WINDOW))

    py = PyPredictor(alpha=0.35)
    try:
        cpp = CppPredictor(alpha=0.35)
    except Exception as exc:  # no compiler available
        print(f"C++ engine unavailable ({exc}); benchmarking Python only.")
        cpp = None

    if cpp is not None:
        assert math.isclose(cpp.predict_next(window), py.predict_next(window),
                            rel_tol=1e-9), "engines disagree!"

    print(f"window: {WINDOW} points | calls: {N:,}\n")
    py_us = bench(py, window)
    print(f"Python fallback : {py_us:8.3f} us/prediction  ({1e6/py_us:,.0f}/sec)")
    if cpp is not None:
        cpp_us = bench(cpp, window)
        print(f"C++ (ctypes)    : {cpp_us:8.3f} us/prediction  ({1e6/cpp_us:,.0f}/sec)")
        print(f"\nspeedup vs Python: {py_us / cpp_us:.1f}x")


if __name__ == "__main__":
    main()
