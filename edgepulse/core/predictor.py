"""Next-step forecaster: a fast C++ core with a pure-Python fallback.

The forecasting math (EWMA level + short-horizon trend) lives in
``cpp/predictor.cpp`` and is called from Python via ``ctypes``. On a fresh
machine (including Streamlit Cloud) the shared library may not exist yet, so we
compile it on first use. If no C++ compiler is available at all, we transparently
fall back to an identical implementation in pure Python.

``get_predictor()`` returns the predictor plus a label of which engine is live,
so the UI can show it honestly ("⚡ C++ engine" vs "🐍 Python fallback").
"""

from __future__ import annotations

import ctypes
import platform
import shutil
import subprocess
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]          # repo root
_LIBNAME = "libpredictor.dylib" if platform.system() == "Darwin" else "libpredictor.so"
_LIBPATH = _ROOT / _LIBNAME


def _compile_library() -> None:
    """Compile cpp/predictor.cpp into the shared library if it's missing."""
    if _LIBPATH.exists():
        return
    cxx = next((c for c in ("c++", "g++", "clang++") if shutil.which(c)), None)
    if cxx is None:
        raise RuntimeError("no C++ compiler found")

    if platform.system() == "Darwin":
        shared_flag = "-dynamiclib"
    else:
        shared_flag = "-shared"

    cmd = [cxx, "-O3", "-std=c++17", "-fPIC", shared_flag,
           "-o", str(_LIBPATH), str(_ROOT / "cpp" / "predictor.cpp")]
    subprocess.run(cmd, check=True, capture_output=True, cwd=_ROOT)


class CppPredictor:
    """Calls the compiled C++ ``predict_next`` through ctypes."""

    def __init__(self, alpha: float = 0.35):
        self.alpha = float(alpha)
        _compile_library()
        self.lib = ctypes.CDLL(str(_LIBPATH))
        self.lib.predict_next.argtypes = [
            ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.c_double,
        ]
        self.lib.predict_next.restype = ctypes.c_double

    def predict_next(self, window) -> float:
        w = np.asarray(window, dtype=np.float64)
        ptr = w.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        return float(self.lib.predict_next(ptr, int(len(w)), ctypes.c_double(self.alpha)))


class PyPredictor:
    """Pure-Python twin of the C++ core — identical math, used as a fallback."""

    def __init__(self, alpha: float = 0.35):
        self.alpha = float(alpha)

    def predict_next(self, window) -> float:
        w = [float(x) for x in window]
        n = len(w)
        if n <= 0:
            return 0.0
        if n == 1:
            return w[0]

        level = w[0]
        for i in range(1, n):
            level = self.alpha * w[i] + (1.0 - self.alpha) * level

        k = min(n, 6)
        trend = sum(w[i] - w[i - 1] for i in range(n - k + 1, n)) / (k - 1)
        return level + trend


def get_predictor(alpha: float = 0.35) -> tuple[object, str]:
    """Return (predictor, engine_label). Prefer C++, fall back to Python."""
    try:
        return CppPredictor(alpha), "cpp"
    except Exception:
        return PyPredictor(alpha), "python"
