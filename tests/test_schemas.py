# tests/test_schemas.py

from datetime import datetime, timezone, timedelta
import pytest

from api.schemas import TelemetryPacket, TelemetryValidationError
from simulator.telemetry_generator import TelemetrySimulator


def test_valid_packet_passes_schema():
    sim = TelemetrySimulator()
    packet = sim.generate_packet()
    # Should not raise
    TelemetryPacket.model_validate(packet.model_dump())


def test_timestamp_too_old_rejected():
    sim = TelemetrySimulator()
    packet = sim.generate_packet()

    data = packet.model_dump()
    data["header"]["generated_at"] = (
        datetime.now(timezone.utc) - timedelta(minutes=10)
    ).isoformat()

    with pytest.raises(TelemetryValidationError):
        TelemetryPacket.model_validate(data)


def test_missing_field_rejected():
    sim = TelemetrySimulator()
    data = sim.generate_packet().model_dump()

    del data["measurements"]["power"]["battery_voltage_v"]

    with pytest.raises(Exception):
        TelemetryPacket.model_validate(data)
