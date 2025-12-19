# api/schemas.py
# Pydantic models for telemetry packet schema (v1)
# Works with Pydantic v2.x (FastAPI current default). If you're on v1, tell me and I'll adapt.

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


# ---------- Errors (useful for consistent API responses) ----------

class TelemetryValidationError(ValueError):
    """Raised when telemetry packet violates validation rules."""


# ---------- Header ----------

PacketType = Literal["HK"]

class TelemetryHeader(BaseModel):
    # routing + traceability
    model_config = ConfigDict(extra="forbid")

    # identity
    mission_id: str = Field(..., min_length=1, max_length=32, examples=["DEMO-01"])
    spacecraft_id: str = Field(..., min_length=1, max_length=32, examples=["SC-001"])
    packet_type: PacketType = Field(default="HK") # locked to v1
    schema_version: int = Field(default=1, ge=1, le=1)  # lock to v1 for now

    # sequence counter to detect drops/out-of-order
    seq: int = Field(..., ge=0, le=2**31 - 1, description="Monotonic packet sequence counter")

    # utc timestamp
    generated_at: datetime = Field(..., description="Packet generation time in UTC (ISO-8601, 'Z' recommended)")


# ---------- Measurements (subsystems) ----------

class PowerMeasurements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    battery_voltage_v: float = Field(..., ge=22.0, le=30.0)
    battery_current_a: float = Field(..., ge=-5.0, le=5.0)  # negative = charging


class ThermalMeasurements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload_temp_c: float = Field(..., ge=-40.0, le=85.0)


class ADCSMeasurements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    angular_rate_deg_s: float = Field(..., ge=0.0, le=5.0)


class CommMeasurements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_strength_db: float = Field(..., ge=-120.0, le=-20.0)


class SystemMeasurements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cpu_load_pct: float = Field(..., ge=0.0, le=100.0)


class Measurements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    power: PowerMeasurements
    thermal: ThermalMeasurements
    adcs: ADCSMeasurements
    comm: CommMeasurements
    system: SystemMeasurements


# ---------- Meta ----------

Mode = Literal["NOMINAL", "SAFE", "DEGRADED", "TEST"]
Source = Literal["SIM", "FLIGHT", "REPLAY"]


class Meta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Mode = Field(default="NOMINAL")
    source: Source = Field(default="SIM")
    tags: list[str] = Field(default_factory=list, max_length=16)


# ---------- Full Packet ----------

class TelemetryPacket(BaseModel):
    """
    Canonical packet structure for ingestion/processing.
    """
    model_config = ConfigDict(extra="forbid")

    header: TelemetryHeader
    measurements: Measurements
    meta: Optional[Meta] = None

    @model_validator(mode="after")
    def timestamp_sanity(self) -> "TelemetryPacket":
        # Allow stale timestamps during REPLAY (ground reprocessing)
        if self.meta is not None and self.meta.source == "REPLAY":
            return self

        now = datetime.now(timezone.utc)
        delta = abs(now - self.header.generated_at)

        if delta > timedelta(minutes=5):
            raise TelemetryValidationError(
                f"header.generated_at outside allowed window (±5 min). "
                f"Delta was {delta}."
            )
        return self

