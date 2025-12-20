# processing/pass_monitor.py

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional


PASS_GAP_THRESHOLD = timedelta(seconds=30)  # configurable


@dataclass(frozen=True)
class PassEvent:
    pass_id: int
    started_at: datetime
    ended_at: Optional[datetime]

class PassTracker:
    """
    Detects ground station contact passes based on telemetry arrival times.
    """

    def __init__(self, gap_threshold: timedelta = PASS_GAP_THRESHOLD):
        self.gap_threshold = gap_threshold
        self._current_pass_id = 0
        self._last_seen: Optional[datetime] = None
        self._pass_start: Optional[datetime] = None

    def update(self, packet_time: datetime) -> PassEvent:
        """
        Update tracker with a new telemetry packet timestamp.
        Returns the current pass state.
        """
        packet_time = packet_time.astimezone(timezone.utc)

        # First packet ever → start first pass
        if self._last_seen is None:
            self._current_pass_id += 1
            self._pass_start = packet_time
            self._last_seen = packet_time
            return PassEvent(
                pass_id=self._current_pass_id,
                started_at=self._pass_start,
                ended_at=None,
            )

        gap = packet_time - self._last_seen

        # New pass detected
        if gap > self.gap_threshold:
            self._current_pass_id += 1
            self._pass_start = packet_time

        self._last_seen = packet_time

        return PassEvent(
            pass_id=self._current_pass_id,
            started_at=self._pass_start,
            ended_at=None,
        )
