# EdgePulse — Real-Time Sensor Prediction + Anomaly Alerts (Edge-Ready)

EdgePulse is a lightweight edge monitoring system that streams sensor time-series data, predicts the next reading, and flags anomalies (spikes, dropouts, drift) in real time. It combines a Python FastAPI service + Streamlit dashboard with a low-latency C++ predictor exposed to Python via `ctypes`.

![EdgePulse Dashboard](assets/edgepulse-dashboard.png)

## Why this matters (Hardware/Systems)
- Real-time pipeline: **ingest → buffer → predict → detect → alert**
- Edge-friendly design: CPU-only inference, minimal memory via ring buffers
- C++ performance + Python product layer (API + UI)

## Features
- Per-sensor rolling window (circular ring buffer)
- Next-step forecasting: EWMA + short-horizon trend (**C++**)
- Python wrapper via shared library (`.so/.dylib`) + `ctypes`
- Error-based anomaly scoring + live alert feed
- Sensor simulator for repeatable demos

## Repo Structure
