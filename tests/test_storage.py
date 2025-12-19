# tests/test_storage.py

from simulator.telemetry_generator import TelemetrySimulator
from storage.parquet_store import ParquetTelemetryStore


def test_parquet_append_and_load(tmp_path):
    store = ParquetTelemetryStore(tmp_path / "telemetry.parquet")
    sim = TelemetrySimulator(seed=1)

    packet = sim.generate_packet()
    store.append(packet, health="GREEN")

    df = store.load()

    assert len(df) == 1
    assert df.iloc[0]["seq"] == packet.header.seq
    assert df.iloc[0]["health"] == "GREEN"
