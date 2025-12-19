# 🛰️ Architecture in a Real Mission Context

This project implements the **ground-segment telemetry processing and monitoring layer** of a spacecraft mission.
It is intentionally scoped to the part of the system where **software engineering is most critical and reusable**.

The architecture mirrors how telemetry flows in real satellite operations, while replacing flight hardware and RF links with a simulator for development and demonstration purposes.

---

## Position in the Mission Architecture

A typical satellite mission consists of the following high-level layers:

```
Satellite (On-board Computer)
        ↓
Space Link (RF)
        ↓
Ground Station
        ↓
Ground Segment Software
        ↓
Mission Control / Operators
```

This project covers the **Ground Segment Software** layer.

It does **not** attempt to emulate:

* RF communications
* antenna tracking
* modulation/demodulation
* flight software running on the spacecraft

Those elements are handled by specialized hardware and low-level systems in real missions.

---

## Telemetry Flow in a Real Mission

### 1️⃣ On-board Telemetry Generation (Flight Segment)

On-board the spacecraft:

* Subsystems (power, thermal, ADCS, payload, etc.) generate telemetry
* Telemetry is packaged by the on-board computer
* Data is typically encoded as:

  * CCSDS packets, or
  * mission-specific binary formats

This data is transmitted over an RF downlink during ground station passes.

---

### 2️⃣ Ground Station Reception & Decoding

At the ground station:

* RF signals are received and demodulated
* Telemetry frames are decoded
* Binary telemetry packets are extracted

This stage is handled by:

* ground station hardware
* SDR systems
* vendor-provided ground station software

The output of this stage is **decoded telemetry data**, not raw RF signals.

---

### 3️⃣ Interface to the Ground Segment Software (This Project)

Once telemetry is decoded, it is forwarded to ground software for processing.

In a real mission, this typically happens via one of the following interfaces:

```
Decoded telemetry
    → HTTP / REST API
    → Message queue (Kafka, RabbitMQ, ZeroMQ)
    → File-based handoff (per pass)
```

In this project:

* The **telemetry simulator** represents the decoded output of the ground station
* The **downlink script** simulates continuous telemetry delivery
* The **FastAPI ingestion service** represents the ground-segment entry point

This makes the architecture realistic while remaining fully self-contained.

---

## Ground Segment Software Architecture (This System)

```
Telemetry Source (Simulator / Decoder)
            ↓
     Ingestion API (FastAPI)
            ↓
 Schema Validation (Pydantic)
            ↓
 Domain Validation & Health Evaluation
            ↓
 Telemetry Buffer / Storage
            ↓
 Monitoring Dashboard (Mission Control View)
```

Each component has a single, well-defined responsibility, which mirrors real ground-segment design principles.

---

## Component Mapping: Project → Real Mission

| Project Component       | Real Mission Equivalent               |
| ----------------------- | ------------------------------------- |
| Telemetry Simulator     | Decoded telemetry from ground station |
| Downlink script         | Telemetry forwarding service          |
| FastAPI `/telemetry`    | Ground segment ingestion endpoint     |
| Schema validation       | Telemetry contract enforcement        |
| Health evaluation       | Mission control health logic          |
| Recent buffer / storage | Telemetry archive / database          |
| Dashboard               | Mission control monitoring console    |

---

## What Changes When Connecting to a Real Satellite

Only the **telemetry source and transport layer** change.

### Replaced components:

* Telemetry simulator → real telemetry decoder
* HTTP sender script → ground station forwarding mechanism

### Unchanged components:

* telemetry schema
* validation logic
* health classification
* storage and replay
* monitoring dashboard

This separation allows the ground software to be:

* developed independently
* tested with simulated data
* reused across missions

---

## Design Rationale

This project intentionally focuses on:

* deterministic processing
* strict validation
* health-driven logic
* observability and monitoring

These characteristics are critical for spacecraft operations, where:

* telemetry cannot be blindly trusted
* failures must be detected early
* operators need clear situational awareness

---

## Extensibility for Real Missions

The system is designed to be extended with minimal changes to core logic:

* **Binary telemetry decoder** (e.g., CCSDS)
* **Message-queue ingestion** for scalability
* **Pass-based ingestion** with bursty telemetry
* **Persistent storage and replay**
* **Multi-spacecraft support**

Because responsibilities are cleanly separated, these extensions can be added without refactoring existing components.

---

## Summary

This project implements a realistic and reusable **ground-segment telemetry processing architecture**.

While telemetry is simulated, the system design, data flow, validation strategy, and monitoring approach closely reflect how real satellite missions operate, making it suitable as a foundation for real-world ground software systems.
