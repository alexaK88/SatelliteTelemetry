# scripts/replay_telemetry.py

import time
import argparse
import logging

import requests
import pandas as pd

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("telemetry-replay")


def parse_args():
    parser = argparse.ArgumentParser(description="Replay stored telemetry")
    parser.add_argument(
        "--parquet",
        default="data/telemetry.parquet",
        help="Path to telemetry parquet file",
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000/telemetry",
        help="Telemetry ingestion endpoint",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=1.0,
        help="Replay rate (packets per second)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    df = pd.read_parquet(args.parquet)
    df = df.sort_values("generated_at")

    interval = 1.0 / args.rate if args.rate > 0 else 0.0

    logger.info(f"Replaying {len(df)} telemetry packets")

    for _, row in df.iterrows():
        payload = {
            "header": {
                "mission_id": row["mission_id"],
                "spacecraft_id": row["spacecraft_id"],
                "packet_type": row["packet_type"],
                "schema_version": int(row["schema_version"]),
                "seq": int(row["seq"]),
                "generated_at": row["generated_at"].isoformat(),
            },
            "measurements": {
                "power": {
                    "battery_voltage_v": row["battery_voltage_v"],
                    "battery_current_a": row["battery_current_a"],
                },
                "thermal": {"payload_temp_c": row["payload_temp_c"]},
                "adcs": {"angular_rate_deg_s": row["angular_rate_deg_s"]},
                "comm": {"signal_strength_db": row["signal_strength_db"]},
                "system": {"cpu_load_pct": row["cpu_load_pct"]},
            },
            "meta": {
                "mode": row["mode"],
                "source": "REPLAY",
                "tags": ["replay"],
            },
        }

        r = requests.post(args.api_url, json=payload, timeout=3.0)
        r.raise_for_status()

        logger.info(f"Replayed SEQ={row['seq']}")

        if interval:
            time.sleep(interval)

    logger.info("Replay complete")


if __name__ == "__main__":
    main()
