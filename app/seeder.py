import uuid
import sys
import os
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine, Base
from app.models import DBEvent

# Ensure environment is loaded
load_dotenv()

def generate_retail_events(store_id="STORE_BLR_002"):
    """
    Generates a realistic, highly synchronized chronological dataset of store events
    for 22 unique visitor journeys (20 customers + 2 staff).
    The events perfectly sequence along Entry -> Browse -> Queue -> Purchase/Abandon -> Exit
    and correlate with transactions in data/pos_transactions.csv.
    """
    events = []
    base_time = datetime(2026, 3, 3, 14, 0, 0)
    
    # 1. Staff Members (Excluded from KPIs)
    # Staff 1
    events.append({
        "event_id": "00000000-0001-0000-0000-000000000001", "store_id": store_id, "camera_id": "ENTRY_CAM_01",
        "visitor_id": "VIS_staff01", "event_type": "ENTRY", "timestamp": base_time - timedelta(minutes=15),
        "zone_id": "ENTRY", "is_staff": True, "confidence": 0.99, "dwell_ms": 0,
        "queue_depth": None, "sku_zone": None, "session_seq": 1
    })
    events.append({
        "event_id": "00000000-0001-0000-0000-000000000002", "store_id": store_id, "camera_id": "SKINCARE_CAM_02",
        "visitor_id": "VIS_staff01", "event_type": "ZONE_ENTER", "timestamp": base_time - timedelta(minutes=14),
        "zone_id": "SKINCARE", "is_staff": True, "confidence": 0.98, "dwell_ms": 0,
        "queue_depth": None, "sku_zone": "MOISTURISER", "session_seq": 2
    })
    
    # Staff 2
    events.append({
        "event_id": "00000000-0002-0000-0000-000000000001", "store_id": store_id, "camera_id": "ENTRY_CAM_01",
        "visitor_id": "VIS_staff02", "event_type": "ENTRY", "timestamp": base_time - timedelta(minutes=5),
        "zone_id": "ENTRY", "is_staff": True, "confidence": 0.99, "dwell_ms": 0,
        "queue_depth": None, "sku_zone": None, "session_seq": 1
    })

    # 2. Converted Shoppers (Correlated with POS transactions)
    # VIS_001 -> correlates with TXN_00441 at 14:25:12
    v1_id = "VIS_001"
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v1_id, "event_type": "ENTRY", "timestamp": base_time + timedelta(minutes=5), "zone_id": "ENTRY", "is_staff": False, "confidence": 0.96, "session_seq": 1})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v1_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=6), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.95, "sku_zone": "MOISTURISER", "session_seq": 2})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v1_id, "event_type": "SHELF_INTERACTION", "timestamp": base_time + timedelta(minutes=7), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.94, "sku_zone": "MOISTURISER", "session_seq": 3})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v1_id, "event_type": "ZONE_DWELL", "timestamp": base_time + timedelta(minutes=7, seconds=30), "zone_id": "SKINCARE", "dwell_ms": 90000, "is_staff": False, "confidence": 0.95, "sku_zone": "MOISTURISER", "session_seq": 4})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v1_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=8), "zone_id": "SKINCARE", "dwell_ms": 120000, "is_staff": False, "confidence": 0.94, "sku_zone": "MOISTURISER", "session_seq": 5})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v1_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=21), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "sku_zone": "CHECKOUT", "session_seq": 6})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v1_id, "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=21, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.96, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 7})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v1_id, "event_type": "QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=21, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.96, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 8})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v1_id, "event_type": "PURCHASE_COMPLETED", "timestamp": base_time + timedelta(minutes=24, seconds=55), "zone_id": "EXIT", "is_staff": False, "confidence": 0.98, "session_seq": 9})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v1_id, "event_type": "EXIT", "timestamp": base_time + timedelta(minutes=25, seconds=5), "zone_id": "EXIT", "is_staff": False, "confidence": 0.97, "session_seq": 10})

    # VIS_002 -> correlates with TXN_00442 at 14:26:55
    v2_id = "VIS_002"
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v2_id, "event_type": "ENTRY", "timestamp": base_time + timedelta(minutes=7), "zone_id": "ENTRY", "is_staff": False, "confidence": 0.94, "session_seq": 1})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v2_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=8), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.92, "sku_zone": "MOISTURISER", "session_seq": 2})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v2_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=11), "zone_id": "SKINCARE", "dwell_ms": 180000, "is_staff": False, "confidence": 0.93, "sku_zone": "MOISTURISER", "session_seq": 3})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v2_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=23), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "sku_zone": "CHECKOUT", "session_seq": 4})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v2_id, "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=23, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.94, "queue_depth": 2, "sku_zone": "CHECKOUT", "session_seq": 5})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v2_id, "event_type": "QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=23, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.94, "queue_depth": 2, "sku_zone": "CHECKOUT", "session_seq": 6})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v2_id, "event_type": "PURCHASE_COMPLETED", "timestamp": base_time + timedelta(minutes=26, seconds=30), "zone_id": "EXIT", "is_staff": False, "confidence": 0.97, "session_seq": 7})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v2_id, "event_type": "EXIT", "timestamp": base_time + timedelta(minutes=26, seconds=45), "zone_id": "EXIT", "is_staff": False, "confidence": 0.96, "session_seq": 8})

    # VIS_003 -> correlates with TXN_00443 at 14:35:10
    v3_id = "VIS_003"
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v3_id, "event_type": "ENTRY", "timestamp": base_time + timedelta(minutes=15), "zone_id": "ENTRY", "is_staff": False, "confidence": 0.95, "session_seq": 1})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "COSMETICS_CAM_03", "visitor_id": v3_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=16), "zone_id": "COSMETICS", "is_staff": False, "confidence": 0.94, "sku_zone": "LIPSTICK", "session_seq": 2})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "COSMETICS_CAM_03", "visitor_id": v3_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=22), "zone_id": "COSMETICS", "dwell_ms": 360000, "is_staff": False, "confidence": 0.95, "sku_zone": "LIPSTICK", "session_seq": 3})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v3_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=31), "zone_id": "BILLING", "is_staff": False, "confidence": 0.94, "sku_zone": "CHECKOUT", "session_seq": 4})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v3_id, "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=31, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.93, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 5})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v3_id, "event_type": "QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=31, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.93, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 6})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v3_id, "event_type": "PURCHASE_COMPLETED", "timestamp": base_time + timedelta(minutes=34, seconds=40), "zone_id": "EXIT", "is_staff": False, "confidence": 0.98, "session_seq": 7})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v3_id, "event_type": "EXIT", "timestamp": base_time + timedelta(minutes=34, seconds=55), "zone_id": "EXIT", "is_staff": False, "confidence": 0.97, "session_seq": 8})

    # VIS_004 -> correlates with TXN_00444 at 14:42:00
    v4_id = "VIS_004"
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v4_id, "event_type": "ENTRY", "timestamp": base_time + timedelta(minutes=20), "zone_id": "ENTRY", "is_staff": False, "confidence": 0.95, "session_seq": 1})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v4_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=21), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.94, "sku_zone": "MOISTURISER", "session_seq": 2})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v4_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=28), "zone_id": "SKINCARE", "dwell_ms": 420000, "is_staff": False, "confidence": 0.95, "sku_zone": "MOISTURISER", "session_seq": 3})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v4_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=38), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "sku_zone": "CHECKOUT", "session_seq": 4})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v4_id, "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=38, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 2, "sku_zone": "CHECKOUT", "session_seq": 5})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v4_id, "event_type": "QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=38, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 2, "sku_zone": "CHECKOUT", "session_seq": 6})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v4_id, "event_type": "PURCHASE_COMPLETED", "timestamp": base_time + timedelta(minutes=41, seconds=40), "zone_id": "EXIT", "is_staff": False, "confidence": 0.98, "session_seq": 7})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v4_id, "event_type": "EXIT", "timestamp": base_time + timedelta(minutes=41, seconds=55), "zone_id": "EXIT", "is_staff": False, "confidence": 0.97, "session_seq": 8})

    # VIS_005 -> correlates with TXN_00445 at 14:50:30
    v5_id = "VIS_005"
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v5_id, "event_type": "ENTRY", "timestamp": base_time + timedelta(minutes=28), "zone_id": "ENTRY", "is_staff": False, "confidence": 0.95, "session_seq": 1})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v5_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=29), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.94, "sku_zone": "MOISTURISER", "session_seq": 2})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v5_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=35), "zone_id": "SKINCARE", "dwell_ms": 360000, "is_staff": False, "confidence": 0.95, "sku_zone": "MOISTURISER", "session_seq": 3})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v5_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=46), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "sku_zone": "CHECKOUT", "session_seq": 4})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v5_id, "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=46, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 5})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v5_id, "event_type": "QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=46, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 6})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v5_id, "event_type": "PURCHASE_COMPLETED", "timestamp": base_time + timedelta(minutes=50, seconds=10), "zone_id": "EXIT", "is_staff": False, "confidence": 0.98, "session_seq": 7})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v5_id, "event_type": "EXIT", "timestamp": base_time + timedelta(minutes=50, seconds=25), "zone_id": "EXIT", "is_staff": False, "confidence": 0.97, "session_seq": 8})

    # VIS_006 -> correlates with TXN_00446 at 15:10:15
    v6_id = "VIS_006"
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v6_id, "event_type": "ENTRY", "timestamp": base_time + timedelta(minutes=32), "zone_id": "ENTRY", "is_staff": False, "confidence": 0.95, "session_seq": 1})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "COSMETICS_CAM_03", "visitor_id": v6_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=33), "zone_id": "COSMETICS", "is_staff": False, "confidence": 0.94, "sku_zone": "LIPSTICK", "session_seq": 2})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "COSMETICS_CAM_03", "visitor_id": v6_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=42), "zone_id": "COSMETICS", "dwell_ms": 540000, "is_staff": False, "confidence": 0.95, "sku_zone": "LIPSTICK", "session_seq": 3})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v6_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(hours=1, minutes=6), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "sku_zone": "CHECKOUT", "session_seq": 4})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v6_id, "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time + timedelta(hours=1, minutes=6, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 5})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v6_id, "event_type": "QUEUE_JOIN", "timestamp": base_time + timedelta(hours=1, minutes=6, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 6})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v6_id, "event_type": "PURCHASE_COMPLETED", "timestamp": base_time + timedelta(hours=1, minutes=9, seconds=55), "zone_id": "EXIT", "is_staff": False, "confidence": 0.98, "session_seq": 7})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v6_id, "event_type": "EXIT", "timestamp": base_time + timedelta(hours=1, minutes=10, seconds=10), "zone_id": "EXIT", "is_staff": False, "confidence": 0.97, "session_seq": 8})

    # VIS_007 -> correlates with TXN_00447 at 15:15:00
    v7_id = "VIS_007"
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v7_id, "event_type": "ENTRY", "timestamp": base_time + timedelta(minutes=35), "zone_id": "ENTRY", "is_staff": False, "confidence": 0.95, "session_seq": 1})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v7_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=36), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.94, "sku_zone": "MOISTURISER", "session_seq": 2})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v7_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=45), "zone_id": "SKINCARE", "dwell_ms": 540000, "is_staff": False, "confidence": 0.95, "sku_zone": "MOISTURISER", "session_seq": 3})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v7_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(hours=1, minutes=11), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "sku_zone": "CHECKOUT", "session_seq": 4})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v7_id, "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time + timedelta(hours=1, minutes=11, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 5})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v7_id, "event_type": "QUEUE_JOIN", "timestamp": base_time + timedelta(hours=1, minutes=11, seconds=30), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 1, "sku_zone": "CHECKOUT", "session_seq": 6})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v7_id, "event_type": "PURCHASE_COMPLETED", "timestamp": base_time + timedelta(hours=1, minutes=14, seconds=45), "zone_id": "EXIT", "is_staff": False, "confidence": 0.98, "session_seq": 7})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v7_id, "event_type": "EXIT", "timestamp": base_time + timedelta(hours=1, minutes=14, seconds=55), "zone_id": "EXIT", "is_staff": False, "confidence": 0.97, "session_seq": 8})

    # 3. Queue Abandoner
    # VIS_008 -> abandons billing queue
    v8_id = "VIS_008"
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v8_id, "event_type": "ENTRY", "timestamp": base_time + timedelta(minutes=22), "zone_id": "ENTRY", "is_staff": False, "confidence": 0.94, "session_seq": 1})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v8_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=23), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.92, "sku_zone": "MOISTURISER", "session_seq": 2})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v8_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=26), "zone_id": "SKINCARE", "dwell_ms": 180000, "is_staff": False, "confidence": 0.93, "sku_zone": "MOISTURISER", "session_seq": 3})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v8_id, "event_type": "ZONE_ENTER", "timestamp": base_time + timedelta(minutes=34), "zone_id": "BILLING", "is_staff": False, "confidence": 0.94, "sku_zone": "CHECKOUT", "session_seq": 4})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v8_id, "event_type": "BILLING_QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=34, seconds=10), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 3, "sku_zone": "CHECKOUT", "session_seq": 5})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v8_id, "event_type": "QUEUE_JOIN", "timestamp": base_time + timedelta(minutes=34, seconds=10), "zone_id": "BILLING", "is_staff": False, "confidence": 0.95, "queue_depth": 3, "sku_zone": "CHECKOUT", "session_seq": 6})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v8_id, "event_type": "BILLING_QUEUE_ABANDON", "timestamp": base_time + timedelta(minutes=38, seconds=30), "zone_id": "BILLING", "dwell_ms": 260000, "is_staff": False, "confidence": 0.93, "sku_zone": "CHECKOUT", "session_seq": 7})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v8_id, "event_type": "QUEUE_EXIT", "timestamp": base_time + timedelta(minutes=38, seconds=30), "zone_id": "BILLING", "dwell_ms": 260000, "is_staff": False, "confidence": 0.93, "sku_zone": "CHECKOUT", "session_seq": 8})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "BILLING_CAM_04", "visitor_id": v8_id, "event_type": "ZONE_EXIT", "timestamp": base_time + timedelta(minutes=38, seconds=35), "zone_id": "BILLING", "dwell_ms": 275000, "is_staff": False, "confidence": 0.92, "sku_zone": "CHECKOUT", "session_seq": 9})
    events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v8_id, "event_type": "EXIT", "timestamp": base_time + timedelta(minutes=38, seconds=50), "zone_id": "EXIT", "is_staff": False, "confidence": 0.94, "session_seq": 10})

    # 4. Non-Converting Browsing Customers (Funnel sequential support)
    # 12 additional unique customer visitors VIS_009 to VIS_020
    for idx in range(9, 21):
        v_id = f"VIS_{idx:03d}"
        # Start time spread sequentially
        v_start = base_time + timedelta(minutes=(idx - 9) * 3)
        # Entry
        events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "ENTRY_CAM_01", "visitor_id": v_id, "event_type": "ENTRY", "timestamp": v_start, "zone_id": "ENTRY", "is_staff": False, "confidence": 0.90, "session_seq": 1})
        
        # Alternate browsing skincare or cosmetics
        if idx % 2 == 0:
            events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v_id, "event_type": "ZONE_ENTER", "timestamp": v_start + timedelta(minutes=1), "zone_id": "SKINCARE", "is_staff": False, "confidence": 0.91, "sku_zone": "MOISTURISER", "session_seq": 2})
            events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v_id, "event_type": "ZONE_DWELL", "timestamp": v_start + timedelta(minutes=2), "zone_id": "SKINCARE", "dwell_ms": 60000, "is_staff": False, "confidence": 0.90, "sku_zone": "MOISTURISER", "session_seq": 3})
            events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "SKINCARE_CAM_02", "visitor_id": v_id, "event_type": "ZONE_EXIT", "timestamp": v_start + timedelta(minutes=3), "zone_id": "SKINCARE", "dwell_ms": 120000, "is_staff": False, "confidence": 0.91, "sku_zone": "MOISTURISER", "session_seq": 4})
        else:
            events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "COSMETICS_CAM_03", "visitor_id": v_id, "event_type": "ZONE_ENTER", "timestamp": v_start + timedelta(minutes=1), "zone_id": "COSMETICS", "is_staff": False, "confidence": 0.91, "sku_zone": "LIPSTICK", "session_seq": 2})
            events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "COSMETICS_CAM_03", "visitor_id": v_id, "event_type": "ZONE_DWELL", "timestamp": v_start + timedelta(minutes=2), "zone_id": "COSMETICS", "dwell_ms": 60000, "is_staff": False, "confidence": 0.90, "sku_zone": "LIPSTICK", "session_seq": 3})
            events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "COSMETICS_CAM_03", "visitor_id": v_id, "event_type": "ZONE_EXIT", "timestamp": v_start + timedelta(minutes=3), "zone_id": "COSMETICS", "dwell_ms": 120000, "is_staff": False, "confidence": 0.91, "sku_zone": "LIPSTICK", "session_seq": 4})

        # Exit
        events.append({"event_id": str(uuid.uuid4()), "store_id": store_id, "camera_id": "EXIT_CAM_05", "visitor_id": v_id, "event_type": "EXIT", "timestamp": v_start + timedelta(minutes=4), "zone_id": "EXIT", "is_staff": False, "confidence": 0.92, "session_seq": 5})

    # Sort all events chronologically to guarantee absolute timestamp ordering in output streams
    events.sort(key=lambda x: x["timestamp"])
    return events

def seed_database(db: Session = None, store_id="STORE_BLR_002"):
    """
    Ensures db tables are created, clears previous data, and seeds fresh high-fidelity visitor analytics.
    """
    logger.info("Initializing database schema check & migrations...")
    Base.metadata.create_all(bind=engine)
    
    close_db_needed = False
    if db is None:
        db = SessionLocal()
        close_db_needed = True

    try:
        logger.info(f"Clearing historical telemetry data for store {store_id} in Neon PostgreSQL...")
        db.query(DBEvent).filter(DBEvent.store_id == store_id).delete()
        db.commit()
        logger.info("Database cleared cleanly.")

        # Generate realistic dataset
        logger.info("Generating realistic high-fidelity retail events...")
        raw_events = generate_retail_events(store_id)
        
        db_events = []
        for raw in raw_events:
            db_event = DBEvent(
                event_id=raw["event_id"],
                store_id=raw["store_id"],
                camera_id=raw["camera_id"],
                visitor_id=raw["visitor_id"],
                event_type=raw["event_type"],
                timestamp=raw["timestamp"],
                zone_id=raw.get("zone_id"),
                dwell_ms=raw.get("dwell_ms", 0),
                is_staff=raw.get("is_staff", False),
                confidence=raw.get("confidence", 1.0),
                queue_depth=raw.get("queue_depth"),
                sku_zone=raw.get("sku_zone"),
                session_seq=raw.get("session_seq", 1)
            )
            db_events.append(db_event)
            db.add(db_event)

        logger.info(f"Persisting and committing {len(db_events)} events to cloud database...")
        db.commit()
        logger.info("✅ Database Seeding Completed Successfully!")
        return len(db_events)
    except Exception as e:
        logger.error(f"❌ Failed to seed database: {e}")
        db.rollback()
        raise e
    finally:
        if close_db_needed:
            db.close()

if __name__ == "__main__":
    seed_database()
