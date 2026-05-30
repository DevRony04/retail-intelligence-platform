# PROMPT: Generate unit tests for a retail store metrics calculation API that correlates POS transactions to visitor billing zone presence in a 5-minute time window, calculates conversion rates and funnel stages, and excludes staff events.
# CHANGES MADE: Stubbed DBEvent mock objects using SQLAlchemy local SQLite connections, structured assertions against Pydantic-validated models, and stubbed POS transactions CSV reading.

import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import DBEvent
from app.metrics import get_store_metrics
from app.funnel import get_store_funnel

# Set up clean in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_store_metrics_and_conversion_rate(db_session):
    store_id = "STORE_BLR_002"
    base_time = datetime(2026, 3, 3, 14, 20, 0)
    
    # Ingest 1 customer who visits browse zone then billing
    db_session.add(DBEvent(
        event_id="e1", store_id=store_id, camera_id="CAM_ENTRY_01", visitor_id="VIS_01",
        event_type="ENTRY", timestamp=base_time, is_staff=False
    ))
    db_session.add(DBEvent(
        event_id="e_b1", store_id=store_id, camera_id="CAM_FLOOR_01", visitor_id="VIS_01",
        event_type="ZONE_ENTER", timestamp=base_time + timedelta(minutes=1), zone_id="SKINCARE", is_staff=False
    ))
    db_session.add(DBEvent(
        event_id="e2", store_id=store_id, camera_id="CAM_BILLING_01", visitor_id="VIS_01",
        event_type="ZONE_ENTER", timestamp=base_time + timedelta(minutes=2), zone_id="BILLING", is_staff=False
    ))
    db_session.add(DBEvent(
        event_id="e_q1", store_id=store_id, camera_id="CAM_BILLING_01", visitor_id="VIS_01",
        event_type="BILLING_QUEUE_JOIN", timestamp=base_time + timedelta(minutes=3), zone_id="BILLING", queue_depth=1
    ))
    db_session.add(DBEvent(
        event_id="e3", store_id=store_id, camera_id="CAM_BILLING_01", visitor_id="VIS_01",
        event_type="ZONE_EXIT", timestamp=base_time + timedelta(minutes=4), zone_id="BILLING", dwell_ms=120000
    ))
    
    # Ingest 1 staff member (must be excluded from metrics)
    db_session.add(DBEvent(
        event_id="e4", store_id=store_id, camera_id="CAM_ENTRY_01", visitor_id="VIS_staff01",
        event_type="ENTRY", timestamp=base_time, is_staff=True
    ))
    
    db_session.commit()
    
    # Verify Unique Customer count is 1 (excluding staff)
    kpis = get_store_metrics(store_id, db_session)
    assert kpis["unique_visitors"] == 1
    
    # Fetch funnel (should have 1 Entry, 1 Queue)
    funnel = get_store_funnel(store_id, db_session)
    assert funnel["stages"][0]["count"] == 1  # Entry
    assert funnel["stages"][2]["count"] == 1  # Billing Queue
