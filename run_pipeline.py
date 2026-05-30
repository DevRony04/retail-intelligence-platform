"""
Apex Retail - Unified Pipeline Execution & Event Ingestion Script
----------------------------------------------------------------
This script integrates all parts of the Store Intelligence System.
It runs the Computer Vision tracking pipeline across all three standard camera angles,
collects the emitted behavioral events, and automatically ingests them into the
FastAPI REST API database (or falls back to direct SQLAlchemy database writes if offline).

Author: Antigravity Agent
"""

import os
import sys
import json
import subprocess
import requests
from datetime import datetime

# Add root directory to path to ensure app imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Default configuration
STORE_ID = "STORE_BLR_002"
LAYOUT_PATH = "data/store_layout.json"
OUTPUT_PATH = "outputs/events.jsonl"
API_URL = os.getenv("API_URL", "http://localhost:8000")

def run_camera_pipeline(camera_id, video_path=None, simulation=False):
    """
    Invokes the pipeline/detect.py script as a subprocess to process a camera stream
    """
    cmd = [
        sys.executable, "pipeline/detect.py",
        "--store-id", STORE_ID,
        "--camera-id", camera_id,
        "--layout-json", LAYOUT_PATH,
        "--output-jsonl", OUTPUT_PATH
    ]
    if video_path and os.path.exists(video_path) and not simulation:
        cmd.extend(["--video", video_path])
        print(f"Running real CV pipeline for camera {camera_id} with video {video_path}...")
    else:
        cmd.append("--simulation")
        print(f"Running high-fidelity simulation pipeline for camera {camera_id}...")

    try:
        # Run subprocess and print output (using UTF-8 encoding to prevent Windows cp1252 decode errors)
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running pipeline for camera {camera_id}: {e}")
        print(f"Subprocess error output:\n{e.stderr}")
        return False

def ingest_emitted_events(jsonl_path, api_url=API_URL):
    """
    Ingests the generated event log from JSONL format into the backend database.
    Attempts to POST to the running FastAPI server first, batching up to 500 events.
    Falls back to direct SQLAlchemy database insertion if the FastAPI server is offline.
    """
    if not os.path.exists(jsonl_path):
        print(f"Error: Event log file {jsonl_path} does not exist.")
        return False

    events = []
    print(f"Parsing event logs from {jsonl_path}...")
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except Exception as e:
                    print(f"Warning: Skipping invalid JSON line at line {line_num}: {e}")

    if not events:
        print("No events found in the event log file to ingest.")
        return True

    print(f"Successfully loaded {len(events)} events. Starting integration ingestion...")

    # Check if API server is reachable
    api_online = False
    try:
        r = requests.get(f"{api_url}/health", timeout=2)
        if r.status_code == 200:
            api_online = True
    except Exception:
        pass

    if api_online:
        print(f"FastAPI server is active at {api_url}. Ingesting events via REST API batch endpoint...")
        # Batch events (API constraint: max 500 per batch)
        batch_size = 500
        success_total = 0
        failed_total = 0
        
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(events) - 1) // batch_size + 1
            
            try:
                resp = requests.post(f"{api_url}/events/ingest", json=batch, timeout=10)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    success_total += data.get("success_count", 0)
                    failed_total += data.get("failed_count", 0)
                    print(f"  Batch {batch_num}/{total_batches}: Ingested successfully (Success: {data.get('success_count')}, Failed: {data.get('failed_count')})")
                else:
                    print(f"  Batch {batch_num}/{total_batches}: Failed with HTTP status {resp.status_code}. Response: {resp.text}")
                    failed_total += len(batch)
            except Exception as req_err:
                print(f"  Batch {batch_num}/{total_batches}: Request error: {req_err}")
                failed_total += len(batch)
                
        print(f"\nIngestion via API Complete! Total Success: {success_total}, Total Failed: {failed_total}")
        return failed_total == 0

    else:
        print("\nFastAPI server is not running. Falling back to direct database insertion...")
        try:
            from app.database import SessionLocal, engine, Base
            from app.models import DBEvent
            
            # Ensure database schema is deployed
            Base.metadata.create_all(bind=engine)
            
            db = SessionLocal()
            success_count = 0
            duplicates_count = 0
            
            try:
                for event in events:
                    # Deduplication (Idempotency check)
                    existing = db.query(DBEvent).filter(DBEvent.event_id == event["event_id"]).first()
                    if existing:
                        duplicates_count += 1
                        success_count += 1
                        continue

                    # Create model instance
                    metadata = event.get("metadata", {})
                    ts_str = event["timestamp"].replace("Z", "")
                    # Convert to datetime object (handling standard ISO strings)
                    try:
                        timestamp_dt = datetime.fromisoformat(ts_str)
                    except ValueError:
                        timestamp_dt = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S")

                    db_event = DBEvent(
                         event_id=event["event_id"],
                         store_id=event["store_id"],
                         camera_id=event["camera_id"],
                         visitor_id=event["visitor_id"],
                         event_type=event["event_type"],
                         timestamp=timestamp_dt,
                         zone_id=event.get("zone_id"),
                         dwell_ms=event.get("dwell_ms", 0),
                         is_staff=event.get("is_staff", False),
                         confidence=event.get("confidence", 1.0),
                         queue_depth=metadata.get("queue_depth"),
                         sku_zone=metadata.get("sku_zone"),
                         session_seq=metadata.get("session_seq", 1)
                    )
                    db.add(db_event)
                    success_count += 1
                    
                db.commit()
                print(f"Direct Database Ingestion Complete! Successfully integrated {success_count} events (including {duplicates_count} idempotent duplicates verified) directly into SQL database.")
                return True
            except Exception as db_err:
                db.rollback()
                print(f"Error writing directly to database: {db_err}")
                return False
            finally:
                db.close()
                
        except Exception as imp_err:
            print(f"Error importing database dependencies for direct ingestion: {imp_err}")
            return False

def main():
    print("=========================================================================")
    print("      APEX RETAIL - UNIFIED STORE INTELLIGENCE SYSTEM INTEGRATION")
    print("=========================================================================")
    
    # 1. Clear old event logs to ensure fresh run metrics
    if os.path.exists(OUTPUT_PATH):
        try:
            os.remove(OUTPUT_PATH)
            print("Cleared historical event log file outputs/events.jsonl.")
        except Exception as e:
            print(f"Warning: Could not remove old event log file: {e}")
            
    # Create output directories if needed
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    # Search for video directory
    video_dir = "C:/Users/deepy/Downloads/CCTV Footage-20260529T160731Z-3-00144614ea/CCTV Footage"
    
    # Run pipelines for all 5 enterprise retail cameras
    run_camera_pipeline("ENTRY_CAM_01", os.path.join(video_dir, "ENTRY_CAM_01.mp4"))
    run_camera_pipeline("SKINCARE_CAM_02", os.path.join(video_dir, "SKINCARE_CAM_02.mp4"))
    run_camera_pipeline("COSMETICS_CAM_03", os.path.join(video_dir, "COSMETICS_CAM_03.mp4"))
    run_camera_pipeline("BILLING_CAM_04", os.path.join(video_dir, "BILLING_CAM_04.mp4"))
    run_camera_pipeline("EXIT_CAM_05", os.path.join(video_dir, "EXIT_CAM_05.mp4"))
    
    # Also run the generic camera channels for complete backwards compatibility with older tests
    run_camera_pipeline("CAM_ENTRY_01", os.path.join(video_dir, "CAM 1.mp4"))
    run_camera_pipeline("CAM_FLOOR_01", os.path.join(video_dir, "CAM 2.mp4"))
    run_camera_pipeline("CAM_BILLING_01", os.path.join(video_dir, "CAM 3.mp4"))

    print("\n-------------------------------------------------------------------------")
    print("             PIPELINE COMPLETE - INGESTING PROCESSED EVENTS")
    print("-------------------------------------------------------------------------")
    
    # Ingest the generated event log
    ingest_emitted_events(OUTPUT_PATH)
    
    print("=========================================================================")
    print("    INTEGRATION COMPLETE! RUN 'python assertions.py' TO VERIFY ALL KPIs.")
    print("=========================================================================")

if __name__ == "__main__":
    main()
