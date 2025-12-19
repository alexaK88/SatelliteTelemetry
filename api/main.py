# api/main.py
from typing import Deque
from collections import deque
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from api.schemas import TelemetryPacket, TelemetryValidationError
from processing.validator import validate_packet, HealthStatus

RECENT_MAX = 2000
RECENT_PACKETS: Deque[TelemetryPacket] = deque(maxlen=RECENT_MAX)
RECENT_STATUSES: Deque[dict] = deque(maxlen=RECENT_MAX)

app = FastAPI(
    title="Satellite Telemetry Ingestion API",
    version="1.0.0",
    description="Ground-segment style telemetry ingestion and validation service",
)

# In-memory cache for demo / latest packet
LATEST_PACKET: TelemetryPacket | None = None
LATEST_STATUS: dict | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "telemetry-ingestion",
    }


@app.post("/telemetry")
def ingest_telemetry(packet: TelemetryPacket):
    """
    Ingest a single telemetry packet.

    - Schema validation handled by Pydantic (422)
    - Domain validation handled here (400)
    """

    global LATEST_PACKET, LATEST_STATUS

    try:
        result = validate_packet(packet)
    except TelemetryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Store latest (replace later with CSV / Parquet)
    LATEST_PACKET = packet
    LATEST_STATUS = {
        "accepted": True,
        "health": result.status,
        "messages": result.messages,
        "seq": packet.header.seq,
        "received_at": datetime.now(timezone.utc)
    }

    RECENT_PACKETS.append(packet)
    RECENT_STATUSES.append(LATEST_STATUS)


    return {
        "accepted": True,
        "health": result.status,
        "messages": result.messages,
    }


@app.get("/telemetry/latest")
def get_latest_telemetry():
    if LATEST_PACKET is None:
        raise HTTPException(status_code=404, detail="No telemetry received yet")

    return {
        "packet": LATEST_PACKET,
        "status": LATEST_STATUS,
    }


# ---------- Global error mapping ----------

@app.exception_handler(TelemetryValidationError)
def telemetry_validation_exception_handler(_, exc: TelemetryValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )

@app.get("/telemetry/recent")
def get_recent(limit: int = 300):
    if not RECENT_PACKETS:
        raise HTTPException(status_code=404, detail="No telemetry received yet")

    limit = max(1, min(limit, len(RECENT_PACKETS)))
    packets = list(RECENT_PACKETS)[-limit:]
    statuses = list(RECENT_STATUSES)[-limit:]

    # Return JSON-friendly dicts
    return {
        "packets": [p.model_dump(mode="json") for p in packets],
        "statuses": statuses,
    }
