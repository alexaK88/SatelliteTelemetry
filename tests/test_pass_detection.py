from datetime import datetime, timezone, timedelta
from processing.pass_monitor import PassTracker


def test_single_pass():
    tracker = PassTracker(gap_threshold=timedelta(seconds=10))
    t0 = datetime.now(timezone.utc)

    p1 = tracker.update(t0)
    p2 = tracker.update(t0 + timedelta(seconds=5))

    assert p1.pass_id == 1
    assert p2.pass_id == 1


def test_new_pass_after_gap():
    tracker = PassTracker(gap_threshold=timedelta(seconds=10))
    t0 = datetime.now(timezone.utc)

    p1 = tracker.update(t0)
    p2 = tracker.update(t0 + timedelta(seconds=20))

    assert p1.pass_id == 1
    assert p2.pass_id == 2
