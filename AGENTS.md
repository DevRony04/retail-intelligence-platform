# 🤖 AGENTS.md - AI Developer Agent Handbook

Welcome, Agent. This document outlines the system architecture, business constraints, technology stack, and repository rules of engagement for the **Retail Intelligence Platform**. You must review this document in its entirety before making any contributions, suggestions, or analysis of this codebase.

---

## 📋 Project Overview & Business Purpose

The **Retail Intelligence Platform** is a real-time, production-grade AI-powered Store Analytics and Operational Intelligence platform. 
* **Core Value Proposition:** Converts raw CCTV footage from retail store camera grids into structured, real-time behavioral event streams. 
* **Business Insights:** Computes checkout funnel conversions, tracks queue lengths, analyzes zone dwell-times (heatmaps), and triggers automated alerts when operational bottlenecks or hardware anomalies occur.
* **Goal:** Enable retail managers and executives to optimize store layout, improve staff scheduling, audit promotional displays, and reduce customer checkout abandonment in real time.

---

## 🛠️ Technology Stack

The platform is built on a highly performant, modular Python-based ecosystem:

* **Computer Vision Pipeline (`pipeline/`):**
  * **YOLOv8 (`yolov8n.pt`):** Headless deep-learning object detector optimized for CPU execution.
  * **ByteTrack Centroid Association (`pipeline/tracker.py`):** Kalman-filter-inspired centroid tracking logic keeping track IDs stable across frames and handling shopper occlusions.
  * **Ray-Casting Polygon solver (`pipeline/zones.py`):** Mathematical Point-in-Polygon spatial solver mapping centroids to store layouts.
* **Control Plane / Backend APIs (`app/`):**
  * **FastAPI:** Asynchronous REST API serving high-throughput event ingestion and serving metrics queries.
  * **SQLAlchemy ORM:** Declarative data-access layer with customized pool controls.
  * **Loguru:** Structured JSON-ready stdout logging middleware.
* **Executive Dashboard (`dashboard/`):**
  * **Streamlit:** Interactive front-end visual interface polling REST APIs and rendering live dashboards.
  * **Matplotlib & Pandas:** Data frame manipulation and visual contour maps.
* **Storage Layers:**
  * **Neon Serverless PostgreSQL:** Production relational store using compound indexes and JSONB metadata.
  * **SQLite:** Local developer fallback automatically provisioned if no production credentials are provided.
* **Orchestration & Infrastructure:**
  * **Docker / Docker Compose:** Fully containerized services with isolated networking.
  * **Render / Streamlit Cloud:** Active production deployment host.

---

## 🏛️ System Architecture Overview

The system utilizes a decoupled, edge-to-cloud architecture designed to minimize expensive video transmission overhead.

```mermaid
graph TD
    subgraph Edge Layer (Physical Retail Store)
        C1[CCTV Cam 1] -->|Raw Frames| CV[YOLOv8 & Centroid Tracker]
        C2[CCTV Cam 2] -->|Raw Frames| CV
        CV -->|Spatial Coordinates| ZM[Ray-Casting Zone Manager]
        ZM -->|Serialized Event JSONL| EMI[Event Ingestion Pipeline]
    end

    subgraph Cloud Control Plane (API & Database)
        EMI -->|POST /events/ingest batch| API[FastAPI Gateway]
        API -->|JSONB & Flattened Write| DB[(Neon PostgreSQL)]
        DB -.->|SQLite Fallback| API
    end

    subgraph Visualization & Alerting
        API -->|REST GET APIs| ST[Streamlit Dashboard]
        API -->|GET /anomalies| AL[Operational Alerts]
    end
```

### Decoupled Data vs. Control Plane
* **Data Plane (Edge):** Computer vision inference runs on local edge nodes (e.g., CCTV boxes, Jetson devices). It converts heavy video streams into lightweight structured JSON events.
* **Control Plane (Cloud):** The API gateway receives batch HTTP posts, validates schemas via Pydantic, persists events to Neon, and runs SQL queries to extract metrics.

---

## 📡 Core Subsystems & Pipelines

### 1. Data Pipeline Architecture (`pipeline/`)
* **Centroid Point Anchor:** Shoppers are tracked by mapping their 2D bounding boxes to a single coordinate $cx = \frac{x_1 + x_2}{2}$ and $cy = y_2$ (the bottom-center coordinate representing their feet contacting the floor).
* **Ray Casting Engine:** The point $(cx, cy)$ is evaluated against a list of polygon vertices from `data/store_layout.json` to trigger `ZONE_ENTER` or `ZONE_EXIT` transitions.
* **Graceful Degradation:** If opencv or pytorch are not installed, the pipeline degrades to a high-fidelity deterministic simulation generator that produces schema-compliant events.

### 2. Event Ingestion Architecture (`app/ingestion.py`)
* **Endpoint:** `POST /events/ingest`
* **Idempotency Protection:** The database enforces a `UNIQUE` constraint on `event_id` (UUIDv4). If a duplicate event batch is sent (e.g., due to edge-to-cloud network retries), the engine performs an `ON CONFLICT (event_id) DO NOTHING` operation, catching exceptions and returning a success count to the edge client without duplicating statistics.

### 3. Dashboard & Metrics Architecture
* **Endpoints:**
  * `GET /stores/{store_id}/metrics` (conversion rate, footfall)
  * `GET /stores/{store_id}/funnel` (4-stage funnel: Entrance -> Browser -> Checkout -> Purchase)
  * `GET /stores/{store_id}/heatmap` (normalized dwell-times per zone)
  * `GET /stores/{store_id}/anomalies` (dead zones, queue spikes, stale CCTV logs)
* **Visuals:** Streamlit reads metrics endpoints asynchronously, rendering Matplotlib bar graphs and raw telemetry feeds.

---

## 🧪 Testing Strategy

* **Unit & Integration Tests:** Driven by `pytest`. Test files live in `tests/` and cover zones mathematics, tracking logic, metrics accumulation, and idempotency constraints.
* **E2E Acceptance Gate:** Handled by `assertions.py` in the workspace root. When run, it checks a live API endpoint, or falls back to standard FastAPI `TestClient` verification.
* **Coverage Requirements:** Must maintain statement coverage above 70%.

---

## 🛑 Production Safety Rules (CRITICAL CONSTRAINTS)

As an AI developer agent, you are strictly forbidden from modifying runtime operations. 

> [!CAUTION]
> **CRITICAL RESTRICTIONS**
> * **NO Source Code Changes:** You MUST NOT edit Python files in `app/`, `pipeline/`, or `dashboard/` directories.
> * **NO Database Modifications:** Do not edit database models in `app/models.py` or modify PostgreSQL/SQLite schemas.
> * **NO Pipeline Changes:** Do not alter YOLO detection models, tracking heuristics, or zone boundaries.
> * **NO Deployment Changes:** Do not modify `Dockerfile`, `docker-compose.yml`, or Render setup configurations.
> * **Validation Only:** Any CI actions or workflows you add must be completely non-invasive, with no auto-deploy or auto-migration side effects.

---

## 🤖 AI-Assisted Development Guidelines

1. **Information Extraction:** Always use the local file system tools to verify active directory paths, config states, and requirements before writing documentation.
2. **Path Mapping:** When linking files in documentation, always construct absolute file paths using the `file:///` URI scheme with forward slashes (e.g., `[main.py](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/app/main.py)`).
3. **No Placeholders:** All documentation and code configuration must be fully resolved. Dummy URLs, placeholders, or template comments are unacceptable.
4. **CI/CD Integration:** When designing CI/CD workflows, strictly reuse existing tools (`pytest`, `assertions.py`). Do not introduce new linters, test harnesses, or security scanners unless explicitly configured in the repository.
