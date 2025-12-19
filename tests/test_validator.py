# tests/test_validator.py

from simulator.telemetry_generator import TelemetrySimulator
from processing.validator import validate_packet, HealthStatus


def test_nominal_packet_is_green():
    sim = TelemetrySimulator(seed=1)
    packet = sim.generate_packet()

    result = validate_packet(packet)

    assert result.status == HealthStatus.NOMINAL


def test_low_battery_is_red():
    sim = TelemetrySimulator(seed=1)
    packet = sim.generate_packet(fault="LOW_BATTERY")

    result = validate_packet(packet)

    assert result.status == HealthStatus.CRITICAL
    assert any("Battery voltage" in msg for msg in result.messages)


def test_overheat_is_red():
    sim = TelemetrySimulator(seed=1)
    packet = sim.generate_packet(fault="OVERHEAT")

    result = validate_packet(packet)

    assert result.status == HealthStatus.CRITICAL
