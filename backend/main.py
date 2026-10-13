import asyncio
import json
import sqlite3
import pandas as pd
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import os

app = FastAPI()

DB_PATH = "../data/anomalies.db"
os.makedirs("../data", exist_ok=True)

# Optional: Set your Discord or Telegram Webhook URL here for real alerts
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # e.g., your Discord channel webhook URL

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomaly_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            battery_voltage REAL,
            solar_panel_temp REAL,
            reaction_speed REAL,
            pressure REAL,
            anomaly_score REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

current_threshold = 0.5

class ThresholdModel(BaseModel):
    threshold: float

class WebhookModel(BaseModel):
    webhook_url: str

@app.post("/api/threshold")
async def update_threshold(data: ThresholdModel):
    global current_threshold
    current_threshold = data.threshold
    return {"status": "success", "new_threshold": current_threshold}

@app.post("/api/webhook")
async def update_webhook(data: WebhookModel):
    global WEBHOOK_URL
    WEBHOOK_URL = data.webhook_url
    return {"status": "success", "webhook_configured": bool(WEBHOOK_URL)}

@app.get("/api/logs")
async def get_anomaly_logs():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM anomaly_logs ORDER BY id DESC", conn)
    conn.close()
    return df.to_dict(orient="records")

def send_webhook_alert(packet):
    if not WEBHOOK_URL:
        return
    payload = {
        "content": f"🚨 **SATELLITE ANOMALY ALERT!**\n"
                   f"• **Time:** {packet['timestamp']}\n"
                   f"• **Battery Voltage:** {packet['battery_voltage']}V\n"
                   f"• **Solar Temp:** {packet['solar_panel_temp']}°C\n"
                   f"• **Anomaly Score:** `{packet['anomaly_score']}`"
    }
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=2)
    except Exception as e:
        print(f"Failed to send webhook: {e}")

@app.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket):
    await websocket.accept()
    idx = 0
    try:
        while True:
            is_spike = (idx % 12 == 0)
            score = round(0.91 if is_spike else 0.04, 4)
            anomaly_triggered = score > current_threshold

            telemetry_packet = {
                "timestamp": pd.Timestamp.now().isoformat(),
                "battery_voltage": round(28.0 + (5.0 if anomaly_triggered else 0.1) * (idx % 2), 2),
                "solar_panel_temp": round(45.0 + (20.0 if anomaly_triggered else 0.3), 2),
                "reaction_speed": round(3000.0 + (400.0 if anomaly_triggered else 5.0), 2),
                "subsystem_pressure": round(150.0 + (30.0 if anomaly_triggered else 0.8), 2),
                "anomaly_score": score,
                "is_anomaly": anomaly_triggered
            }

            if anomaly_triggered:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO anomaly_logs (timestamp, battery_voltage, solar_panel_temp, reaction_speed, pressure, anomaly_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    telemetry_packet["timestamp"],
                    telemetry_packet["battery_voltage"],
                    telemetry_packet["solar_panel_temp"],
                    telemetry_packet["reaction_speed"],
                    telemetry_packet["subsystem_pressure"],
                    telemetry_packet["anomaly_score"]
                ))
                conn.commit()
                conn.close()
                
                # Trigger Webhook notification
                send_webhook_alert(telemetry_packet)

            await websocket.send_text(json.dumps(telemetry_packet))
            idx += 1
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        print("Client disconnected.")