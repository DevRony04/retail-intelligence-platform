# Computer Vision & Centroid Tracking Pipeline Guide

This document describes the design, coordinate math, spatial algorithms, and graceful degradation strategies implemented inside the edge AI processing pipeline.

---

## 👁️ AI Core Processing Stack

The edge processing framework (`pipeline/detect.py`) transforms raw video feeds into high-fidelity behavioral event telemetry streams.

```
+------------------------------------+
|         CCTV Video Input           |
+------------------------------------+
                  |
                  v
+------------------------------------+
|  1. YOLOv8 Nano Person Detector    |
|     - Class 0: Person Only         |
|     - Max resolution: 640px        |
+------------------------------------+
                  |
                  v
+------------------------------------+
|  2. stable Centroid ByteTrack      |
|     - Centroid tracking algorithm  |
|     - Missed frame threshold: 45   |
+------------------------------------+
                  |
                  v
+------------------------------------+
|  3. Ray-Casting Polygon In/Out     |
|     - Point-in-polygon checks      |
|     - Zone entering & transition   |
+------------------------------------+
                  |
                  v
+------------------------------------+
|  4. Asynchronous Event Emitting    |
|     - Emits ENTRY, DWELL, EXIT     |
+------------------------------------+
```

---

## 📐 Bounding Box to Centroid Mapping

To perform accurate spatial mapping, we reduce the shopper's 2D bounding box coordinate `[x1, y1, x2, y2]` to a single 2D spatial centroid `(cx, cy)` representing the shopper's physical footprint on the retail floor:

$$cx = \frac{x1 + x2}{2}$$
$$cy = y2$$

* **Design Decision:** We use the bottom-center of the bounding box ($y2$) instead of the center ($y1 + y2 / 2$) as the tracking anchor coordinate. In a perspective-warped CCTV setup, the bottom of the bounding box corresponds to the customer's actual feet contacting the retail floor, ensuring far more accurate polygon region overlap testing.

---

## 🎯 Spatial Point-in-Polygon Ray Casting

To determine if a shopper's centroid is inside a retail zone (e.g. `SKINCARE` or `COSMETICS`), the system employs a high-performance 2D ray-casting intersection algorithm (`pipeline/zones.py`).

### Ray-Casting Principle
A horizontal ray is cast from the centroid point $(x, y)$ extending infinitely to the right $(+x)$. We count how many times this ray intersects with the segments of the zone polygon.
* **Odd number of intersections** $\implies$ The point is **inside** the polygon.
* **Even number of intersections** $\implies$ The point is **outside** the polygon.

```text
    Outside Polygon                  Inside Polygon
    +-------------+                 +-------------+
    |             |                 |   (x,y)-----> [1 Intersection (ODD)]
    |   (x,y)-----------> [2 Intersections (EVEN)]|
    |             |                 |             |
    +-------------+                 +-------------+
```

---

## 📈 Stable Re-ID Centroid Association

Shopper trajectories are tracked using a custom Kalman-filter-inspired centroid distance tracker (`pipeline/tracker.py`):
1. **Centroid Distance Calculation**: Computes Euclidean distance matrix between current frame detections and previous active tracks.
2. **Euclidean Cost Assignment**: Associates tracks to detections using a stable distance-threshold gate (e.g., maximum centroid shift $\le$ 180 pixels).
3. **Graceful Track Preservation**: If a track is briefly lost (due to temporary shopper occlusion by shelves or other customers), the track is preserved for up to 45 frames (3 seconds) in memory. This eliminates track fragmentation and keeps the tracking session cohesive.

---

## 🚀 High-Fidelity Graceful Degradation Simulation

To support frictionless testing, recruiter demos, and developer workflows when running on basic laptops or machines lacking high-performance GPU hardware, the pipeline includes a **High-Fidelity Simulation Fallback Engine**:
* If OpenCV (`cv2`) or Ultralytics (`YOLO`) is unavailable, `run_pipeline.py` automatically falls back to simulation mode.
* The simulation generates deterministic, highly realistic, chronologically ordered retail event sequences that mimic actual physical shopper movement patterns, queue joins, purchase completions, and staff patrols.
* Telemetry generated in simulation mode matches the production schemas exactly, ensuring all downstream APIs and dashboards function perfectly.
