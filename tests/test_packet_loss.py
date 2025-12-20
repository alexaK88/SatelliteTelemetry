from processing.packet_monitor import SequenceTracker, GapSeverity


def test_no_gap():
    tracker = SequenceTracker()
    assert tracker.update(1) is None
    assert tracker.update(2) is None


def test_gap_detected_warning():
    tracker = SequenceTracker()
    tracker.update(1)
    gap = tracker.update(4)

    assert gap is not None
    assert gap.gap_size == 2
    assert gap.severity == GapSeverity.WARNING


def test_gap_detected_critical():
    tracker = SequenceTracker()
    tracker.update(10)
    gap = tracker.update(20)

    assert gap is not None
    assert gap.gap_size == 9
    assert gap.severity == GapSeverity.CRITICAL
