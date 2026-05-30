# Store Intelligence System Architecture Guide

This document describes the high-level system architecture, component relationships, data flow patterns, and production deployment considerations of the Store Intelligence System.

---

## 🏛️ System Component Topology

The system is designed with a highly modular, loose-coupling strategy that separates the data plane (edge AI ingestion pipeline) from the control plane (FastAPI REST backend and Streamlit Observability Dashboard).

```mermaid
graph TD
    %% Video Input Section
    subgraph Video Inputs (CCTV Nodes)
        V1[ENTRY_CAM_01]
        V2[SKINCARE_CAM_02]
        V3[COSMETICS_CAM_03]
        V4[BILLING_CAM_04]
        V5[EXIT_CAM_05]
    end

    %% Edge AI Pipeline Section
    subgraph Edge Processing (pipeline/)
        DET[pipeline/detect.py YOLOv8 + Centroids]
        EMI[pipeline/emit.py Schema Validator]
    end

    %% API Backend Section
    subgraph Analytics Core (app/)
        API[app/main.py FastAPI Gateway]
        DB[app/database.py Connection Manager]
        MET[app/metrics.py Analytics Engine]
        ANO[app/anomalies.py Rule Engine]
    end

    %% Storage Section
    subgraph Storage Layer
        PSQL[(PostgreSQL Pool)]
        LITE[(SQLite Offline Fallback)]
    end

    %% Front End Section
    subgraph Operations Control (dashboard/)
        DSH[dashboard/dashboard.py Streamlit App]
    end

    %% Flows
    V1 --> DET
    V2 --> DET
    V3 --> DET
    V4 --> DET
    V5 --> DET
    
    DET --> EMI
    EMI -->|outputs/events.jsonl| API
    EMI -->|Direct SQLAlchemy Fallback| PSQL
    
    API --> DB
    DB --> PSQL
    DB -.-> LITE
    
    MET --> API
    ANO --> API
    
    API -->|HTTP REST Endpoints| DSH
    LITE -.->|Direct Query| DSH
```

---

## 🛰️ Component Responsibilities

### 1. Edge Processing Ingestion Pipeline (`pipeline/`)
* **`detect.py`**: Invokes the YOLOv8 object detector to track humans and ByteTrack-style centroid tracking to maintain shopper identity across zones. Translates spatial zone coordinate crossings into structured chronological streams.
* **`emit.py`**: Asserts event schema validation on emitted JSON payloads and appends them asynchronously to a localized telemetry file (`outputs/events.jsonl`).

### 2. Analytics Backend APIs (`app/`)
* **`main.py`**: Hosts the ASGI FastAPI application router, CORS middleware, global exception handler, and observability logging hooks.
* **`database.py`**: Establishes production connection pools (`QueuePool`) for high-concurrency PostgreSQL backends, with a zero-setup SQLite fallback for local developer workstations.
* **`metrics.py`**: Aggregates complex raw behavioral records to compute high-level executive KPIs (e.g. conversion, basket values, dwell-to-purchase correlation, queue waits) on demand.
* **`anomalies.py`**: Background rule engine checking real-time store stats for alerts (e.g., dead zones, long billing lines, queue abandonment, stale cameras).

### 3. Unified Operations Command Center (`dashboard/`)
* **`dashboard.py`**: Futuristic Streamlit application providing live 2D footfall heatmaps, active YOLO detection overlays, operational SOC-style event feeds, and executive business KPIs.

---

## 📊 End-to-End Shopper Data Lifecycle Flow

1. **Detection & Centroid Tracking**: The shopper walks into range of `ENTRY_CAM_01`. Centroid coordinates are computed, a visitor token is assigned (e.g. `VIS_c8a2`), and a timezone-aware `ENTRY` event is emitted.
2. **Behavioral Logging**: The shopper browses product shelves under `SKINCARE_CAM_02`. Chronological `ZONE_ENTER`, `SHELF_INTERACTION`, `ZONE_DWELL`, and `ZONE_EXIT` events are appended.
3. **Queue Processing**: The shopper enters checkout under `BILLING_CAM_04`. `QUEUE_JOIN` and `QUEUE_EXIT` events register queue density fluctuations.
4. **Journey Closure**: The shopper purchases items and exits under `EXIT_CAM_05`, firing a `PURCHASE_COMPLETED` and `EXIT` log.
5. **Batch Ingestion**: The integration pipeline bundles these events and issues a `POST /events/ingest` batch request (idempotent, deduplicated via `event_id`).
6. **Command Dashboard**: The operations control panel fetches the compiled metrics, rendering the glowing 2D contour heatmap and updating live business intelligence indices.
