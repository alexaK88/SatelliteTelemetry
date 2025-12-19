# processing/validator.py

from dataclasses import dataclass
from enum import Enum

from api.schemas import TelemetryPacket, TelemetryValidationError


class HealthStatus(str, Enum):
    NOMINAL = "GREEN"
    WARNING = "YELLOW"
    CRITICAL = "RED"


@dataclass(frozen=True)
class ValidationResult:
    status: HealthStatus
    messages: list[str]


def validate_packet(packet: TelemetryPacket) -> ValidationResult:
    """
    Domain-level validation beyond schema checks.
    This mirrors real ground software:
    - schema ensures correctness
    - validator determines health
    """

    warnings: list[str] = []
    critical: list[str] = []

    m = packet.measurements

    # --- Power ---
    if m.power.battery_voltage_v < 23.0:
        warnings.append("Battery voltage approaching lower limit")

    if m.power.battery_voltage_v < 22.5:
        critical.append("Battery voltage critically low")

    # --- Thermal ---
    if m.thermal.payload_temp_c > 70.0:
        warnings.append("Payload temperature high")

    if m.thermal.payload_temp_c > 80.0:
        critical.append("Payload temperature critical")

    # --- ADCS ---
    if m.adcs.angular_rate_deg_s > 2.0:
        warnings.append("High angular rate detected")

    # --- System ---
    if m.system.cpu_load_pct > 85.0:
        warnings.append("High CPU load")

    if m.system.cpu_load_pct > 95.0:
        critical.append("CPU overload")

    # --- Decide status ---
    if critical:
        return ValidationResult(
            status=HealthStatus.CRITICAL,
            messages=critical,
        )

    if warnings:
        return ValidationResult(
            status=HealthStatus.WARNING,
            messages=warnings,
        )

    return ValidationResult(
        status=HealthStatus.NOMINAL,
        messages=["All parameters within nominal ranges"],
    )
