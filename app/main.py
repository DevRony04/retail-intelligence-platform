import time
import uuid
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from app.database import engine, Base
from app.utils import setup_logging
from app.ingestion import router as ingest_router
from app.metrics import router as metrics_router
from app.funnel import router as funnel_router
from app.heatmap import router as heatmap_router
from app.anomalies import router as anomalies_router
from app.health import router as health_router

# ==========================================
# 1. ORM TABLE INITIALIZATION & LOGS SETUP
# ==========================================
setup_logging()

# Auto-generate PostgreSQL/SQLite schemas on app startup
try:
    Base.metadata.create_all(bind=engine)
    logger.bind(
        trace_id="STARTUP", store_id="SYSTEM", endpoint="DB_INIT",
        latency_ms=0, event_count=0, status_code=200
    ).info("SQL Database tables verified/created successfully.")
except Exception as e:
    logger.bind(
        trace_id="STARTUP", store_id="SYSTEM", endpoint="DB_INIT",
        latency_ms=0, event_count=0, status_code=500
    ).error(f"Fatal Database migration error during startup: {e}")

# ==========================================
# 2. FASTAPI APPLICATION SETUP
# ==========================================
app = FastAPI(
    title="Apex Retail - Store Intelligence Analytics API",
    description="Real-time CCTV-derived Store behavioral analytics, funnel metrics, and anomaly alerts.",
    version="1.0.0"
)

# Enable CORS for Streamlit and dashboard integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(ingest_router)
app.include_router(metrics_router)
app.include_router(funnel_router)
app.include_router(heatmap_router)
app.include_router(anomalies_router)
app.include_router(health_router)

# ==========================================
# 3. GLOBAL EXCEPTION ERROR HANDLING
# ==========================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions, logs them with traceable telemetry,
    and returns a clean, structured JSON 500 response (preventing stack trace leakages).
    """
    trace_id = getattr(request.state, "trace_id", uuid.uuid4().hex[:12])
    logger.bind(
        trace_id=trace_id,
        store_id="SYSTEM",
        endpoint=request.url.path,
        latency_ms=0,
        event_count=0,
        status_code=500
    ).error(f"Internal Server Error on request {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "error",
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please contact system administrators.",
            "trace_id": trace_id
        }
    )

# ==========================================
# 4. TELEMETRY & OBSERVABILITY MIDDLEWARE
# ==========================================
@app.middleware("http")
async def observability_telemetry_middleware(request: Request, call_next):
    """
    Standard HTTP logging middleware measuring route latencies, tracking trace IDs,
    and outputting structured logs with exact transaction sizes (batch event count).
    """
    start_time = time.perf_counter()
    trace_id = uuid.uuid4().hex[:12]
    
    # Initialize state fields
    request.state.trace_id = trace_id
    request.state.store_id = "SYSTEM"
    request.state.event_count = 0

    response: Response = await call_next(request)
    
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    # Capture state injected from endpoints
    store_id = getattr(request.state, "store_id", "SYSTEM")
    event_count = getattr(request.state, "event_count", 0)

    # Log route metrics
    logger.bind(
        trace_id=trace_id,
        store_id=store_id,
        endpoint=request.url.path,
        latency_ms=latency_ms,
        event_count=event_count,
        status_code=response.status_code
    ).info(f"Handled HTTP request {request.method} {request.url.path}")

    # Add trace ID directly to headers for tracking
    response.headers["X-Trace-ID"] = trace_id
    return response
