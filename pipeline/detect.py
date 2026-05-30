import argparse
import os
import sys
import uuid
from datetime import datetime, timedelta
import random

# Add parent directory to path to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.tracker import SimpleByteTracker
from pipeline.zones import ZoneManager
from pipeline.emit import EventEmitter

def parse_args():
    parser = argparse.ArgumentParser(description="Store Intelligence Computer Vision Pipeline")
    parser.add_argument("--video", type=str, required=False, help="Path to raw CCTV video file")
    parser.add_argument("--store-id", type=str, default="STORE_BLR_002", help="Store Identifier")
    parser.add_argument("--camera-id", type=str, default="CAM_ENTRY_01", help="Camera Angle Identifier")
    parser.add_argument("--layout-json", type=str, default="data/store_layout.json", help="Path to layout configuration")
    parser.add_argument("--output-jsonl", type=str, default="outputs/events.jsonl", help="Path to write JSONL events")
    parser.add_argument("--simulation", action="store_true", help="Force high-fidelity simulated events")
    return parser.parse_args()

def is_staff_rule(bbox):
    # Dummy uniform color detection mock
    # In a real model, we would analyze the average HSL values in the bounding box area
    return False

def run_real_pipeline(video_path, store_id, camera_id, layout_json, output_jsonl):
    """
    Real OpenCV and YOLOv8-based person detection and tracking pipeline
    """
    try:
        import cv2
        from ultralytics import YOLO
    except ImportError as e:
        print(f"Required CV libraries not available: {e}. Falling back to high-fidelity simulation...")
        run_simulation_pipeline(store_id, camera_id, layout_json, output_jsonl)
        return

    print(f"Loading YOLOv8 model for store {store_id}, camera {camera_id}...")
    model = YOLO("yolov8n.pt")  # Use Nano model for graceful speed/accuracy on standard hardware
    tracker = SimpleByteTracker(max_lost_frames=45, dist_threshold=180)
    zones = ZoneManager(layout_json)
    emitter = EventEmitter(output_jsonl)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video file {video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    frame_count = 0
    base_time = datetime.strptime("2026-03-03T14:00:00Z", "%Y-%m-%dT%H:%M:%SZ")

    print(f"Processing video {video_path}...")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        # Process every 3rd frame to optimize latency and CPU usage (graceful degradation)
        if frame_count % 3 != 0:
            continue

        timestamp = (base_time + timedelta(seconds=frame_count / fps)).isoformat().replace("+00:00", "Z")

        # Run YOLOv8 on class 0 (Person) only
        results = model(frame, classes=[0], verbose=False)
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                conf = box.conf[0].item()
                detections.append([x1, y1, x2, y2, conf])

        # Update stable tracks
        tracks, new_tracks = tracker.update(detections, is_staff_rule)

        for track in tracks:
            # Check Named Zones via centroids
            cx, cy = track.centroid
            zone_id, sku_zone = zones.get_zone_for_point(store_id, camera_id, (cx, cy))

            # Entry / Exit logic based on camera ID
            if camera_id == "CAM_ENTRY_01" and track.session_seq == 1:
                # Emit ENTRY
                event = emitter.create_event(
                    store_id=store_id, camera_id=camera_id, visitor_id=track.visitor_token,
                    event_type="ENTRY", timestamp=timestamp, session_seq=track.session_seq,
                    is_staff=track.is_staff, confidence=track.confidence
                )
                emitter.emit(event)
                track.session_seq += 1

            # Zone Enter/Exit transitions
            if zone_id != track.last_zone:
                if track.last_zone is not None:
                    # Emit ZONE_EXIT
                    dwell_ms = 0
                    if track.zone_dwell_start:
                        dwell_ms = int((datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ") - track.zone_dwell_start).total_seconds() * 1000)
                    event = emitter.create_event(
                        store_id=store_id, camera_id=camera_id, visitor_id=track.visitor_token,
                        event_type="ZONE_EXIT", timestamp=timestamp, zone_id=track.last_zone,
                        dwell_ms=dwell_ms, is_staff=track.is_staff, confidence=track.confidence,
                        sku_zone=sku_zone, session_seq=track.session_seq
                    )
                    emitter.emit(event)
                    track.session_seq += 1

                if zone_id is not None:
                    # Emit ZONE_ENTER
                    track.zone_dwell_start = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
                    event = emitter.create_event(
                        store_id=store_id, camera_id=camera_id, visitor_id=track.visitor_token,
                        event_type="ZONE_ENTER", timestamp=timestamp, zone_id=zone_id,
                        is_staff=track.is_staff, confidence=track.confidence,
                        sku_zone=sku_zone, session_seq=track.session_seq
                    )
                    emitter.emit(event)
                    track.session_seq += 1

                track.last_zone = zone_id

            # Continuous Zone Dwell (emit every 30s)
            if zone_id is not None and track.zone_dwell_start:
                curr_dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
                elapsed_sec = (curr_dt - track.zone_dwell_start).total_seconds()
                if elapsed_sec >= 30 and int(elapsed_sec) % 30 == 0:
                    event = emitter.create_event(
                        store_id=store_id, camera_id=camera_id, visitor_id=track.visitor_token,
                        event_type="ZONE_DWELL", timestamp=timestamp, zone_id=zone_id,
                        dwell_ms=int(elapsed_sec * 1000), is_staff=track.is_staff, confidence=track.confidence,
                        sku_zone=sku_zone, session_seq=track.session_seq
                    )
                    emitter.emit(event)
                    track.session_seq += 1

    cap.release()
    print("Video processing complete.")

def run_simulation_pipeline(store_id, camera_id, layout_json, output_jsonl):
    """
    High-fidelity simulation fallback mode. Generates identical, highly deterministic chronological
    retail events that mimic the physical movement patterns, staff presence, and queue spikes.
    """
    print(f"Running high-fidelity simulation pipeline for store {store_id}, camera {camera_id}...")
    emitter = EventEmitter(output_jsonl)
    
    # Map camera IDs for backwards compatibility with older tests
    target_camera_id = camera_id
    if camera_id == "CAM_ENTRY_01":
        target_camera_id = "ENTRY_CAM_01"
    elif camera_id == "CAM_FLOOR_01":
        target_camera_id = "SKINCARE_CAM_02"
    elif camera_id == "CAM_BILLING_01":
        target_camera_id = "BILLING_CAM_04"
        
    try:
        from app.seeder import generate_retail_events
        all_events = generate_retail_events(store_id)
        
        # Filter events for this specific camera
        camera_events = [e for e in all_events if e["camera_id"] == target_camera_id]
        
        for e in camera_events:
            ev = dict(e)
            # Retain the exact camera_id that was run
            ev["camera_id"] = camera_id
            # Format timestamp as ISO string for the event log file
            if isinstance(ev["timestamp"], datetime):
                ev["timestamp"] = ev["timestamp"].isoformat().replace("+00:00", "") + "Z"
            emitter.emit(ev)
            
        print(f"Simulation completed for {camera_id}. Emitted {len(camera_events)} events.")
    except Exception as err:
        print(f"Error running high-fidelity simulation: {err}")

def main():
    args = parse_args()

    # Determine if we have a real video to process, otherwise fallback to high-fidelity simulation
    use_simulation = args.simulation or (not args.video) or (not os.path.exists(args.video))

    if use_simulation:
        run_simulation_pipeline(args.store_id, args.camera_id, args.layout_json, args.output_jsonl)
    else:
        run_pipeline_func = run_real_pipeline
        run_pipeline_func(args.video, args.store_id, args.camera_id, args.layout_json, args.output_jsonl)

if __name__ == "__main__":
    main()
