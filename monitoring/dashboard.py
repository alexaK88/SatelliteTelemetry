# monitoring/dashboard.py

import os
import time
from datetime import datetime
from typing import Any

import requests
import streamlit as st
import plotly.express as px
import pandas as pd


API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="Satellite Telemetry Console", layout="wide")
st.title("🛰️ Satellite Telemetry Console")
st.caption("Ground-segment style live monitoring (HK telemetry)")


# ----------------------------
# Sidebar controls
# ----------------------------
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

    st.divider()
    st.subheader("Pass & Gap Detection")
    pass_gap_s = st.slider("New pass if silence > (seconds)", 5, 300, 30, 5)
    show_pass_lines = st.checkbox("Show pass boundaries", value=True)
    show_gap_lines = st.checkbox("Show sequence gap markers", value=True)


# ----------------------------
# Helpers
# ----------------------------
def infer_pass_ids(times: list[datetime], pass_gap_seconds: float) -> list[int]:
    """
    Infer pass_id from inter-arrival time.
    New pass starts if time gap > pass_gap_seconds.
    """
    pass_ids: list[int] = []
    current = 1
    last_t: datetime | None = None

    for t in times:
        if last_t is None:
            pass_ids.append(current)
            last_t = t
            continue

        dt = (t - last_t).total_seconds()
        if dt > pass_gap_seconds:
            current += 1

        pass_ids.append(current)
        last_t = t

    return pass_ids


def detect_seq_gaps(seqs: list[int], times: list[datetime]) -> list[dict[str, Any]]:
    """
    Detect missing packets by sequence gaps.
    Returns list of dicts: {time, gap_size, from_seq, to_seq}
    """
    gaps: list[dict[str, Any]] = []
    for i in range(1, len(seqs)):
        expected = seqs[i - 1] + 1
        if seqs[i] > expected:
            gap_size = seqs[i] - expected
            gaps.append(
                {
                    "time": times[i],
                    "gap_size": gap_size,
                    "from_seq": expected,
                    "to_seq": seqs[i] - 1,
                }
            )
    return gaps


def add_pass_and_gap_markers(
    fig,
    times: list[datetime],
    pass_ids: list[int],
    gaps: list[dict[str, Any]],
    show_pass: bool,
    show_gaps: bool,
):
    """
    Add vertical lines for pass starts and gap detections.
    """
    if not times:
        return fig

    # Pass boundaries: add a vline when pass_id changes
    if show_pass and pass_ids:
        for i in range(1, len(pass_ids)):
            if pass_ids[i] != pass_ids[i - 1]:
                fig.add_vline(
                    x=times[i],
                    annotation_text=f"Pass {pass_ids[i]} start",
                    annotation_position="top left",
                )

    # Gaps: add a vline at the packet where the gap is detected
    if show_gaps and gaps:
        for g in gaps:
            fig.add_vline(
                x=g["time"],
                annotation_text=f"Gap {g['gap_size']} (seq {g['from_seq']}-{g['to_seq']})",
                annotation_position="bottom left",
            )

    return fig


def fetch_recent(base: str, n: int) -> dict:
    r = requests.get(f"{base}/telemetry/recent", params={"limit": n}, timeout=3.0)
    r.raise_for_status()
    return r.json()


def status_badge(health: str) -> str:
    if health == "GREEN":
        return "🟢 NOMINAL"
    if health == "YELLOW":
        return "🟡 WARNING"
    return "🔴 CRITICAL"


def safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def safe_int(x: Any) -> int:
    try:
        return int(x)
    except Exception:
        return 0


# ----------------------------
# Auto refresh loop
# ----------------------------
placeholder = st.empty()

while True:
    with placeholder.container():
        cols = st.columns([1.2, 1.2, 1.2, 2.4])

        try:
            data = fetch_recent(api_base, limit)
            packets = data.get("packets", [])
            statuses = data.get("statuses", [])

            if not packets or not statuses:
                st.warning("No telemetry received yet.")
                time.sleep(refresh_s)
                continue

            latest = packets[-1]
            latest_status = statuses[-1]
            health = latest_status.get("health", "UNKNOWN")

            # ----------------------------
            # KPIs
            # ----------------------------
            with cols[0]:
                st.metric("Latest SEQ", safe_int(latest["header"].get("seq")))
                st.metric("Health", status_badge(health))

            with cols[1]:
                pwr = latest["measurements"]["power"]
                st.metric("Battery Voltage (V)", safe_float(pwr.get("battery_voltage_v")))
                st.metric("Battery Current (A)", safe_float(pwr.get("battery_current_a")))

            with cols[2]:
                tval = safe_float(latest["measurements"]["thermal"].get("payload_temp_c"))
                cpuval = safe_float(latest["measurements"]["system"].get("cpu_load_pct"))
                st.metric("Payload Temp (°C)", tval)
                st.metric("CPU Load (%)", cpuval)

            with cols[3]:
                msgs = latest_status.get("messages", [])
                if isinstance(msgs, list) and msgs:
                    st.subheader("Health messages")
                    for m in msgs[:6]:
                        st.write(f"- {m}")
                else:
                    st.subheader("Health messages")
                    st.write("- (none)")

            # ----------------------------
            # Time series + derived signals
            # ----------------------------
            # Parse timestamps to timezone-aware datetimes
            times = pd.to_datetime(
                [p["header"]["generated_at"] for p in packets],
                utc=True,
                errors="coerce",
            ).to_pydatetime().tolist()

            # Filter out any rows where time failed to parse
            filtered = [(t, p, s) for t, p, s in zip(times, packets, statuses) if t is not None]
            if not filtered:
                st.error("Could not parse any timestamps from telemetry.")
                time.sleep(refresh_s)
                continue

            times, packets, statuses = zip(*filtered)
            times = list(times)
            packets = list(packets)
            statuses = list(statuses)

            seqs = [safe_int(p["header"].get("seq")) for p in packets]

            voltage = [safe_float(p["measurements"]["power"].get("battery_voltage_v")) for p in packets]
            temp = [safe_float(p["measurements"]["thermal"].get("payload_temp_c")) for p in packets]
            cpu = [safe_float(p["measurements"]["system"].get("cpu_load_pct")) for p in packets]
            rate = [safe_float(p["measurements"]["adcs"].get("angular_rate_deg_s")) for p in packets]
            rssi = [safe_float(p["measurements"]["comm"].get("signal_strength_db")) for p in packets]
            health_series = [s.get("health", "UNKNOWN") for s in statuses]

            # Infer passes + detect seq gaps
            pass_ids = infer_pass_ids(times, pass_gap_s)
            gaps = detect_seq_gaps(seqs, times)

            # Packet rate (packets/sec) based on inter-arrival time
            pkt_rate = [0.0]
            for i in range(1, len(times)):
                dt = (times[i] - times[i - 1]).total_seconds()
                pkt_rate.append(0.0 if dt <= 0 else 1.0 / dt)

            # ----------------------------
            # Charts
            # ----------------------------
            left, right = st.columns(2)

            with left:
                fig_rate = px.line(
                    x=times,
                    y=pkt_rate,
                    labels={"x": "Time (UTC)", "y": "Packets/sec"},
                    title="Packet rate",
                )
                fig_rate = add_pass_and_gap_markers(fig_rate, times, pass_ids, gaps, show_pass_lines, show_gap_lines)
                st.plotly_chart(fig_rate, use_container_width=True)

                fig_v = px.line(
                    x=times,
                    y=voltage,
                    labels={"x": "Time (UTC)", "y": "Battery Voltage (V)"},
                    title="Power: Battery voltage",
                )
                fig_v = add_pass_and_gap_markers(fig_v, times, pass_ids, gaps, show_pass_lines, show_gap_lines)
                st.plotly_chart(fig_v, use_container_width=True)

                fig_t = px.line(
                    x=times,
                    y=temp,
                    labels={"x": "Time (UTC)", "y": "Payload Temp (°C)"},
                    title="Thermal: Payload temperature",
                )
                fig_t = add_pass_and_gap_markers(fig_t, times, pass_ids, gaps, show_pass_lines, show_gap_lines)
                st.plotly_chart(fig_t, use_container_width=True)

                fig_r = px.line(
                    x=times,
                    y=rate,
                    labels={"x": "Time (UTC)", "y": "Angular Rate (deg/s)"},
                    title="ADCS: Angular rate",
                )
                fig_r = add_pass_and_gap_markers(fig_r, times, pass_ids, gaps, show_pass_lines, show_gap_lines)
                st.plotly_chart(fig_r, use_container_width=True)

            with right:
                fig_cpu = px.line(
                    x=times,
                    y=cpu,
                    labels={"x": "Time (UTC)", "y": "CPU Load (%)"},
                    title="System: CPU load",
                )
                fig_cpu = add_pass_and_gap_markers(fig_cpu, times, pass_ids, gaps, show_pass_lines, show_gap_lines)
                st.plotly_chart(fig_cpu, use_container_width=True)

                fig_rssi = px.line(
                    x=times,
                    y=rssi,
                    labels={"x": "Time (UTC)", "y": "Signal Strength (dB)"},
                    title="Comm: Signal strength",
                )
                fig_rssi = add_pass_and_gap_markers(fig_rssi, times, pass_ids, gaps, show_pass_lines, show_gap_lines)
                st.plotly_chart(fig_rssi, use_container_width=True)

                fig_pass = px.line(
                    x=times,
                    y=pass_ids,
                    labels={"x": "Time (UTC)", "y": "Pass ID"},
                    title="Inferred contact passes",
                )
                fig_pass = add_pass_and_gap_markers(fig_pass, times, pass_ids, gaps, show_pass_lines, show_gap_lines)
                st.plotly_chart(fig_pass, use_container_width=True)

                fig_h = px.scatter(
                    x=times,
                    y=health_series,
                    labels={"x": "Time (UTC)", "y": "Health"},
                    title="Health timeline",
                )
                fig_h = add_pass_and_gap_markers(fig_h, times, pass_ids, gaps, show_pass_lines, show_gap_lines)
                st.plotly_chart(fig_h, use_container_width=True)

            # ----------------------------
            # Latest packet JSON
            # ----------------------------
            st.divider()
            st.subheader("Latest Packet (truncated)")
            st.json(
                {
                    "header": latest.get("header", {}),
                    "status": latest_status,
                    "measurements": latest.get("measurements", {}),
                    "meta": latest.get("meta", {}),
                },
                expanded=False,
            )

        except Exception as exc:
            st.error(f"Failed to fetch telemetry: {exc}")
            st.info("Make sure FastAPI is running and telemetry is being sent.")
            time.sleep(max(1.0, refresh_s))

    time.sleep(refresh_s)
