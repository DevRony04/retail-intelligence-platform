from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any, List
from app.database import get_db
from app.models import DBEvent

router = APIRouter(prefix="/stores", tags=["Analytics"])

@router.get("/{store_id}/heatmap")
def get_store_heatmap(store_id: str, db: Session = Depends(get_db)):
    """
    Returns zone visit frequencies and average dwell times, normalized 0-100.
    Includes data_confidence flag if sessions count is low (< 20).
    """
    # 1. Total visitor session count in store
    sessions = db.query(DBEvent.visitor_id)\
        .filter(DBEvent.store_id == store_id)\
        .filter(DBEvent.is_staff == False)\
        .distinct().all()
    session_count = len(sessions)
    data_confidence = session_count >= 20

    # 2. Fetch absolute visit count and average dwell per zone
    # We group by zone_id, excluding Entry/Exit (None zone_id)
    zone_stats = db.query(
        DBEvent.zone_id,
        func.count(func.distinct(DBEvent.visitor_id)).label("visits"),
        func.avg(DBEvent.dwell_ms).label("avg_dwell")
    ).filter(DBEvent.store_id == store_id)\
     .filter(DBEvent.is_staff == False)\
     .filter(DBEvent.zone_id.isnot(None))\
     .filter(DBEvent.event_type.in_(["ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL", "BILLING_QUEUE_ABANDON"]))\
     .group_by(DBEvent.zone_id).all()

    if not zone_stats:
        return {
            "store_id": store_id,
            "data_confidence": data_confidence,
            "zones": {}
        }

    # 3. Find max values for normalization
    max_visits = float(max(stats[1] for stats in zone_stats)) if zone_stats else 1.0
    raw_max_dwell = max(stats[2] for stats in zone_stats if stats[2] is not None) if zone_stats else 1.0
    max_dwell = float(raw_max_dwell) if raw_max_dwell is not None else 1.0
    if max_dwell == 0:
        max_dwell = 1.0

    # 4. Generate normalized heatmap
    heatmap_zones = {}
    for zone_id, visits, avg_dwell in zone_stats:
        avg_dwell_val = float(avg_dwell) if avg_dwell is not None else 0.0
        visits_val = float(visits)
        
        # Normalize 0 - 100
        norm_freq = (visits_val / max_visits) * 100.0 if max_visits > 0 else 0.0
        norm_dwell = (avg_dwell_val / max_dwell) * 100.0 if max_dwell > 0 else 0.0
        
        # Combined heatmap intensity index (weighted average)
        intensity = (norm_freq * 0.5) + (norm_dwell * 0.5)
        
        heatmap_zones[zone_id] = {
            "absolute_visits": visits,
            "absolute_dwell_ms": float(round(avg_dwell_val, 2)),
            "normalized_frequency": float(round(norm_freq, 2)),
            "normalized_dwell": float(round(norm_dwell, 2)),
            "heatmap_intensity": float(round(intensity, 2))
        }

    return {
        "store_id": store_id,
        "data_confidence": data_confidence,
        "zones": heatmap_zones
    }
