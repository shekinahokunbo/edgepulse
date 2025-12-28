import time
import streamlit as st
import requests

st.set_page_config(page_title="EdgePulse", layout="wide")
st.title("EdgePulse — Real-Time Sensor Prediction + Anomaly Alerts")

# Controls
refresh_ms = st.sidebar.slider("Refresh interval (ms)", 200, 2000, 500, 100)
auto = st.sidebar.toggle("Auto refresh", value=True)

col1, col2 = st.columns([2, 1])
table_slot = col1.empty()
alert_slot = col2.empty()

def fetch_latest():
    resp = requests.get("http://127.0.0.1:8000/latest", timeout=3)
    resp.raise_for_status()
    return resp.json()

def render_once():
    try:
        data = fetch_latest()
    except Exception as e:
        table_slot.error(f"Failed to fetch data: {e}")
        alert_slot.info("Make sure the API is running on http://127.0.0.1:8000 and the simulator is sending data.")
        return

    rows = []
    alerts = []
    for sid, p in data.items():
        rows.append({
            "sensor_id": sid,
            "value": p.get("value"),
            "pred": p.get("pred"),
            "err": p.get("err"),
            "anomaly": p.get("anomaly"),
            "z": p.get("z"),
        })
        if p.get("anomaly"):
            try:
                zval = float(p.get("z", 0.0))
                errv = p.get("err")
                alerts.append(f"🚨 {sid} anomaly | err={errv} | z={zval:.2f}")
            except Exception:
                alerts.append(f"🚨 {sid} anomaly | err={p.get('err')} | z={p.get('z')}")

    with table_slot.container():
        st.subheader("Latest readings")
        st.dataframe(rows, use_container_width=True)

    with alert_slot.container():
        st.subheader("Alerts")
        if alerts:
            for a in alerts[:10]:
                st.error(a)
        else:
            st.success("No anomalies right now.")

# Render
render_once()

# Manual refresh button
if st.button("Refresh now"):
    st.rerun()

# Auto refresh
if auto:
    time.sleep(refresh_ms / 1000.0)
    st.rerun()
