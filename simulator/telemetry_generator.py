# simulator/telemetry_generator.py

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Optional

from api.schemas import TelemetryPacket, TelemetryHeader, Measurements
from api.schemas import (
    PowerMeasurements,
    ThermalMeasurements,
    ADCSMeasurements,
    CommMeasurements,
    SystemMeasurements,
    Meta,
)


class TelemetrySimulator:
    """
    Satellite telemetry simulator (HK packets).

    Usage:
        sim = TelemetrySimulator()
        packet = sim.generate_packet()
    """

    def __init__(
        self,
        mission_id: str = "DEMO-01",
        spacecraft_id: str = "SC-001",
        seed: Optional[int] = 42,
    ):
        self.mission_id = mission_id
        self.spacecraft_id = spacecraft_id
        self.seq = 0

        if seed is not None:
            random.seed(seed)

    # ---------- Nominal generators ----------

    def _battery_voltage(self) -> float:
        return random.gauss(mu=27.5, sigma=0.3)

    def _battery_current(self) -> float:
        return random.gauss(mu=1.5, sigma=0.4)

    def _payload_temp(self) -> float:
        return random.gauss(mu=15.0, sigma=2.0)

    def _angular_rate(self) -> float:
        return abs(random.gauss(mu=0.05, sigma=0.02))

    def _signal_strength(self) -> float:
        return random.gauss(mu=-75.0, sigma=3.0)

    def _cpu_load(self) -> float:
        return random.gauss(mu=40.0, sigma=8.0)

    # simulator/telemetry_generator.py

    def generate_packet(self, fault: Optional[str] = None) -> TelemetryPacket:
        self.seq += 1

        # --- Nominal values ---
        battery_voltage = self._battery_voltage()
        battery_current = self._battery_current()
        payload_temp = self._payload_temp()
        angular_rate = self._angular_rate()
        signal_strength = self._signal_strength()
        cpu_load = self._cpu_load()

        # --- Fault injection (schema-safe) ---
        if fault == "LOW_BATTERY":
            battery_voltage = 22.4  # valid but critical

        elif fault == "OVERHEAT":
            payload_temp = 82.0  # valid but critical

        elif fault == "HIGH_SPIN":
            angular_rate = 3.2  # valid but warning/critical

        elif fault == "CPU_OVERLOAD":
            cpu_load = 98.0  # valid but critical

        packet = TelemetryPacket(
            header=TelemetryHeader(
                mission_id=self.mission_id,
                spacecraft_id=self.spacecraft_id,
                packet_type="HK",
                schema_version=1,
                seq=self.seq,
                generated_at=datetime.now(timezone.utc),
            ),
            measurements=Measurements(
                power=PowerMeasurements(
                    battery_voltage_v=round(battery_voltage, 2),
                    battery_current_a=round(battery_current, 2),
                ),
                thermal=ThermalMeasurements(
                    payload_temp_c=round(payload_temp, 2),
                ),
                adcs=ADCSMeasurements(
                    angular_rate_deg_s=round(angular_rate, 4),
                ),
                comm=CommMeasurements(
                    signal_strength_db=round(signal_strength, 2),
                ),
                system=SystemMeasurements(
                    cpu_load_pct=round(cpu_load, 1),
                ),
            ),
            meta=Meta(
                mode="NOMINAL" if fault is None else "DEGRADED",
                source="SIM",
                tags=["hk", "simulated"],
            ),
        )

        return packet
