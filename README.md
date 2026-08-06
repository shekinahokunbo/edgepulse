# ⚡ EdgePulse — Real-Time Forecasting & Anomaly Detection

**EdgePulse streams a live signal, forecasts its next value, and flags anomalies
(spikes, drift, drop-outs) in real time.** The forecasting core is written in
**C++** and called from Python via **`ctypes`**; the rest is a live **Streamlit**
console with a **FastAPI** ingestion service for distributed/edge deployments.

The monitoring pipeline is completely **stream-agnostic** — the same code watches
a temperature probe, a server metric, or a market feed. The hosted demo plugs in
**live cryptocurrency prices** (Coinbase public API, no key) so it works in real
time out of the box.

### ▶️ Live demo
_Deploying on Streamlit Community Cloud — see [Deploy](#deploy) below._

---

## Why it's interesting

- **C++ performance core, Python product layer.** The `predict_next` forecaster
  (EWMA level + short-horizon trend) is C++ compiled to a shared library and
  called through `ctypes` — with a pure-Python fallback so it runs anywhere. The
  UI shows which engine is live.
- **Genuinely real-time.** A `st.fragment(run_every=…)` loop ingests live data
  every second, updates a rolling window, forecasts, and detects anomalies —
  no page reloads.
- **Robust anomaly detection.** Anomalies are flagged with a **median/MAD
  robust z-score** on the prediction-error stream, which resists the outliers a
  plain mean/std would be skewed by.
- **Deploys as a single app.** The whole pipeline runs in-process, so it hosts
  on Streamlit Community Cloud with no separate services.

## How it works

```
 live feed ─▶ ring buffer ─▶ C++ forecaster ─▶ error ─▶ robust z-score ─▶ alerts
 (Coinbase)   (last N pts)    (ctypes)          |err|     (median/MAD)      + live UI
```

1. **Ingest** the latest value from a live stream.
2. **Buffer** it in a fixed-size circular ring buffer (per channel).
3. **Forecast** the next value with the C++ core.
4. **Score** the prediction error against recent errors (robust z-score).
5. **Alert** when the score crosses a sensitivity threshold.

## Repo structure

```
streamlit_app.py            deployment entrypoint (Streamlit Cloud)
edgepulse/
  core/
    predictor.py            C++ (ctypes) forecaster + Python fallback + auto-compile
    ringbuffer.py           fixed-size circular buffer
    anomaly.py              robust median/MAD z-score detector
    sources.py              live data feeds (Coinbase public API)
  dashboard/app.py          real-time Streamlit console (the demo)
  api/main.py               FastAPI ingestion service (distributed/edge path)
cpp/predictor.{cpp,h}       C++ forecasting core
scripts/simulate_sensors.py synthetic sensor generator (for the API path)
Makefile                    builds the C++ shared library
packages.txt                apt build tools for cloud (compiles C++ on deploy)
```

## Run locally

```bash
pip install -r requirements.txt

# Live dashboard (self-contained — compiles the C++ core on first run)
streamlit run streamlit_app.py
```

Optional — the distributed path (separate API + simulator + dashboard):

```bash
make                                        # build the C++ library
uvicorn edgepulse.api.main:app --port 8000  # ingestion API
python scripts/simulate_sensors.py          # feed synthetic sensors
```

## Deploy

Hosts free on [Streamlit Community Cloud](https://share.streamlit.io):

1. Push to GitHub.
2. Create an app pointing at **`streamlit_app.py`**.
3. `requirements.txt` and `packages.txt` (which installs `build-essential`) are
   picked up automatically; the C++ core compiles on first launch, and falls
   back to Python if compilation isn't available.

## Tech stack

`C++ · Python · ctypes · FastAPI · Streamlit · Altair · pandas · NumPy`

---

*Educational project. The crypto feed is used purely as a convenient live data
source — EdgePulse is a general-purpose monitor, not a trading tool.*
