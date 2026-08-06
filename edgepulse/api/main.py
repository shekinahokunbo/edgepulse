import time
from fastapi import FastAPI
from pydantic import BaseModel

from edgepulse.core.ringbuffer import RingBuffer
from edgepulse.core.predictor import get_predictor
from edgepulse.core.anomaly import is_anomaly

app = FastAPI(title="EdgePulse API")

WINDOW = 60
ERROR_WIN = 200

predictor, _engine = get_predictor(alpha=0.35)  # C++ if available, else Python

buffers = {}
err_buffers = {}
latest = {}

class Reading(BaseModel):
    sensor_id: str
    ts: float | None = None
    value: float

@app.post("/ingest")
def ingest(r: Reading):
    ts = r.ts if r.ts is not None else time.time()
    sid = r.sensor_id

    if sid not in buffers:
        buffers[sid] = RingBuffer(WINDOW)
        err_buffers[sid] = RingBuffer(ERROR_WIN)

    buffers[sid].append(r.value)

    pred = None
    err = None
    anomaly = False
    z = 0.0

    if len(buffers[sid]) >= 6:
        window = buffers[sid].values()
        pred = predictor.predict_next(window)
        err = abs(r.value - pred)
        err_buffers[sid].append(err)
        anomaly, z = is_anomaly(err_buffers[sid].values())

    payload = {
        "sensor_id": sid,
        "ts": ts,
        "value": r.value,
        "pred": pred,
        "err": err,
        "anomaly": anomaly,
        "z": z,
    }
    latest[sid] = payload
    return payload

@app.get("/latest")
def get_latest():
    return latest
