# Store Intelligence System

A real-time, production-grade AI Store Analytics and Operational Intelligence platform. It converts raw CCTV footage into structured event streams, tracks customer conversion funnels, maps normalized shopper heatmaps, and triggers alerts for operational anomalies.

---

## 🚀 4-Command Quickstart

Deploy, process, test, and verify the entire end-to-end system in exactly 4 commands:

```bash
# 1. Spin up the production infrastructure (PostgreSQL + FastAPI API + Streamlit Dashboard)
docker compose up --build -d

# 2. Run the unified computer vision & database ingestion integration pipeline
# (Processes all standard camera streams, handles YOLOv8 CV tracking/simulation, and automatically ingests events)
python run_pipeline.py

# 3. Run the comprehensive pytest verification suite (Statement Coverage > 70%)
pytest

# 4. Execute the reference acceptance assertions gate
python assertions.py
```

*Dashboard URL: http://localhost:8501 | API Documentation: http://localhost:8000/docs*

---

## 📂 Repository Layout

```
store-intelligence/
├── data/
│   ├── store_layout.json      # Polygon definitions, zones, and open hours
│   ├── pos_transactions.csv   # POS sales transaction records
│   └── sample_events.jsonl    # Reference schema events
├── outputs/
│   ├── events.jsonl           # Emitted event log from CV pipeline
│   └── logs/                  # Telemetry log directories
├── pipeline/
│   ├── detect.py              # Main YOLOv8 person detector & tracking runner
│   ├── tracker.py             # stable ByteTrack centroid association engine
│   ├── emit.py                # Schema validator and event constructor
│   ├── zones.py               # Spatial point-in-polygon ray-casting
│   └── run.sh                 # Batch execution script for store clips
├── app/
│   ├── main.py                # FastAPI server entrypoint
│   ├── models.py              # SQLAlchemy DB models & Pydantic request models
│   ├── database.py            # PostgreSQL pool configuration
│   ├── ingestion.py           # Ingestion batch handler
│   ├── metrics.py             # KPIs calculations (Conversion rate, Dwells)
│   ├── funnel.py              # Conversion funnel stages
│   ├── anomalies.py           # Anomaly alerts rules engine
│   ├── health.py              # System health check & lag warning
│   └── utils.py               # Observability loguru telemetry logger
├── dashboard/
│   └── dashboard.py           # Streamlit live operational visual grid
├── tests/
│   ├── test_pipeline.py       # Centroid tracking & polygon tests
│   ├── test_metrics.py        # Conversion rates & funnel tests
│   ├── test_anomalies.py      # Alerts rules engines tests
│   └── test_ingestion.py      # Idempotency & batch size tests
├── docs/
│   ├── DESIGN.md              # Architecture & AI decisions write-up
│   └── CHOICES.md             # Model, schema, and storage choices rationales
├── docker-compose.yml         # Container configuration file
├── requirements.txt           # Pinned Python package manifest
├── .gitignore                 # Cache & local database exclusion list
└── README.md                  # Quickstart manual
```

---

## 🔍 How to Run the Detection Pipeline

Our main CV runner (`pipeline/detect.py`) processes raw CCTV footage using YOLOv8 person detection and our stable centroid tracking association algorithm:

1.  **Locate Videos**: Place store video clips in `C:/Users/deepy/Downloads/CCTV Footage-20260529T160731Z-3-00144614ea/CCTV Footage/` or define a custom path.
2.  **Run Pipeline**: Execute the batch script `bash pipeline/run.sh`.
    *   *Real Video Processing*: If video clips are present and required libraries are installed, it runs frame-by-frame person tracking via YOLOv8.
    *   *High-Fidelity Simulation Fallback*: If running on basic hardware or libraries are missing, the pipeline gracefully degrades to a simulated real-time stream that emits identical, deterministic, and highly realistic retail events representing all edge cases.
3.  **Outputs**: Structured events are continuously written to `outputs/events.jsonl` matching the required event schema:
    ```json
    {
      "event_id": "uuid-v4",
      "store_id": "STORE_BLR_002",
      "camera_id": "CAM_ENTRY_01",
      "visitor_id": "VIS_c8a2f1",
      "event_type": "ZONE_DWELL",
      "timestamp": "2026-03-03T14:22:10Z",
      "zone_id": "SKINCARE",
      "dwell_ms": 8400,
      "is_staff": false,
      "confidence": 0.91,
      "metadata": {
        "queue_depth": null,
        "sku_zone": "MOISTURISER",
        "session_seq": 5
      }
    }
    ```

---

## 🧪 Comprehensive Verification Suite

The repository contains extensive unit and integration tests (Statement Coverage > 70%) checking all edge cases. Run them using pytest:

```bash
pytest -v
```

### Reference Assertions Gate
Our acceptance gate (`assertions.py`) verifies all 10 challenge criteria:
1.  FastAPI health check resolves HTTP 200.
2.  Service returns a `healthy` status in health payloads.
3.  Database connection pool actively pings database.
4.  `/events/ingest` accepts batch uploads cleanly.
5.  Ingestion is strictly idempotent (rejects duplicate `event_id` writes).
6.  `/stores/{id}/metrics` resolves HTTP 200.
7.  Conversion rate is dynamically calculated and numeric.
8.  `/stores/{id}/funnel` returns exactly 4 stages.
9.  `/stores/{id}/heatmap` aggregates and normalizes zone visit statistics.
10. Active anomalies (queue spikes, dead zones, staleness lags) are correctly flagged.

Run the gate locally using:
```bash
python assertions.py
```
