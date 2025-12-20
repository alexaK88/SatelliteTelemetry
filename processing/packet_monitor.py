# processing/packet_monitor.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime, timezone


class GapSeverity(str, Enum):
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class PacketGap:
    from_seq: int
    to_seq: int
    gap_size: int
    detected_at: datetime
    severity: GapSeverity


class SequenceTracker:
    """
    Tracks telemetry sequence numbers and detects packet loss.
    """

    def __init__(self):
        self._last_seq: Optional[int] = None

    def update(self, seq: int) -> Optional[PacketGap]:
        """
        Update tracker with new seq.
        Returns PacketGap if a gap is detected.
        """
        now = datetime.now(timezone.utc)

        if self._last_seq is None:
            self._last_seq = seq
            return None

        expected = self._last_seq + 1

        if seq == expected:
            self._last_seq = seq
            return None

        if seq <= self._last_seq:
            # Out-of-order or duplicate packet (ignore for now)
            return None

        gap_size = seq - expected

        severity = (
            GapSeverity.WARNING if gap_size <= 5 else GapSeverity.CRITICAL
        )

        gap = PacketGap(
            from_seq=expected,
            to_seq=seq - 1,
            gap_size=gap_size,
            detected_at=now,
            severity=severity,
        )

        self._last_seq = seq
        return gap
