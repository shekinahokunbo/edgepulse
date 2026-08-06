"""EdgePulse — real-time streaming forecaster + anomaly detector (single-file UI).

This dashboard is fully self-contained: it runs the whole pipeline
(ingest → ring buffer → C++ forecast → anomaly detection → alert) in-process and
streams REAL live data, so it deploys to Streamlit Community Cloud as one app —
no separate API/simulator needed. The FastAPI service in ``edgepulse/api`` still
exists for the distributed/edge deployment story; this is the demo-friendly path.
"""

from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path

# Make the package importable no matter how Streamlit launches this file.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import altair as alt
import pandas as pd
import streamlit as st

from edgepulse.core.anomaly import is_anomaly
from edgepulse.core.predictor import get_predictor
from edgepulse.core.ringbuffer import RingBuffer
from edgepulse.core.sources import CHANNELS, fetch_value

# --- palette ---------------------------------------------------------------- #
CYAN = "#22d3ee"
MAGENTA = "#e879f9"
GREEN = "#34d399"
RED = "#fb7185"
AMBER = "#fbbf24"
DIM = "#64748b"

WINDOW = 60        # points fed to the forecaster
ERROR_WIN = 200    # error history for the anomaly detector
HIST = 140         # points shown on the live chart

st.set_page_config(page_title="EdgePulse — live anomaly detection",
                   page_icon="⚡", layout="wide")


# --------------------------------------------------------------------------- #
# Styling — dark, neon, glassmorphic
# --------------------------------------------------------------------------- #
def inject_css() -> None:
    st.markdown(
        f"""
        <style>
          .stApp {{
            background:
              radial-gradient(1200px 600px at 20% -10%, rgba(34,211,238,0.10), transparent 60%),
              radial-gradient(1000px 500px at 100% 0%, rgba(232,121,249,0.10), transparent 55%),
              #06080f;
          }}
          .block-container {{ padding-top: 1.6rem; max-width: 1200px; }}
          html, body, [class*="css"] {{
            font-family: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
          }}
          h1, h2, h3, h4 {{ letter-spacing: 0.02em; }}

          .ep-hero {{
            border: 1px solid rgba(34,211,238,0.25);
            border-radius: 16px;
            padding: 1.1rem 1.4rem;
            background: linear-gradient(135deg, rgba(34,211,238,0.08), rgba(232,121,249,0.06));
            box-shadow: 0 0 40px rgba(34,211,238,0.10) inset;
          }}
          .ep-title {{ font-size: 1.7rem; font-weight: 800; color: #e5faff;
                       text-shadow: 0 0 18px rgba(34,211,238,0.55); }}
          .ep-sub {{ color: #9fb3c8; font-size: 0.95rem; margin-top: 0.15rem; }}

          .ep-card {{
            border: 1px solid rgba(148,163,184,0.18);
            border-radius: 14px;
            padding: 0.9rem 1.05rem;
            background: rgba(17,24,39,0.55);
            backdrop-filter: blur(8px);
            height: 100%;
          }}
          .ep-label {{ color:{DIM}; font-size:0.72rem; text-transform:uppercase;
                       letter-spacing:0.12em; }}
          .ep-value {{ font-size:1.55rem; font-weight:750; margin-top:0.15rem; }}

          .ep-pill {{ display:inline-flex; align-items:center; gap:0.5rem;
                      padding:0.35rem 0.85rem; border-radius:999px; font-weight:700;
                      font-size:0.85rem; }}
          .ep-ok  {{ color:{GREEN}; border:1px solid rgba(52,211,153,0.45);
                     background:rgba(52,211,153,0.08);
                     box-shadow:0 0 18px rgba(52,211,153,0.25); }}
          .ep-bad {{ color:{RED}; border:1px solid rgba(251,113,133,0.55);
                     background:rgba(251,113,133,0.10);
                     box-shadow:0 0 22px rgba(251,113,133,0.45);
                     animation: epflash 1s ease-in-out infinite; }}
          @keyframes epflash {{ 0%,100%{{opacity:1}} 50%{{opacity:0.55}} }}

          .ep-dot {{ height:9px; width:9px; border-radius:50%; background:{GREEN};
                     box-shadow:0 0 10px {GREEN}; animation: eppulse 1.4s infinite; }}
          @keyframes eppulse {{ 0%{{opacity:1}} 50%{{opacity:0.3}} 100%{{opacity:1}} }}

          .ep-engine {{ font-size:0.75rem; color:{CYAN}; border:1px solid rgba(34,211,238,0.35);
                        border-radius:999px; padding:0.2rem 0.6rem; }}
          .ep-alert {{ border-left:3px solid {RED}; background:rgba(251,113,133,0.08);
                       padding:0.4rem 0.7rem; border-radius:6px; margin-bottom:0.4rem;
                       font-size:0.82rem; color:#ffd8de; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
def channel_state(channel: str) -> dict:
    store = st.session_state.setdefault("channels", {})
    if channel not in store:
        store[channel] = {
            "vals": RingBuffer(WINDOW),
            "errs": RingBuffer(ERROR_WIN),
            "hist": deque(maxlen=HIST),
            "alerts": deque(maxlen=12),
        }
    return store[channel]


def fmt(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x:,.2f}"


# --------------------------------------------------------------------------- #
# One live tick: fetch → predict → detect → render
# --------------------------------------------------------------------------- #
def tick(channel: str, z_thresh: float, slots: dict) -> None:
    predictor = st.session_state.predictor
    predictor.alpha = st.session_state.alpha
    cs = channel_state(channel)

    value = fetch_value(channel)
    if value is None:
        slots["status"].markdown(
            f"<span class='ep-pill ep-bad'>⚠ FEED UNAVAILABLE</span>",
            unsafe_allow_html=True)
        return

    # Optional manual anomaly injection (clearly a test), applied to one tick.
    if st.session_state.pop("inject", False):
        value *= 1.05

    cs["vals"].append(value)

    pred = err = None
    anomaly, z = False, 0.0
    if len(cs["vals"]) >= 6:
        pred = predictor.predict_next(cs["vals"].values())
        err = abs(value - pred)
        cs["errs"].append(err)
        anomaly, z = is_anomaly(cs["errs"].values(), z_thresh=z_thresh)

    ts = time.time()
    cs["hist"].append({"ts": ts, "value": value, "pred": pred, "anomaly": anomaly})
    if anomaly:
        cs["alerts"].appendleft(
            f"🚨 {time.strftime('%H:%M:%S', time.localtime(ts))} · "
            f"{channel.split('·')[0].strip()} · z={z:.1f} · err={fmt(err)}")

    _render(channel, cs, value, pred, err, z, anomaly, slots)


def _render(channel, cs, value, pred, err, z, anomaly, slots) -> None:
    calibrating = len(cs["errs"]) < 20

    # Metric cards
    status_html = (
        "<span class='ep-pill ep-bad'>⚠ ANOMALY DETECTED</span>" if anomaly
        else ("<span class='ep-pill ep-ok'>◍ CALIBRATING</span>" if calibrating
              else "<span class='ep-pill ep-ok'>● NOMINAL</span>")
    )
    cards = [
        ("Live value", f"<span style='color:{CYAN}'>{fmt(value)}</span>"),
        ("Predicted next", f"<span style='color:{MAGENTA}'>{fmt(pred)}</span>"),
        ("Prediction error", fmt(err)),
        ("Anomaly score (z)", f"{z:+.2f}" if not calibrating else "—"),
    ]
    cols = "".join(
        f"<div class='ep-card'><div class='ep-label'>{lbl}</div>"
        f"<div class='ep-value'>{val}</div></div>"
        for lbl, val in cards
    )
    slots["metrics"].markdown(
        f"<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:0.7rem'>{cols}</div>",
        unsafe_allow_html=True,
    )
    slots["status"].markdown(status_html, unsafe_allow_html=True)

    # Live chart: actual vs predicted, anomalies glowing
    df = pd.DataFrame(cs["hist"])
    if not df.empty:
        df["time"] = pd.to_datetime(df["ts"], unit="s")
        base = alt.Chart(df).encode(x=alt.X("time:T", title=None,
                                            axis=alt.Axis(format="%H:%M:%S")))
        actual = base.mark_line(color=CYAN, strokeWidth=2).encode(
            y=alt.Y("value:Q", title="value", scale=alt.Scale(zero=False)))
        predicted = base.mark_line(color=MAGENTA, strokeWidth=1.5,
                                   strokeDash=[4, 3]).encode(y="pred:Q")
        layers = [actual, predicted]
        anoms = df[df["anomaly"]]
        if not anoms.empty:
            layers.append(
                alt.Chart(anoms).mark_point(color=RED, size=150, filled=True,
                                            opacity=0.9).encode(
                    x="time:T", y="value:Q"))
        chart = (
            alt.layer(*layers).properties(height=340)
            .configure(background="transparent")
            .configure_axis(grid=True, gridColor="rgba(148,163,184,0.12)",
                            domainColor="rgba(148,163,184,0.3)",
                            labelColor="#94a3b8", titleColor="#94a3b8")
            .configure_view(strokeWidth=0)
        )
        slots["chart"].altair_chart(chart, width="stretch")

    # Alert feed
    if cs["alerts"]:
        feed = "".join(f"<div class='ep-alert'>{a}</div>" for a in cs["alerts"])
    else:
        feed = (f"<div style='color:{DIM};font-size:0.85rem'>No anomalies detected "
                "yet — the stream looks healthy.</div>")
    slots["alerts"].markdown(feed, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    inject_css()

    if "predictor" not in st.session_state:
        predictor, engine = get_predictor(alpha=0.35)
        st.session_state.predictor = predictor
        st.session_state.engine = engine
    st.session_state.setdefault("alpha", 0.35)

    engine_badge = ("⚡ C++ engine (ctypes)" if st.session_state.engine == "cpp"
                    else "🐍 Python fallback")

    st.markdown(
        f"""
        <div class="ep-hero">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.5rem">
            <div>
              <div class="ep-title">⚡ EdgePulse</div>
              <div class="ep-sub">Real-time forecasting &amp; anomaly detection on live streaming data</div>
            </div>
            <div style="display:flex;align-items:center;gap:0.8rem">
              <span class="ep-engine">{engine_badge}</span>
              <span style="display:inline-flex;align-items:center;gap:0.4rem;color:{GREEN};font-size:0.8rem">
                <span class="ep-dot"></span> LIVE
              </span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### ⚙️ Console")
        channel = st.selectbox("Data stream", list(CHANNELS.keys()))
        refresh = st.select_slider("Refresh", options=[1, 2, 3, 5], value=2,
                                   format_func=lambda s: f"{s}s")
        st.session_state.alpha = st.slider("Smoothing α (EWMA)", 0.05, 0.95, 0.35, 0.05)
        z_thresh = st.slider("Anomaly sensitivity (z)", 2.0, 6.0, 3.5, 0.5,
                             help="Lower = more sensitive. Robust MAD z-score threshold.")
        st.markdown("---")
        if st.button("💥 Inject anomaly", width="stretch"):
            st.session_state.inject = True
        if st.button("♻️ Reset stream", width="stretch"):
            st.session_state.pop("channels", None)
        st.markdown("---")
        st.caption("Live prices via Coinbase (no key). The pipeline is stream-agnostic — "
                   "the same code monitors sensors, servers, or markets.")

    st.write("")
    slots = {"status": st.empty(), "metrics": st.empty()}
    st.write("")
    left, right = st.columns([3, 1])
    with left:
        st.markdown("###### 📈 Live signal — actual vs. predicted")
        slots["chart"] = st.empty()
    with right:
        st.markdown("###### 🚨 Alert feed")
        slots["alerts"] = st.empty()

    # Live loop: rerun just this fragment every `refresh` seconds.
    @st.fragment(run_every=refresh)
    def live():
        tick(channel, z_thresh, slots)

    live()


if __name__ == "__main__":
    main()
