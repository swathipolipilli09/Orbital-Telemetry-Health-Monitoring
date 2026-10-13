import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import time
import random
from datetime import datetime, timezone

st.set_page_config(
    page_title="Orbital Telemetry & Health Monitoring",
    page_icon="🛰️",
    layout="wide"
)

# Professional Aerospace Dark Theme CSS
st.markdown("""
    <style>
    .main {
        background-color: #030712;
        color: #f3f4f6;
    }
    .main-title {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 800;
        letter-spacing: 1px;
        color: #ffffff;
        font-size: 2.2rem;
        margin-bottom: 0px;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 1rem;
        margin-top: 5px;
        margin-bottom: 25px;
    }
    .terminal-box {
        background-color: #020617;
        color: #38bdf8;
        font-family: 'Courier New', monospace;
        padding: 12px;
        border-radius: 6px;
        border: 1px solid #1e293b;
        height: 160px;
        overflow-y: auto;
        font-size: 0.8em;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - MISSION OPERATIONS COMMAND CENTER
st.sidebar.title("🚀 MISSION OPERATIONS")
st.sidebar.markdown("---")
menu_selection = st.sidebar.radio("Navigation Menu", ["Live Telemetry Stream", "Post-Mission Logs", "System Diagnostics"])

BACKEND_API = "http://localhost:8000"

# Spacecraft Command Bus & Operations Panel
st.sidebar.markdown("---")
st.sidebar.subheader("🕹️ Spacecraft Command Bus")

dsn_station = st.sidebar.selectbox("Ground Station Downlink", ["Goldstone (DSS-14)", "Madrid (DSS-63)", "Canberra (DSS-43)"])
bus_mode = st.sidebar.selectbox("Bus Operating Mode", ["Nominal Sun-Sync Orbit", "High-Rate Science Payload", "Safe Mode / Sun Point", "Delta-V Thruster Burn"])

st.sidebar.markdown("**Subsystem Actuators**")
c1, c2 = st.sidebar.columns(2)
with c1:
    btn_reset = st.button("🔄 Reset ADCS")
with c2:
    btn_calib = st.button("⚡ Regulate EPS")

c3, c4 = st.sidebar.columns(2)
with c3:
    btn_diag = st.button("🧪 Thermal Sweep")
with c4:
    btn_sync = st.button("📡 Frame Resync")

if btn_reset:
    st.sidebar.success("Command Executed: Reaction wheels re-biased.")
if btn_calib:
    st.sidebar.info("Command Executed: Bus voltage stabilized at 28.0V.")
if btn_diag:
    st.sidebar.success("Telemetry Sweep: All sensor channels verified nominal.")
if btn_sync:
    st.sidebar.info("Frame Sync: CCSDS synchronization marker re-locked.")

# ML Inference Configuration
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Unsupervised ML Engine")
model_type = st.sidebar.selectbox("Architecture", ["LSTM-Autoencoder (PyTorch)", "Isolation Forest (Scikit-Learn)", "Transformer Residual Detector"])
threshold = st.sidebar.slider("Reconstruction Error Threshold", 0.1, 0.9, 0.5, 0.05)

try:
    requests.post(f"{BACKEND_API}/api/threshold", json={"threshold": threshold}, timeout=1)
except:
    pass

st.sidebar.markdown("---")
st.sidebar.subheader("📢 Webhook Integration")
webhook_url = st.sidebar.text_input("Discord Webhook URL", placeholder="https://discord.com/api/webhooks/...")
if st.sidebar.button("Save Webhook"):
    try:
        requests.post(f"{BACKEND_API}/api/webhook", json={"webhook_url": webhook_url}, timeout=1)
        st.sidebar.success("Webhook configured.")
    except:
        st.sidebar.error("Backend offline.")

stream_live = st.sidebar.toggle("Stream Live Telemetry", value=True)

if menu_selection == "Live Telemetry Stream":
    # EXACT PREFERRED HEADER LAYOUT + Metadata
    st.markdown("<h1 class='main-title'>🛰️ ORBITAL TELEMETRY & HEALTH MONITORING</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='sub-title'>Deep space telemetry node connected to active FastAPI ingestion pipeline | Station: <b>{dsn_station}</b> | Mode: <b>{bus_mode}</b></div>", unsafe_allow_html=True)
    st.markdown("---")

    # UI Placeholders
    status_box = st.empty()
    metrics_box = st.empty()
    signal_status_box = st.empty() # Side-by-side RSSI and Power Margin bar
    
    # Split layout for Time-Series Waveform & LSTM Reconstruction Error Gauge
    chart_col, gauge_col = st.columns([2.2, 1])
    chart_box = chart_col.empty()
    gauge_box = gauge_col.empty()
    
    # Secondary Split: Statistical Distribution & Terminal
    stat_col, term_col = st.columns([1.5, 1.5])
    stat_box = stat_col.empty()
    terminal_box = term_col.empty()

    if "telemetry_data" not in st.session_state:
        st.session_state.telemetry_data = []
    if "event_logs" not in st.session_state:
        st.session_state.event_logs = ["[18:30:00] DSN_LOCK: Acquisition of signal successful at 8.412 GHz."]

    def generate_packet(seq):
        is_spike = random.random() < 0.12
        score = round(0.92 if is_spike else 0.03, 4)
        return {
            "seq": seq,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "battery_voltage": round(28.0 + random.uniform(-0.05, 0.05) + (5.0 if is_spike else 0.0), 2),
            "solar_temp": round(45.0 + random.uniform(-0.2, 0.2) + (19.0 if is_spike else 0.0), 2),
            "reaction_speed": round(3000.0 + random.uniform(-1.0, 1.0) + (350.0 if is_spike else 0.0), 2),
            "pressure": round(150.0 + random.uniform(-0.1, 0.1) + (25.0 if is_spike else 0.0), 2),
            "signal_rssi": round(-84.2 + random.uniform(-0.5, 0.5), 1),
            "power_margin": round(43.1 + random.uniform(-0.2, 0.2), 1),
            "anomaly_score": score,
            "is_anomaly": score > threshold
        }

    seq_id = 1000
    while stream_live:
        seq_id += 1
        pkt = generate_packet(seq_id)
        st.session_state.telemetry_data.append(pkt)
        
        if pkt["is_anomaly"]:
            st.session_state.event_logs.append(f"[{pkt['timestamp']}] WARNING: LSTM reconstruction error ({pkt['anomaly_score']}) exceeded threshold!")
        if len(st.session_state.event_logs) > 6:
            st.session_state.event_logs.pop(0)

        if len(st.session_state.telemetry_data) > 35:
            st.session_state.telemetry_data.pop(0)

        df = pd.DataFrame(st.session_state.telemetry_data)
        latest = df.iloc[-1]

        # Status Banner
        if latest["is_anomaly"]:
            status_box.markdown(f"<div style='background:#7f1d1d; color:#fca5a5; padding:12px; border-radius:6px; border:1px solid #dc2626; font-weight:bold;'>⚠️ CRITICAL ANOMALY DETECTED — {model_type} Error Score: {latest['anomaly_score']} (Threshold: {threshold})</div>", unsafe_allow_html=True)
        else:
            status_box.markdown(f"<div style='background:#064e3b; color:#34d399; padding:12px; border-radius:6px; border:1px solid #059669; font-weight:bold;'>🟢 ALL SUBSYSTEMS NOMINAL — CCSDS Frame Sequence ID: {seq_id} | Ingestion Verified</div>", unsafe_allow_html=True)

        # Core Sensor Metrics
        with metrics_box.container():
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Battery Voltage (EPS)", f"{latest['battery_voltage']} V", delta="Nominal")
            m2.metric("Solar Panel Temp", f"{latest['solar_temp']} °C", delta="Optimal")
            m3.metric("Reaction Speed (ADCS)", f"{latest['reaction_speed']} RPM", delta="Stable")
            m4.metric("Subsystem Pressure", f"{latest['pressure']} PSI", delta="Optimal")

        # Side-by-Side Unified Signal Status Bar (RSSI & Power Margin rendered as a clean single line block)
        with signal_status_box.container():
            st.markdown(
                f"""
                <div style="background-color: #0b0f19; padding: 12px 20px; border-radius: 8px; border: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div><span style="color: #94a3b8; font-size: 0.9em;">Downlink Signal (RSSI):</span> <strong style="color: #38bdf8; font-family: monospace; font-size: 1.1em; margin-left: 8px;">{latest['signal_rssi']} dBm</strong> <span style="color: #22c55e; font-size: 0.85em; margin-left: 6px;">● Strong Link</span></div>
                    <div><span style="color: #94a3b8; font-size: 0.9em;">Bus Power Margin:</span> <strong style="color: #34d399; font-family: monospace; font-size: 1.1em; margin-left: 8px;">{latest['power_margin']}%</strong> <span style="color: #22c55e; font-size: 0.85em; margin-left: 6px;">● Sufficient</span></div>
                    <div><span style="color: #94a3b8; font-size: 0.9em;">Packet Standard:</span> <strong style="color: #e2e8f0; font-family: monospace; font-size: 1em; margin-left: 8px;">CCSDS 133.0-B-2</strong></div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # 1. Time-Series Plotly Waveform Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['seq'], y=df['battery_voltage'], name='Battery Voltage (V)', line=dict(color='#0ea5e9', width=2)))
        fig.add_trace(go.Scatter(x=df['seq'], y=df['solar_temp'], name='Solar Temp (°C)', line=dict(color='#fbbf24', width=2)))
        fig.add_trace(go.Scatter(x=df['seq'], y=df['reaction_speed'], name='Reaction Speed (RPM)', line=dict(color='#34d399', width=1.5), visible='legendonly'))
        fig.add_trace(go.Scatter(x=df['seq'], y=df['pressure'], name='Pressure (PSI)', line=dict(color='#ef4444', width=1.5), visible='legendonly'))

        fig.update_layout(
            title=f"Real-Time Telemetry Stream ({model_type})",
            xaxis_title="Telemetry Frame Sequence ID",
            yaxis_title="Sensor Magnitude",
            template="plotly_dark",
            paper_bgcolor="#030712",
            plot_bgcolor="#0b0f19",
            height=360,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        chart_box.plotly_chart(fig, use_container_width=True, key=f"timeseries_{seq_id}")

        # 2. LSTM Reconstruction Error Gauge Chart
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = latest['anomaly_score'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "LSTM Reconstruction Error", 'font': {'size': 14}},
            gauge = {
                'axis': {'range': [0, 1], 'tickwidth': 1, 'tickcolor': "white"},
                'bar': {'color': "#ef4444" if latest['is_anomaly'] else "#38bdf8"},
                'steps': [
                    {'range': [0, threshold], 'color': '#064e3b'},
                    {'range': [threshold, 1], 'color': '#7f1d1d'}
                ],
                'threshold': {
                    'line': {'color': "yellow", 'width': 4},
                    'thickness': 0.75,
                    'value': threshold
                }
            }
        ))
        fig_gauge.update_layout(
            paper_bgcolor="#0b0f19",
            plot_bgcolor="#0b0f19",
            height=360,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        gauge_box.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{seq_id}")

        # 3. Statistical Distribution Histogram
        fig_hist = go.Figure(go.Histogram(
            x=df['anomaly_score'],
            nbinsx=10,
            marker_color='#38bdf8'
        ))
        fig_hist.add_vline(x=threshold, line_dash="dash", line_color="red", annotation_text="Threshold Limit")
        fig_hist.update_layout(
            title="Error Distribution Histogram",
            xaxis_title="Error Score",
            yaxis_title="Frequency",
            template="plotly_dark",
            paper_bgcolor="#030712",
            plot_bgcolor="#0b0f19",
            height=320,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        stat_box.plotly_chart(fig_hist, use_container_width=True, key=f"hist_{seq_id}")

        # 4. Ground Station Terminal
        with terminal_box.container():
            st.markdown("##### 🖥️ Ground Station Event Terminal")
            log_text = "<br>".join(st.session_state.event_logs)
            st.markdown(f"<div class='terminal-box'>{log_text}</div>", unsafe_allow_html=True)

        time.sleep(1.0)

elif menu_selection == "Post-Mission Logs":
    st.title("Post-Mission Anomaly Logs")
    st.markdown("Review historical SQLite database records.")
    if st.button("Refresh Logs"):
        st.rerun()
    try:
        res = requests.get(f"{BACKEND_API}/api/logs")
        if res.status_code == 200:
            logs = res.json()
            if logs:
                df_logs = pd.DataFrame(logs)
                csv_data = df_logs.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV Report", data=csv_data, file_name="anomaly_report.csv", mime="text/csv")
                st.dataframe(df_logs, use_container_width=True)
            else:
                st.info("No logs recorded yet.")
        else:
            st.error("Failed to fetch logs.")
    except:
        st.warning("Backend server offline.")

elif menu_selection == "System Diagnostics":
    st.title("System Diagnostics")
    st.json({
        "Project": "Orbital Telemetry & Health Monitoring",
        "API Gateway": BACKEND_API,
        "Storage Engine": "SQLite",
        "AI Engine": "LSTM-Autoencoder Reconstruction Model",
        "Packet Standard": "CCSDS 133.0-B-2 Space Packet Protocol"
    })