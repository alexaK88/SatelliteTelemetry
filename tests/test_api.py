# tests/test_api.py

from fastapi.testclient import TestClient

from api.main import app
from simulator.telemetry_generator import TelemetrySimulator


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_post_valid_telemetry():
    sim = TelemetrySimulator()
    packet = sim.generate_packet()

    response = client.post("/telemetry", json=packet.model_dump())

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["health"] in ("GREEN", "YELLOW", "RED")


def test_post_invalid_telemetry_rejected():
    sim = TelemetrySimulator()
    data = sim.generate_packet().model_dump()

    # Break schema
    data["measurements"]["system"]["cpu_load_pct"] = 200

    response = client.post("/telemetry", json=data)

    # Schema violation → 422
    assert response.status_code in (400, 422)


def test_latest_telemetry():
    sim = TelemetrySimulator()
    packet = sim.generate_packet()

    client.post("/telemetry", json=packet.model_dump())
    response = client.get("/telemetry/latest")

    assert response.status_code == 200
    assert response.json()["packet"]["header"]["seq"] == packet.header.seq
