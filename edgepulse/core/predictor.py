import ctypes
import platform
from pathlib import Path
import numpy as np

class CppPredictor:
    def __init__(self, alpha: float = 0.35):
        self.alpha = float(alpha)
        root = Path(__file__).resolve().parents[2]  # repo root

        libname = "libpredictor.dylib" if platform.system() == "Darwin" else "libpredictor.so"
        libpath = root / libname
        if not libpath.exists():
            raise FileNotFoundError(f"Missing {libpath}. Run: make")

        self.lib = ctypes.CDLL(str(libpath))
        self.lib.predict_next.argtypes = [ctypes.POINTER(ctypes.c_double), ctypes.c_int, ctypes.c_double]
        self.lib.predict_next.restype = ctypes.c_double

    def predict_next(self, window) -> float:
        w = np.asarray(window, dtype=np.float64)
        ptr = w.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        return float(self.lib.predict_next(ptr, int(len(w)), ctypes.c_double(self.alpha)))
