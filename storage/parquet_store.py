# storage/parquet_store.py

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from api.schemas import TelemetryPacket


class ParquetTelemetryStore:
    """
    Append-only Parquet storage for telemetry packets.
    """

    def __init__(self, path: str | Path = "data/telemetry.parquet"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _flatten(packet: TelemetryPacket, health: str) -> dict:
        """
        Flatten telemetry packet into a single row.
        """
        m = packet.measurements

        return {
            # Header
            "mission_id": packet.header.mission_id,
            "spacecraft_id": packet.header.spacecraft_id,
            "packet_type": packet.header.packet_type,
            "schema_version": packet.header.schema_version,
            "seq": packet.header.seq,
            "generated_at": packet.header.generated_at,

            # Health
            "health": health,

            # Power
            "battery_voltage_v": m.power.battery_voltage_v,
            "battery_current_a": m.power.battery_current_a,

            # Thermal
            "payload_temp_c": m.thermal.payload_temp_c,

            # ADCS
            "angular_rate_deg_s": m.adcs.angular_rate_deg_s,

            # Comm
            "signal_strength_db": m.comm.signal_strength_db,

            # System
            "cpu_load_pct": m.system.cpu_load_pct,

            # Meta
            "mode": packet.meta.mode if packet.meta else None,
            "source": packet.meta.source if packet.meta else None,
        }

    def append(self, packet: TelemetryPacket, health: str) -> None:
        row = self._flatten(packet, health)
        df_new = pd.DataFrame([row])

        if self.path.exists():
            df_old = pd.read_parquet(self.path)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new

        # Ensure deterministic ordering
        df = df.sort_values("generated_at")

        df.to_parquet(self.path, index=False)

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError("No telemetry parquet file found")
        return pd.read_parquet(self.path)
