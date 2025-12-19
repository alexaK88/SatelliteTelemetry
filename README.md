# SatelliteTelemetry
A modular satellite telemetry ingestion, processing, and monitoring system inspired by real spacecraft ground-segment architectures.

### System Architecture
Telemetry Simulator
        ↓
Ingestion API (FastAPI)
        ↓
Validation & Processing
        ↓
Storage (CSV / Parquet)
        ↓
Monitoring & Visualization


### Telemetry Data
| Subsystem | Parameter       | Unit  |
| --------- | --------------- | ----- |
| Power     | Battery voltage | V     |
| Power     | Battery current | A     |
| Thermal   | Payload temp    | °C    |
| ADCS      | Angular rate    | deg/s |
| Comm      | Signal strength | dB    |
| System    | CPU load        | %     |

Idea: each parameter has expected ranges and physical meaning.

### Module Breakdown
#### 1. Telemetry Simulator
Simulates spacecraft telemetry packets.
Responsibilities:
- Generate time-stamped telemetry
- Add noise
- Inject faults

Interface: `generate_packet() -> dict`

#### 2. Ingestion API (FastAPI)
Space software never trusts input blindly, it must be validated.
Endpoints:
POST /telemetry
GET  /health
GET  /telemetry/latest

Responsibilities:
- Receive telemetry
- Validate schema
- Reject invalid packets

#### 3. Processing & Validation Layer
Checks:
- Missing fields
- Unit consistency
- Range validation
- Timestamp sanity

#### 4. Storage Layer
For now:
- CSV 
- Append-only
- Deterministic order
Later:
- Time-based partitioning
- Replay capability

#### 5. Monitoring & Visualization
Dashboards:
- Battery voltage vs time
- Temperature vs time
- System health status
Status:
- Nominal
- Warning
- Critical

### Current implementation
Mini ground-segment telemetry pipeline:
1. A telemetry producer (simulated spacecraft)
2. An ingestion service (ground endpoint)
3. A validation + health evaluation layer (ground logic)
4. An ops-style downlink script (tooling to puch telemetry continuously)
5. A test suite (verification)

##### 1) Telemetry data model (schemas)
Defined a formal telemetry packet schema using Pydantic models (Pydantic v2 style). 
This is a canonical definition of "what a valid telemetry packet looks like" in the system.

The packet contains:
- Header (routing + traceability)
- Measurements (nested by subsystem)
- Meta (ops context)

Rules enforced at schema level:
- `extra="forbid"` everywhere (reject unknown fields -- important in critical software)
- numeric bounds (CPU 0 - 100, voltage 22 - 30, etc.)
- timestamp samity check: `generated_at` must be within +- 5 minutes of server time

##### 2) Processing & Validation layer (domain logic)
Separated "schema validity" from "mission/domain heath".

Ground-segment design pattern:
- Schema validation: Is this packet structurally correct?
- Domain validation & health: Is the spacecraft healthy?

Implelemented in `processing/validator.py`

Output:
A `ValidationResult` that contains:
- `status`: `GREEN / YELLOW / RED`
- `messages`: human-readable reasons (warnings or critical)

Example logic:
- voltage approaching limit -> YELLOW
- voltage critically low -> RED
- payload temperature high -> YELLOW; critical -> RED
- CPU load high -> YELLOW; overload -> RED
- angular rate high -> YELLOW

##### 3) Ingestion API (FastAPI ground endpoint)
A FastAPI service that behaves like a ground station ingestion node.

Endpoints:
`GET /health`
- confirms the service is alive
`POST /telemetry`
- accepts a telemetry packet (validated by schema)
- runs domain validation
- updates “latest packet” cache
`GET /telemetry/latest`
- returns the last accepted packet + status

Error semantics:
- Schema errors: handled automatically by FastAPI/Pydantic → typically `422 Unprocessable Entity`
- Domain validation errors (your `TelemetryValidationError`) → mapped to `400 Bad Request`

Internal state:
- `LATEST_PACKET` and `LATEST_STATUS` kept in memory

##### 4) Telemetry Simulator (spacecraft)
Python simulator that generates telemetry packets.

Implemented file: `simulator/telemetry_generator.py`

Key features:
- generates realistic housekeeping (HK) telemetry packets.
- physically plausible values with noise.
- deterministic sequence counter (`seq`)
- reproducible randomness via `seed`
- realistic nominal distributions (Gaussian noise around plausible values)
- configurable fault injection modes:
    - `LOW_BATTERY`
    - `OVERHEAT`
    - `HIGH_SPIN`
    - `CPU_OVERLOAD`
Faults intentionally shift values so they trigger the validator health logic, but still generally remain schema-valid (unless you intentionally push extremes later).

##### 5) Simulator -> API Integration (ops downlink tool)
A command-line operational tool that simulates a telemetry downlink stream by continuously sending telemetry to API.

Implemented file: `scripts/send_telemetry.py`

Capabilities:
- configurable API endpoint (`--api-url`)
- configurable rate (`--rate`, packets per second)
- configurable fault injection (`--fault`)
- optional finite send count (`--count`)
- logging designed like an ops tool
- network error handling (timeouts / connection failure logged)

##### Summary
A complete MVP ground telemetry system:
- data contract (schema)
- realistic producer (simulator)
- ingestion service (FastAPI)
- domain validation (health states)
- operational downlink tool (CLI sender)
- test suite


### How to Run
All commands should be run from the project root directory.

Terminal 1: Start the Ground Ingestion API
```commandline
uvicorn api.main:app --reload
```
Expected:
- API running at http://127.0.0.1:8000
- `/health` endpoint available

Terminal 2: Start Telemetry Downlink Simulation
```commandline
python -m scripts.send_telemetry --rate 1
```
Nominal telemetry stream (1 packet/sec)

You should logs like:
```ini
2025-12-19 19:40:49,384 | INFO | SEQ=1 | MODE=NOMINAL | sent OK
2025-12-19 19:40:50,398 | INFO | SEQ=2 | MODE=NOMINAL | sent OK
2025-12-19 19:40:51,412 | INFO | SEQ=3 | MODE=NOMINAL | sent OK
2025-12-19 19:40:52,416 | INFO | SEQ=4 | MODE=NOMINAL | sent OK
2025-12-19 19:40:53,424 | INFO | SEQ=5 | MODE=NOMINAL | sent OK
2025-12-19 19:40:54,435 | INFO | SEQ=6 | MODE=NOMINAL | sent OK
```

Terminal 3: Start the Monitoring Dashboard
```commandline
streamlit run monitoring/dashboard.py
```
Expected:
- Browser opens with live telemetry dashboard
- KPIs and plots update in real time


### Next MileStones
The system is designed to be easily extended.
- Dashboard Enhancements:
    - Subsystem-specific threshold overlays
    - Packet rate and drop detection (seq gap monitoring)
    - Improved health timeline visualization
    - Operator-style alarm indicators
- Persistent Storage:
    - Append-only CSV or Parquet storage
    - Time-partitioned telemetry files
    - Schema-consistent archival
    - Enables long-duration runs and offline analysis
- Telemetry Replay Mode:
    - Replay stored telemetry at configurable speeds
    - Feed historical data back into the ingestion API
    - Ideal for:
        - debugging
        - demos
        - regression testing
        - fault investigation
- Dockerized Deployment
- Multiple spacecraft support
- Anomaly detection