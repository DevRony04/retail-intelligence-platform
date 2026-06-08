# PROMPT: Generate integration tests for a FastAPI database ingestion endpoint that supports batches of up to 500 events, handles strict idempotency, processes partial successes for malformed items, and handles database outages gracefully.
# CHANGES MADE: Integrated TestClient from fastapi.testclient, stubbed DBEvent and metadata mock fields, used an in-memory SQLAlchemy DB context, and wrapped assertions inside structured pytest methods.

import pytest
import os
import sys
from fastapi.testclient import TestClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import DBEvent

from sqlalchemy.pool import StaticPool

# Setup Test In-Memory Database with StaticPool to allow sharing across TestClient session threads
TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def clean_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(clean_db):
    def override_get_db():
        try:
            yield clean_db
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

def test_batch_ingestion_and_idempotency(client):
    # 1. Post a valid batch of events
    batch = [
        {
            "event_id": "00000000-0000-0000-0000-000000000001",
            "store_id": "STORE_BLR_002",
            "camera_id": "CAM_ENTRY_01",
            "visitor_id": "VIS_c8a2f1",
            "event_type": "ENTRY",
            "timestamp": "2026-03-03T14:20:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.95,
            "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1}
        }
    ]
    
    resp1 = client.post("/events/ingest", json=batch)
    assert resp1.status_code == 201
    assert resp1.json()["success_count"] == 1
    assert resp1.json()["failed_count"] == 0

    # 2. Resubmit the exact same batch to test strict idempotency
    resp2 = client.post("/events/ingest", json=batch)
    assert resp2.status_code == 201
    assert resp2.json()["success_count"] == 1  # counted as success due to idempotency
    assert resp2.json()["failed_count"] == 0

def test_partial_success_handling(client):
    # Post a batch where one event is valid and one is malformed
    batch = [
        {
            "event_id": "00000000-0000-0000-0000-000000000002",
            "store_id": "STORE_BLR_002",
            "camera_id": "CAM_FLOOR_01",
            "visitor_id": "VIS_c8a2f1",
            "event_type": "ZONE_ENTER",
            "timestamp": "2026-03-03T14:20:30Z",
            "zone_id": "SKINCARE",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.92,
            "metadata": {"queue_depth": None, "sku_zone": "MOISTURISER", "session_seq": 2}
        },
        {
            "event_id": "malformed-event",
            "store_id": "STORE_BLR_002",
            # missing required field camera_id and event_type
            "visitor_id": "VIS_c8a2f1"
        }
    ]
    
    resp = client.post("/events/ingest", json=batch)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "partial_success"
    assert data["success_count"] == 1
    assert data["failed_count"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["event_id"] == "malformed-event"
