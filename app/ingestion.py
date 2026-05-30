from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any
from app.database import get_db
from app.models import EventSchema, DBEvent
from pydantic import ValidationError

router = APIRouter(prefix="/events", tags=["Ingestion"])

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_events(batch: List[Dict[str, Any]], db: Session = Depends(get_db)):
    """
    Ingests a batch of up to 500 store events. Handles idempotency by event_id,
    performs robust Pydantic validation, and supports partial success with structured errors.
    """
    if len(batch) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch size exceeds maximum limit of 500 events"
        )
        
    success_count = 0
    errors = []
    
    for idx, raw_event in enumerate(batch):
        # 1. Validate Schema
        try:
            event_data = EventSchema(**raw_event)
        except ValidationError as ve:
            errors.append({
                "index": idx,
                "event_id": raw_event.get("event_id", "unknown"),
                "error": "Validation Error",
                "details": ve.errors()
            })
            continue
        except Exception as e:
            errors.append({
                "index": idx,
                "event_id": raw_event.get("event_id", "unknown"),
                "error": "Malformed JSON structure",
                "details": str(e)
            })
            continue

        # 2. Check Idempotency (Deduplication) in current session
        existing = db.query(DBEvent).filter(DBEvent.event_id == event_data.event_id).first()
        if existing:
            # Idempotent write: count as success and skip insertion
            success_count += 1
            continue

        # 3. Queue DB Insert
        db_event = DBEvent(
            event_id=event_data.event_id,
            store_id=event_data.store_id,
            camera_id=event_data.camera_id,
            visitor_id=event_data.visitor_id,
            event_type=event_data.event_type,
            timestamp=event_data.timestamp,
            zone_id=event_data.zone_id,
            dwell_ms=event_data.dwell_ms,
            is_staff=event_data.is_staff,
            confidence=event_data.confidence,
            # Flattened metadata
            queue_depth=event_data.metadata.queue_depth,
            sku_zone=event_data.metadata.sku_zone,
            session_seq=event_data.metadata.session_seq
        )
        
        db.add(db_event)
        
        # Flush periodically or check unique constraint on write
        try:
            db.flush()
            success_count += 1
        except IntegrityError:
            db.rollback()
            # If a concurrent query committed the same event_id, treat as successful (idempotency)
            success_count += 1
        except Exception as e:
            db.rollback()
            errors.append({
                "index": idx,
                "event_id": event_data.event_id,
                "error": "Database Write Failure",
                "details": str(e)
            })

    # Commit all successful inserts in the batch transaction
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to commit batch to database: {str(e)}"
        )

    # Return structured partial success response
    if len(errors) > 0:
        return {
            "status": "partial_success",
            "success_count": success_count,
            "failed_count": len(errors),
            "errors": errors
        }

    return {
        "status": "success",
        "success_count": success_count,
        "failed_count": 0,
        "errors": []
    }
