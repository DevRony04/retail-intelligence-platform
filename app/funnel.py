from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database import get_db
from app.models import DBEvent
from app.metrics import get_pos_transactions_for_store, get_store_metrics

router = APIRouter(prefix="/stores", tags=["Analytics"])

@router.get("/{store_id}/funnel")
def get_store_funnel(store_id: str, db: Session = Depends(get_db)):
    """
    Computes the conversion funnel: Entry -> Zone Visit -> Billing Queue -> Purchase
    Returns absolute counts per stage and drop-off percentages.
    """
    # 1. Total Entry Sessions (excluding staff)
    unique_entries = db.query(DBEvent.visitor_id)\
        .filter(DBEvent.store_id == store_id)\
        .filter(DBEvent.is_staff == False)\
        .filter(DBEvent.event_type.in_(["ENTRY", "REENTRY"]))\
        .distinct().all()
    entry_count = len(unique_entries)

    # 2. Total Zone Browse Visits (any named zone other than BILLING)
    unique_browsers = db.query(DBEvent.visitor_id)\
        .filter(DBEvent.store_id == store_id)\
        .filter(DBEvent.is_staff == False)\
        .filter(DBEvent.zone_id.isnot(None))\
        .filter(DBEvent.zone_id != "BILLING")\
        .filter(DBEvent.event_type.in_(["ZONE_ENTER", "SHELF_INTERACTION", "PROMOTION_INTERACTION"]))\
        .distinct().all()
    browse_count = len(unique_browsers)

    # 3. Total Billing Queue Joins
    unique_queue = db.query(DBEvent.visitor_id)\
        .filter(DBEvent.store_id == store_id)\
        .filter(DBEvent.is_staff == False)\
        .filter(DBEvent.event_type.in_(["BILLING_QUEUE_JOIN", "QUEUE_JOIN"]))\
        .distinct().all()
    queue_count = len(unique_queue)

    # 4. Total Purchase (Converted unique visitors via POS correlation)
    # We fetch metrics to reuse the transaction-visitor correlation logic
    metrics = get_store_metrics(store_id, db)
    purchase_count = int(metrics["unique_visitors"] * metrics["conversion_rate"])

    # Ensure counts degrade sequentially down the funnel for consistency (edge case smoothing)
    # In a real store, a visitor might walk directly to the billing zone without visiting a floor zone,
    # but for a strict funnel sequence, we ensure: Entry >= Browse >= Queue >= Purchase
    browse_count = min(entry_count, browse_count)
    queue_count = min(browse_count, queue_count)
    purchase_count = min(queue_count, purchase_count)

    # Calculate drop-off percentages
    browse_drop_off = 100.0 * (1 - (browse_count / entry_count)) if entry_count > 0 else 100.0
    queue_drop_off = 100.0 * (1 - (queue_count / browse_count)) if browse_count > 0 else 100.0
    purchase_drop_off = 100.0 * (1 - (purchase_count / queue_count)) if queue_count > 0 else 100.0

    return {
        "store_id": store_id,
        "stages": [
            {
                "stage_name": "Entry",
                "count": entry_count,
                "percentage_of_first": 100.0,
                "drop_off_from_previous": 0.0
            },
            {
                "stage_name": "Zone Visit",
                "count": browse_count,
                "percentage_of_first": float(round((browse_count / entry_count) * 100, 2)) if entry_count > 0 else 0.0,
                "drop_off_from_previous": float(round(browse_drop_off, 2))
            },
            {
                "stage_name": "Billing Queue",
                "count": queue_count,
                "percentage_of_first": float(round((queue_count / entry_count) * 100, 2)) if entry_count > 0 else 0.0,
                "drop_off_from_previous": float(round(queue_drop_off, 2))
            },
            {
                "stage_name": "Purchase",
                "count": purchase_count,
                "percentage_of_first": float(round((purchase_count / entry_count) * 100, 2)) if entry_count > 0 else 0.0,
                "drop_off_from_previous": float(round(purchase_drop_off, 2))
            }
        ]
    }
