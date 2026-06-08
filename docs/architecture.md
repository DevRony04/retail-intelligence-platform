# 🏗️ System Architecture Manual

This document provides a comprehensive technical breakdown of the system architecture, component topologies, storage engines, and observability layers of the **Retail Intelligence Platform**.

---

## 1. System Component Topology

The system is designed with a decoupled architecture that separates the edge-based data plane from the cloud-based control plane. This ensures maximum efficiency, lower latency, and zero bandwidth waste from streaming raw video.

```mermaid
graph TD
    %% CCTV Inputs
    subgraph Video Capture (Edge)
        C1[ENTRY_CAM_01]
        C2[APPAREL_CAM_02]
        C3[COSMETICS_CAM_03]
        C4[BILLING_CAM_04]
        C5[EXIT_CAM_05]
    end

    %% Edge CV Processing
    subgraph Edge CV Engine (pipeline/)
        DET[detect.py YOLOv8 + Tracker]
        EMI[emit.py Schema Serializer]
    end

    %% Cloud REST API
    subgraph Backend API Core (app/)
        MAIN[main.py FastAPI Gateway]
        DB[database.py Session Manager]
        MET[metrics.py Analytics Engine]
        ANO[anomalies.py Rules Engine]
    end

    %% Storage
    subgraph Storage Layer
        PSQL[(Neon Serverless PostgreSQL)]
        LITE[(SQLite Offline Fallback)]
    end

    %% Dashboard
    subgraph Frontend Control
        DSH[dashboard.py Streamlit App]
    end

    %% Streams
    C1 & C2 & C3 & C4 & C5 -->|Raw Frames| DET
    DET --> EMI
    EMI -->|POST /events/ingest batch| MAIN
    MAIN --> DB
    DB --> PSQL
    DB -.->|In-Memory Fallback| LITE
    MET & ANO --> MAIN
    MAIN -->|REST Queries| DSH
```

---

## 2. Component Responsibilities

### Edge Processing Module (`pipeline/`)
* **[`detect.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/pipeline/detect.py):** Main computer vision driver. Reads video streams, executes person detection via YOLOv8, and feeds centroids to the tracking engine.
* **[`tracker.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/pipeline/tracker.py):** Implements `SimpleByteTracker`, associating centroids between consecutive frames to preserve unique visitor identities.
* **[`zones.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/pipeline/zones.py):** Maps spatial coordinate centroids to polygon coordinates defined in `data/store_layout.json` to trigger zone entry, exit, and dwell timers.
* **[`emit.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/pipeline/emit.py):** Serializes validated shopper event schemas to `outputs/events.jsonl` and batch-posts them to the backend API.

### FastAPI REST Backend (`app/`)
* **[`main.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/main.py):** Mounts routers, initializes database connections, registers middlewares, and handles uncaught exceptions.
* **[`ingestion.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/ingestion.py):** High-throughput ingest gateway that filters duplicates and saves telemetry batches to the database.
* **[`metrics.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/metrics.py):** Computes total store footfall, average shopper dwell times, and conversion ratios.
* **[`funnel.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/funnel.py):** Compiles the 4-stage funnel (Entrance -> Browser -> Checkout -> Purchase).
* **[`anomalies.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/anomalies.py):** Background evaluation engine scanning for long checkout queues, inactive zones, or frozen edge video feeds.
* **[`health.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/health.py):** Pings core database pools and tracks camera delays to determine system status.

---

## 3. Storage Layer Architecture & Connection Tuning

The data access layer ([`database.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/database.py)) is optimized for handling concurrent ingestion and real-time analytical queries:

### Neon Serverless PostgreSQL (Production)
* **Connection Pooling:** Employs SQLAlchemy `QueuePool` with parameters optimized for cloud deployment:
  * `DB_POOL_SIZE = 20` (maximum persistent connection instances)
  * `DB_MAX_OVERFLOW = 10` (allowable temporary connections above pool size)
  * `DB_POOL_RECYCLE = 1800` (recycles connections older than 30 minutes to prevent database-side timeouts)
* **Compound Indexing Strategy:**
  * `idx_store_time_type` (`store_id`, `timestamp`, `event_type`): Speeds up funnel calculation and time-series rollups.
  * `idx_store_visitor` (`store_id`, `visitor_id`): Speeds up visitor pathway tracking.
* **Metadata Flattening:** While the Pydantic schema utilizes a generic `metadata` JSON field, the ORM mapping flattens metadata fields (`queue_depth`, `sku_zone`, `session_seq`) into individual columns. This allows PostgreSQL to index them directly, optimizing query speed.

### SQLite Graceful Fallback (Local Development & Testing)
* If `DATABASE_URL` is empty, missing, or configured as a file path, the system automatically instantiates a local SQLite database (`store_intelligence.db`).
* Enables developers and CI runners to test backend APIs instantly without running a PostgreSQL instance.

---

## 4. Observability & Telemetry middleware

The platform features a structured observability system built into the request-response cycle:

* **Injected Trace IDs:** The HTTP middleware ([`main.py`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/main.py#L130-L164)) injects a unique 12-character string (`X-Trace-ID`) into each request context and response header.
* **State Propagation:** To log request metadata without reading request payloads multiple times, endpoints update `request.state` fields (e.g., `request.state.event_count` or `request.state.store_id`). The middleware retrieves these values on execution end.
* **Log Rotation:** Loguru writes structured logs to `stdout` and appends them to rotated, compressed audit logs at `outputs/logs/api.log`.
* **Global Error Isolation:** The exception handler catches uncaught errors, logs them with trace-IDs, and returns safe JSON responses to prevent leaking internal database schemas.

---

## 5. Deployment Model

```
                              [ Physical Retail Store ]
+---------------------------------------------------------------------------------+
|                                                                                 |
|   CCTV Feeds (15fps) --->  +-----------------------+                            |
|                            | NVIDIA Edge Micro-box | --> Local Event JSONL      |
|                            |  YOLOv8 + Centroids   |       |                    |
|                            +-----------------------+       |                    |
|                                                            |                    |
+------------------------------------------------------------|--------------------+
                                                             | (HTTPS POST)
                                                             v
                             [ Cloud Control Plane ]
+---------------------------------------------------------------------------------+
|                                                                                 |
|   +--------------------------+                 +----------------------------+   |
|   |   FastAPI Docker Nodes   | <-------------> |     Neon Serverless SQL    |   |
|   |  (Render Web Service)    |                 |  (ACID Transactions Pool)  |   |
|   +--------------------------+                 +----------------------------+   |
|                 ^                                                               |
|                 | (REST API Calls)                                              |
|                 v                                                               |
|   +--------------------------+                                                  |
|   |    Streamlit Dashboard   |                                                  |
|   | (Streamlit Cloud Host)   |                                                  |
|   +--------------------------+                                                  |
|                                                                                 |
+---------------------------------------------------------------------------------+
```
