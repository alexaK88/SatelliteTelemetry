# monitoring/dashboard.py

import os
import time
import requests
import streamlit as st
import plotly.express as px

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="Satellite Telemetry Console", layout="wide")
st.title("🛰️ Satellite Telemetry Console")
st.caption("Ground-segment style live monitoring (HK telemetry)")

with st.sidebar:
    st.subheader("Settings")
    api_base = st.text_input("API base URL", value=API_BASE)
    limit = st.slider("History points", min_value=50, max_value=1000, value=300, step=50)
    refresh_s = st.slider("Refresh (seconds)", min_value=0.2, max_value=5.0, value=1.0, step=0.2)
    st.divider()
    st.write("Quick links")
    st.code(f"{api_base}/health")
    st.code(f"{api_base}/telemetry/latest")
    st.code(f"{api_base}/telemetry/recent?limit={limit}")

def fetch_recent(base: str, n: int):
    r = requests.get(f"{base}/telemetry/recent", params={"limit": n}, timeout=3.0)
    r.raise_for_status()
    return r.json()

def status_badge(health: str) -> str:
    if health == "GREEN":
        return "🟢 NOMINAL"
    if health == "YELLOW":
        return "🟡 WARNING"
    return "🔴 CRITICAL"

# --- Auto refresh loop (simple + reliable) ---
placeholder = st.empty()

while True:
    with placeholder.container():
        cols = st.columns([1.2, 1.2, 1.2, 2.4])

        try:
            data = fetch_recent(api_base, limit)
            packets = data["packets"]
            statuses = data["statuses"]

            latest = packets[-1]
            latest_status = statuses[-1]
            health = latest_status["health"]

            # KPIs
            with cols[0]:
                st.metric("Latest SEQ", latest["header"]["seq"])
                st.metric("Health", status_badge(health))

            with cols[1]:
                p = latest["measurements"]["power"]
                st.metric("Battery Voltage (V)", p["battery_voltage_v"])
                st.metric("Battery Current (A)", p["battery_current_a"])

            with cols[2]:
                t = latest["measurements"]["thermal"]["payload_temp_c"]
                cpu = latest["measurements"]["system"]["cpu_load_pct"]
                st.metric("Payload Temp (°C)", t)
                st.metric("CPU Load (%)", cpu)

            # Build time series
            times = [p["header"]["generated_at"] for p in packets]
            voltage = [p["measurements"]["power"]["battery_voltage_v"] for p in packets]
            temp = [p["measurements"]["thermal"]["payload_temp_c"] for p in packets]
            cpu = [p["measurements"]["system"]["cpu_load_pct"] for p in packets]
            rate = [p["measurements"]["adcs"]["angular_rate_deg_s"] for p in packets]
            rssi = [p["measurements"]["comm"]["signal_strength_db"] for p in packets]
            health_series = [s["health"] for s in statuses]

            # Charts
            left, right = st.columns(2)

            with left:
                fig_v = px.line(x=times, y=voltage, labels={"x": "Time (UTC)", "y": "Battery Voltage (V)"})
                st.plotly_chart(fig_v, use_container_width=True)

                fig_t = px.line(x=times, y=temp, labels={"x": "Time (UTC)", "y": "Payload Temp (°C)"})
                st.plotly_chart(fig_t, use_container_width=True)

                fig_r = px.line(x=times, y=rate, labels={"x": "Time (UTC)", "y": "Angular Rate (deg/s)"})
                st.plotly_chart(fig_r, use_container_width=True)

            with right:
                fig_cpu = px.line(x=times, y=cpu, labels={"x": "Time (UTC)", "y": "CPU Load (%)"})
                st.plotly_chart(fig_cpu, use_container_width=True)

                fig_rssi = px.line(x=times, y=rssi, labels={"x": "Time (UTC)", "y": "Signal Strength (dB)"})
                st.plotly_chart(fig_rssi, use_container_width=True)

                # Health timeline
                fig_h = px.scatter(
                    x=times,
                    y=health_series,
                    labels={"x": "Time (UTC)", "y": "Health"},
                )
                st.plotly_chart(fig_h, use_container_width=True)

            st.divider()
            st.subheader("Latest Packet (truncated)")
            st.json(
                {
                    "header": latest["header"],
                    "health": latest_status,
                    "measurements": latest["measurements"],
                },
                expanded=False,
            )

        except Exception as exc:
            st.error(f"Failed to fetch telemetry: {exc}")
            st.info("Make sure FastAPI is running and telemetry is being sent.")
            # Don't crash-loop too hard if API is down
            time.sleep(max(1.0, refresh_s))
            continue

    time.sleep(refresh_s)
