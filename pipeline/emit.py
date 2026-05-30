import uuid
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

class EventEmitter:
    def __init__(self, output_path):
        self.output_path = output_path
        # Ensure outputs directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    def create_event(self, store_id, camera_id, visitor_id, event_type, timestamp, zone_id=None, dwell_ms=0, is_staff=False, confidence=1.0, queue_depth=None, sku_zone=None, session_seq=1):
        """
        Builds and validates an event dictionary according to the Purplle event schema
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "store_id": store_id,
            "camera_id": camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": timestamp if isinstance(timestamp, str) else timestamp.isoformat().replace("+00:00", "Z"),
            "zone_id": zone_id,
            "dwell_ms": int(dwell_ms),
            "is_staff": bool(is_staff),
            "confidence": float(round(confidence, 2)),
            "metadata": {
                "queue_depth": int(queue_depth) if queue_depth is not None else None,
                "sku_zone": sku_zone,
                "session_seq": int(session_seq)
            }
        }
        return event

    def emit(self, event):
        """
        Appends a validated event into the output JSONL file
        """
        try:
            with open(self.output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event) + "\n")
            
            # Structured log for event emission
            logger.info(f"Event EMITTED | ID: {event.get('event_id')} | Type: {event.get('event_type')} | Cam: {event.get('camera_id')} | Visitor: {event.get('visitor_id')}")
        except Exception as e:
            logger.error(f"Error emitting event: {e}")
