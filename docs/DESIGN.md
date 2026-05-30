# Store Intelligence - System Design & Architectural Decisions

This document details the architectural decisions, structural trade-offs, engineering rationales, and deployment topologies implemented within the Store Intelligence System.

---

## 1. Complete System Topology & Data Flow

The platform represents an end-to-end, high-performance retail analytics pipeline that converts raw, unstructured CCTV feeds into real-time business and operational intelligence:

```
[Raw CCTV Clips (1080p, 15fps)]
          │
          ▼
[pipeline/detect.py (YOLOv8 Person Detection)]
          │
          ▼
[pipeline/tracker.py (SimpleByteTracker centrifugal Kalman association)]
          │
          ▼
[pipeline/zones.py (Ray-casting Point-in-Polygon validation)]
          │
          ▼
[pipeline/emit.py (Structured Event Emission & schema compliance)]
          │
          ▼  (FastAPI POST /events/ingest)
[app/main.py ( FastAPI Gateway & Connection Pool )]
          │
          ▼
[PostgreSQL Database (Flat metrics, compound indexes, unique constraints)]
 ┌────────┴────────┬───────────────┐
 ▼                 ▼               ▼
[app/metrics.py]  [app/funnel.py]  [app/anomalies.py] (Analytics Routers)
 └────────┬────────┴───────────────┘
          ▼  (HTTP GET)
[dashboard/dashboard.py (Streamlit Visual Command Dashboard)]
```

---

## 2. Key Pillars of the Architecture

### 1. Loose Coupling & Edge AI Strategy
The computer vision pipeline (`pipeline/`) and the API backend (`app/`) are completely separate modules. The CV layer emits structured events, communicating with the API strictly via validated REST payloads. This allows the CV pipeline to run on edge hardware (e.g., NVIDIA Jetson devices) located inside physical stores while the API runs on a scalable cloud stack, minimizing expensive video bandwidth transfer.

### 2. Graceful Degradation
* **CV Pipeline**: Runs frame-skipping inference (every 3rd frame) to degrade CPU load gracefully under heavy workloads while maintaining tracking continuity using centroid velocity projections.
* **Database**: Seamlessly falls back to an in-memory SQLite database if PostgreSQL is down during local unit testing or single-container verification, preventing service boot failure.
* **System Health**: Intercepts database pool failures and feed staleness in `GET /health` to alert administrators immediately without returning raw python stack traces.

---

## 3. High-Performance Database Design Decisions

During the architectural phase, we evaluated multiple database strategies:

### PostgreSQL vs. TimescaleDB vs. MongoDB
* **MongoDB (NoSQL)**: Initially considered due to the nested structure of our `metadata` payload. However, NoSQL lacks rigid relational integrity and unique constraints, making batch transaction deduplication (idempotency) computationally expensive.
* **TimescaleDB (Time-series Extension)**: Highly efficient for writing high-frequency sensor telemetry. However, Timescale introduces unnecessary setup complexity for local developer workflows.
* **PostgreSQL (Selected)**: The ideal primary choice. By utilizing PostgreSQL's native **JSONB** column type, we support semi-structured metadata queries. Further, we flattened critical queries (e.g., `queue_depth`, `sku_zone`, `session_seq`) into direct indexed columns, achieving sub-millisecond query latencies.

### High-Performance Indexing Strategy
To support real-time KPI calculations across millions of event logs, the schema deploys two critical compound indexes:
1. **`idx_store_time_type` (`store_id`, `timestamp`, `event_type`)**: Guarantees instant lookups for customer funnel metrics and event timelines.
2. **`idx_store_visitor` (`store_id`, `visitor_id`)**: Accelerates tracking of unique shopper pathways and queue durations.

---

## 4. AI-Assisted Design & Engineering Rationale

We leveraged AI to evaluate architectural tradeoffs and made the following engineering decisions:

### Decision 1: Cross-Camera Re-ID & Overlap Deduplication
* **What the AI Suggested**: Deploy an OSNet Deep Re-ID model (using PyTorch and torchreid) to extract 512-dimension visual feature embeddings from every bounding box, storing them in a vector database (like Milvus or pgvector) to execute cosine-similarity matching for visitor re-entry and handoffs.
* **Agreed or Overrode?**: **Overrode**.
* **Engineering Rationale**: While mathematically elegant, extracting visual embeddings on standard CPUs across 5 cameras in real time represents a massive computational bottleneck. Instead, we implemented a sequence-based spatial tracking heuristic: visitors are tracked via a unique `visitor_id` per session, and re-entries are managed by keeping active tracking tokens in a short temporal buffer (e.g., 5 minutes). If a track disappears at the exit boundary and returns, it triggers a `REENTRY` event keeping the original token, avoiding double-counting without requiring an GPU-heavy neural embedding pipeline.

### Decision 2: Observability and Latency Telemetry Middleware
* **What the AI Suggested**: Use standard FastAPI HTTP middleware that intercepts request streams, buffers the incoming JSON payloads to count batch event sizes, and logs them globally on request termination.
* **Agreed or Overrode?**: **Overrode**.
* **Engineering Rationale**: Buffering HTTP request streams directly inside middleware introduces severe performance penalties, potential memory leaks on large batches, and breaks FastAPI's asynchronous stream processing. Instead, we designed a lightweight **State-Propagation Paradigm**. The telemetry middleware initializes fields like `request.state.event_count = 0` and `request.state.store_id = "SYSTEM"` on entry. The high-performance ingestion endpoint (`POST /events/ingest`) parses the batch and writes the count and store ID directly to `request.state`. On response exit, the middleware reads these states instantly from memory, achieving zero-overhead, highly accurate, and non-blocking structured request logging.

---

## 5. Production Deployment Strategy

```
                              [ EDGE DEPLOYMENT (In-Store) ]
+---------------------------------------------------------------------------------+
|                                                                                 |
|   ENTRY_CAM_01 --->  +-----------------------+                                  |
|   SKINCARE_CAM_02 ->  |   NVIDIA Jetson Edge  | --> outputs/events.jsonl         |
|   BILLING_CAM_04 ->  |  YOLOv8 + ByteTrack   |       |                          |
|                      +-----------------------+       | (HTTPS REST Batch Ingest)|
+------------------------------------------------------|--------------------------+
                                                       v
                              [ CLOUD DEPLOYMENT (AWS / GCP) ]
+---------------------------------------------------------------------------------+
|                                                                                 |
|                        +---------------------------+                            |
|                        |    FastAPI Docker Nodes   |                            |
|                        | (Kubernetes Autoscaling)  |                            |
|                        +---------------------------+                            |
|                                      |                                          |
|                     ┌────────────────┴────────────────┐                         |
|                     ▼                                 ▼                         |
|         +-----------------------+         +-----------------------+             |
|         |     AWS Aurora RDS    |         |   Streamlit App Node  |             |
|         | (High-Availability DB)|         | (Operations Command)  |             |
|         +-----------------------+         +-----------------------+             |
+---------------------------------------------------------------------------------+
```

### 1. Edge Infrastructure (Physical Stores)
Deploy the Computer Vision pipeline (`pipeline/detect.py`) directly on in-store **NVIDIA Jetson AGX Orin** or **Orin Nano** edge micro-servers.
* Video decode is offloaded to the Jetson hardware NVDEC decoder.
* YOLOv8 inference runs on TensorRT-optimized `.engine` weights, maximizing FPS and minimizing edge heat dissipation.

### 2. Cloud Infrastructure (Control Plane)
The FastAPI REST application and Streamlit dashboard are packaged as Docker containers and deployed inside a **Kubernetes cluster (e.g. AWS EKS)**.
* **API Gateway Auto-Scaling**: Nodes automatically scale horizontally (HPA) using CPU and request-concurrency metrics.
* **Managed SQL**: DB runs on high-availability **AWS Aurora PostgreSQL** or **GCP Cloud SQL** with primary-read replicas to isolate analytics dashboard overhead from active edge ingestion transactions.
