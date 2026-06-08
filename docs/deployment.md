# 🚢 Deployment and Operations Guide

This document describes the deployment workflows, environment configuration guidelines, cloud topologies, rollback strategies, and monitoring requirements for the **Retail Intelligence Platform**.

---

## 1. Local Containerized Orchestration (Docker & Compose)

The platform is containerized using a multi-stage Dockerfile and orchestrated via Docker Compose, ensuring identical execution contexts across local, staging, and production environments.

### Dockerfile Design
The project uses a single [`Dockerfile`](file:///c:/Deepyaman%20Mondal/retail-intelligence-platform/Dockerfile) configured for multi-stage builds to optimize image size and build speeds.
* **Stage 1 (Builder):** Installs compiler tools and builds heavy Python wheel dependencies.
* **Stage 2 (Runtime):** Utilizes a minimal `python:3.10-slim` base image, copying pre-compiled dependencies and source files. It exposes ports `8000` (FastAPI) and `8501` (Streamlit).

### Orchestrating Services (`docker-compose.yml`)
The local docker setup configures three services running inside a shared network overlay:
1. **`db`:** Spin up PostgreSQL 15 alpine container on port `5432` with a health check.
2. **`api`:** Runs the FastAPI backend server after the database is healthy.
3. **`dashboard`:** Boots the Streamlit UI dashboard on port `8501`.

```bash
# Build and start services in background
docker compose up --build -d

# Verify container health status
docker compose ps

# Inspect API execution logs
docker compose logs -f api
```

---

## 2. Environment Configuration Matrix

The application behavior adapts based on the `APP_ENV` variable. Ensure the appropriate keys are injected at runtime:

| Variable | Development / Local | Staging | Production |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `development` | `staging` | `production` |
| `DATABASE_URL` | `sqlite:///./store_intelligence.db` | Staging PostgreSQL connection URI | Production Neon PostgreSQL URI |
| `API_URL` | `http://localhost:8000` | Staging API endpoint | `https://retail-intelligence-platform.onrender.com` |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `WARNING` |
| `DB_POOL_SIZE` | Default (SQLite) | `10` | `20` |
| `DB_MAX_OVERFLOW`| Default (SQLite) | `5` | `10` |

---

## 3. Production Cloud Deployment Topology

The active production environment is deployed using a highly scalable, serverless-first topology:

```
[ Streamlit Community Cloud ]
             │
             ▼ (REST JSON queries)
   [ Render Web Service ] ──────> Runs multi-stage Dockerfile (API Node)
             │
             ▼ (ACID Connection Pool)
   [ Serverless Neon PostgreSQL ] ──> Placed in Singapore region for APAC latency reduction
```

### 1. Database Provisioning (Neon.tech)
* Instantiated in Neon PostgreSQL.
* Set compute resources to auto-suspend after 15 minutes of zero traffic to minimize serverless costs during store closed hours.
* Ensure the target tables are auto-migrated on FastAPI startup via the ORM metadata hooks:
  ```python
  Base.metadata.create_all(bind=engine)
  ```

### 2. API Node Deployment (Render)
* Configured as a **Web Service** linked to the GitHub repository.
* **Runtime:** Set to `Docker`. Render automatically builds and hosts the image defined in the repository `Dockerfile`.
* **Instance Type:** Starter (CPU-bound, as CV inference is handled at the edge).
* **Variables:** Inject `DATABASE_URL`, `APP_ENV=production`, `API_HOST=0.0.0.0`, and `API_PORT=8000`.

### 3. Executive Dashboard (Streamlit Cloud)
* Configured as a Streamlit application linked to the repository path `dashboard/dashboard.py`.
* In advanced project parameters, specify:
  ```ini
  API_URL=https://retail-intelligence-platform.onrender.com
  ```

---

## 4. Rollback Strategy

If a production update introduces regressions (e.g. database locks, slow API latency, dashboard rendering issues):

### Step 1: Redeploy Last Stable Image
* **Render:** Navigate to the Web Service Dashboard, locate the "Events" tab, select the previous successful release, and click **Rollback to this deploy**.
* **Streamlit Cloud:** Streamlit automatically matches the target git branch. Reverting the git commit on the `main` branch immediately updates the running front-end.

### Step 2: Database Migration Reversion
* Since database tables are auto-generated on startup, schema additions are non-destructive. 
* Avoid deleting columns in production updates. If a column structure must be modified, deprecate it in one release before removing it in a later release.

---

## 5. Monitoring & Operational Health Checklists

### Health Check Endpoint
* **Path:** `GET /health`
* **Response Payload:** Returns database state (`connected` / `disconnected`) and the time elapsed since the last event ingestion per store.
* **Alerting Threshold:** If the last ingestion event timestamp exceeds 10 minutes, the status degrades to `degraded`, triggering pager alerts for operations teams to check edge CCTV connectivity.

### Logs Audit
* Ensure files under `outputs/logs/api.log` are rotated daily and compressed.
* Check logs for database connection timeouts or `500` status codes. Use the trace ID header (`X-Trace-ID`) to correlate requests across routers and middlewares.
