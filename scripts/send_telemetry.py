# scripts/send_telemetry.py

import time
import logging
import argparse
from typing import Optional

import requests

from simulator.telemetry_generator import TelemetrySimulator


LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("telemetry-uplink")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Simulate spacecraft telemetry downlink to ground API"
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
        help="Packets per second",
    )
    parser.add_argument(
        "--fault",
        choices=["LOW_BATTERY", "OVERHEAT", "HIGH_SPIN", "CPU_OVERLOAD"],
        default=None,
        help="Inject a persistent fault",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=0,
        help="Number of packets to send (0 = infinite)",
    )
    return parser.parse_args()


def send_packet(api_url: str, payload: dict) -> bool:
    try:
        response = requests.post(api_url, json=payload, timeout=3.0)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.error(f"Failed to send telemetry: {exc}")
        return False


def main():
    args = parse_args()

    simulator = TelemetrySimulator()

    interval = 1.0 / args.rate if args.rate > 0 else 1.0
    sent = 0

    logger.info("Starting telemetry downlink simulation")
    logger.info(f"Target API: {args.api_url}")
    logger.info(f"Rate: {args.rate} pkt/s")
    if args.fault:
        logger.warning(f"Fault injection enabled: {args.fault}")

    try:
        while True:
            packet = simulator.generate_packet(fault=args.fault)
            payload = packet.model_dump(mode="json")

            ok = send_packet(args.api_url, payload)

            if ok:
                logger.info(
                    f"SEQ={packet.header.seq} | "
                    f"MODE={packet.meta.mode} | "
                    f"sent OK"
                )

            sent += 1
            if args.count and sent >= args.count:
                logger.info("Packet count reached, stopping.")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        logger.info("Downlink simulation stopped by operator")


if __name__ == "__main__":
    main()
