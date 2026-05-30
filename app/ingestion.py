from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Dict, Any
from app.database import get_db
from app.models import EventSchema, DBEvent
from pydantic import ValidationError
from dotenv import load_dotenv
from loguru import logger

# Ensure environment variables are loaded
load_dotenv()

router = APIRouter(prefix="/events", tags=["Ingestion"])

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_events(batch: List[Dict[str, Any]], db: Session = Depends(get_db)):
    """
    Ingests a batch of up to 500 store events. Handles idempotency by event_id,
    performs robust Pydantic validation, and supports partial success with structured errors.
    """
    logger.info(f"API Ingestion: Received batch of {len(batch)} events to process.")
    
    if len(batch) > 500:
        logger.warning(f"API Ingestion rejected: Batch size of {len(batch)} exceeds maximum limit of 500 events.")
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
            logger.warning(f"API Ingestion validation failure | Index: {idx} | ID: {raw_event.get('event_id', 'unknown')} | Details: {ve.errors()}")
            errors.append({
                "index": idx,
                "event_id": raw_event.get("event_id", "unknown"),
                "error": "Validation Error",
                "details": ve.errors()
            })
            continue
        except Exception as e:
            logger.warning(f"API Ingestion parsing failure | Index: {idx} | ID: {raw_event.get('event_id', 'unknown')} | Error: {str(e)}")
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
            logger.info(f"API Ingestion duplicate skipped | ID: {event_data.event_id} | Treated as successful (idempotent)")
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
        
        # 3. Queue DB Insert inside a nested SAVEPOINT
        # This isolates individual row insertion failures so that the outer transaction
        # remains healthy and other events in the batch are committed successfully.
        try:
            with db.begin_nested():
                db.add(db_event)
                db.flush()
            logger.info(f"API Ingestion event staged | ID: {event_data.event_id} | Type: {event_data.event_type} | Cam: {event_data.camera_id}")
            success_count += 1
        except IntegrityError:
            # If a concurrent query or duplicate event is flushed, treat as successful (idempotency)
            # The nested transaction is automatically rolled back to the savepoint
            logger.info(f"API Ingestion database duplicate bypassed | ID: {event_data.event_id}")
            success_count += 1
        except Exception as e:
            # Any other database write failure will only roll back this event's savepoint
            logger.error(f"API Ingestion SAVEPOINT failure | ID: {event_data.event_id} | Error: {str(e)}")
            errors.append({
                "index": idx,
                "event_id": event_data.event_id,
                "error": "Database Write Failure",
                "details": str(e)
            })

    # Commit all successful inserts in the batch transaction
    try:
        db.commit()
        logger.info(f"API Ingestion batch transaction committed successfully | Total Success: {success_count} | Errors: {len(errors)}")
    except Exception as e:
        logger.error(f"API Ingestion transaction COMMIT failed | Rolled back! | Error: {str(e)}")
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
