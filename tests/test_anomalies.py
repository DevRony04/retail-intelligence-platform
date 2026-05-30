# PROMPT: Generate unit tests for a retail store anomalies alert engine that evaluates queue depth spikes, dead zone browsing halts, stale camera feed lags, conversion rate drops, and queue abandonment spikes.
# CHANGES MADE: Stubbed DBEvent and metadata mock fields, used an in-memory SQLAlchemy DB context, and wrapped assertions inside structured pytest methods.

import pytest
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import DBEvent
from app.anomalies import get_store_anomalies

# In-memory DB setup
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

def test_operational_anomalies_rules(db_session):
    store_id = "STORE_BLR_002"
    base_time = datetime(2026, 3, 3, 14, 20, 0)
    
    # 1. Test Queue Spike Anomaly
    # Insert a billing queue join event with queue_depth > 3
    db_session.add(DBEvent(
        event_id="e1", store_id=store_id, camera_id="CAM_BILLING_01", visitor_id="VIS_01",
        event_type="BILLING_QUEUE_JOIN", timestamp=base_time, zone_id="BILLING", queue_depth=5, is_staff=False
    ))
    db_session.commit()
    
    alerts = get_store_anomalies(store_id, db_session)
    alert_types = [a["anomaly_type"] for a in alerts["anomalies"]]
    assert "BILLING_QUEUE_SPIKE" in alert_types

    # 2. Test Stale Feed Anomaly
    # Simulated live time is 2026-03-03T14:40:00Z.
    # If last event timestamp in DB is 2026-03-03T14:20:00Z, lag is 20 minutes (> 10m threshold)
    # The anomaly engine evaluates lag compared to the simulated live time
    assert "STALE_FEED" in alert_types
