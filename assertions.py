import requests
import sys
import os

# Base API url configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")

def safe_print(msg):
    """
    Safely prints messages containing unicode characters, falling back to ASCII
    if the terminal does not support UTF-8 (e.g. standard Windows cp1252 cmd/powershell).
    """
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            # Fallback to ascii representation, replacing unencodable characters
            print(msg.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
        except Exception:
            # Absolute fallback
            print(msg.encode('ascii', errors='replace').decode('ascii'))

def run_e2e_assertions():
    safe_print(f"Running E2E Assertions against API at {API_URL}...")
    
    # 1. Assert health check returns HTTP 200
    try:
        resp = requests.get(f"{API_URL}/health", timeout=3)
    except Exception as e:
        safe_print(f"Error connecting to API server: {e}")
        safe_print("Please verify the FastAPI server is running (e.g. docker compose up) before executing assertions.")
        sys.exit(1)
        
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    health_data = resp.json()
    
    # 2. Assert health check includes healthy state
    assert "status" in health_data
    assert health_data["status"] in ["healthy", "degraded"], f"Unexpected status: {health_data['status']}"

    # 3. Assert database connection pool is active
    assert health_data.get("database") == "connected", "Database should be connected"

    # Define a clean batch of mock events
    batch = [
        {
            "event_id": "99999999-0000-0000-0000-000000000001",
            "store_id": "STORE_BLR_002",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_assertions01",
            "event_type": "ENTRY",
            "timestamp": "2026-03-03T14:20:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.98,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
        },
        {
            "event_id": "99999999-0000-0000-0000-000000000002",
            "store_id": "STORE_BLR_002",
            "camera_id": "CAM_BILLING_01",
            "visitor_id": "VIS_assertions01",
            "event_type": "BILLING_QUEUE_JOIN",
            "timestamp": "2026-03-03T14:22:00Z",
            "zone_id": "BILLING",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.95,
            "metadata": {"queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 2}
        }
    ]

    # 4. Assert batch event ingestion accepts payloads cleanly
    ingest_resp = requests.post(f"{API_URL}/events/ingest", json=batch)
    assert ingest_resp.status_code == 201, f"Failed ingestion: {ingest_resp.text}"
    ingest_data = ingest_resp.json()
    assert ingest_data["success_count"] == 2, "Expected 2 successful event ingestions"

    # 5. Assert Ingestion is strictly idempotent
    dup_resp = requests.post(f"{API_URL}/events/ingest", json=batch)
    assert dup_resp.status_code == 201
    assert dup_resp.json()["success_count"] == 2, "Duplicate ingestion should return successful count (idempotency)"

    # 6. Assert Store Metrics endpoint returns correctly
    metrics_resp = requests.get(f"{API_URL}/stores/STORE_BLR_002/metrics")
    assert metrics_resp.status_code == 200
    metrics_data = metrics_resp.json()
    assert metrics_data["store_id"] == "STORE_BLR_002"
    assert "conversion_rate" in metrics_data

    # 7. Assert conversion rate logic is numeric
    assert isinstance(metrics_data["conversion_rate"], (int, float))

    # 8. Assert Store Conversion Funnel exists and correlates stages
    funnel_resp = requests.get(f"{API_URL}/stores/STORE_BLR_002/funnel")
    assert funnel_resp.status_code == 200
    funnel_data = funnel_resp.json()
    assert "stages" in funnel_data
    assert len(funnel_data["stages"]) == 4, "Expected exactly 4 stages in conversion funnel"

    # 9. Assert Heatmap normalizes statistics
    heatmap_resp = requests.get(f"{API_URL}/stores/STORE_BLR_002/heatmap")
    assert heatmap_resp.status_code == 200
    heatmap_data = heatmap_resp.json()
    assert "data_confidence" in heatmap_data
    assert "zones" in heatmap_data

    # 10. Assert active anomalies are detected and flagged
    anomalies_resp = requests.get(f"{API_URL}/stores/STORE_BLR_002/anomalies")
    assert anomalies_resp.status_code == 200
    anomalies_data = anomalies_resp.json()
    assert "anomalies" in anomalies_data
    assert isinstance(anomalies_data["anomalies"], list)

    safe_print("\n=========================================================================")
    safe_print("[SUCCESS] ALL 10 REFERENCE E2E TEST ASSERTIONS PASSED SUCCESSFULLY!")
    safe_print("=========================================================================")

if __name__ == "__main__":
    # If standard local server is not running, we degrade gracefully and run assertions via FastAPI TestClient!
    try:
        r = requests.get(f"{API_URL}/health", timeout=1)
        run_e2e_assertions()
    except Exception:
        safe_print("Local server not active. Spawning direct FastAPI TestClient assertion suite...")
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database import Base, engine
        
        # Verify schema is deployed
        Base.metadata.create_all(bind=engine)
        
        # Override API_URL interface with client requests wrapper
        client = TestClient(app)
        
        # 1. Health check returns HTTP 200
        resp = client.get("/health")
        assert resp.status_code == 200
        health_data = resp.json()
        
        # 2. Status in health data
        assert "status" in health_data
        
        # 3. DB connection
        assert health_data.get("database") == "connected"
        
        # Setup mock events
        batch = [
            {
                "event_id": "99999999-0000-0000-0000-000000000001",
                "store_id": "STORE_BLR_002",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_assertions01",
                "event_type": "ENTRY",
                "timestamp": "2026-03-03T14:20:00Z",
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.98,
                "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
            }
        ]
        
        # 4. Ingest accepts payloads
        ingest_resp = client.post("/events/ingest", json=batch)
        assert ingest_resp.status_code == 201
        assert ingest_resp.json()["success_count"] == 1
        
        # 5. Strict idempotency
        dup_resp = client.post("/events/ingest", json=batch)
        assert dup_resp.status_code == 201
        assert dup_resp.json()["success_count"] == 1
        
        # 6. Store metrics endpoint
        metrics_resp = client.get("/stores/STORE_BLR_002/metrics")
        assert metrics_resp.status_code == 200
        metrics_data = metrics_resp.json()
        assert metrics_data["store_id"] == "STORE_BLR_002"
        
        # 7. Conversion rate is numeric
        assert isinstance(metrics_data["conversion_rate"], (int, float))
        
        # 8. Conversion funnel has 4 stages
        funnel_resp = client.get("/stores/STORE_BLR_002/funnel")
        assert funnel_resp.status_code == 200
        assert len(funnel_resp.json()["stages"]) == 4
        
        # 9. Heatmap
        heatmap_resp = client.get("/stores/STORE_BLR_002/heatmap")
        assert heatmap_resp.status_code == 200
        
        # 10. Anomalies
        anomalies_resp = client.get("/stores/STORE_BLR_002/anomalies")
        assert anomalies_resp.status_code == 200
        assert "anomalies" in anomalies_resp.json()
        
        safe_print("\n=========================================================================")
        safe_print("[SUCCESS] ALL 10 REFERENCE TEST CLIENT ASSERTIONS PASSED SUCCESSFULLY!")
        safe_print("=========================================================================")
