# Enterprise Retail Event Schema Specification

This document details the standardized JSON schema payload structure and semantic event types processed by the Store Intelligence System edge AI pipeline and database ingestion gateways.

---

## 📐 Base Event Payload Schema

All computer-vision-derived telemetry events are transmitted and persisted as flat objects with a structured `metadata` dictionary containing operational context.

```json
{
  "event_id": "c8a2f1a3-ef11-4828-97fb-fa2bfa2b3a19",
  "store_id": "STORE_BLR_002",
  "camera_id": "SKINCARE_CAM_02",
  "visitor_id": "VIS_c8a2f1",
  "event_type": "SHELF_INTERACTION",
  "timestamp": "2026-03-03T14:20:45Z",
  "zone_id": "SKINCARE",
  "dwell_ms": 0,
  "is_staff": false,
  "confidence": 0.95,
  "metadata": {
    "queue_depth": null,
    "sku_zone": "MOISTURISER",
    "session_seq": 3
  }
}
```

### Field Definitions

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `event_id` | String | Required, UUIDv4, Unique | Globally unique token for strict idempotency and deduplication at backend gateways. |
| `store_id` | String | Required, Max 50 chars | Identifier matching active retail layouts (e.g. `STORE_BLR_002`). |
| `camera_id`| String | Required, Max 50 chars | Camera source producing the track (e.g. `ENTRY_CAM_01`, `BILLING_CAM_04`). |
| `visitor_id`| String | Required, Max 50 chars | Re-ID tracking token mapping shopper session. |
| `event_type`| String | Enum (Allowed Types) | Retail behavior tag (see semantic types list). |
| `timestamp` | String | Required, ISO-8601 UTC | Timezone-aware UTC ISO timestamp format (e.g. `YYYY-MM-DDTHH:MM:SSZ`). |
| `zone_id` | String | Optional, Nullable | Spatial polygon zone matching layout (e.g. `SKINCARE`, `BILLING`). |
| `dwell_ms` | Integer | Optional, Default 0 | Duration of interaction in milliseconds (populated on exit/dwell events). |
| `is_staff` | Boolean| Optional, Default `false` | Set to true if shopper vest/shirt color tracking rules identify employee. |
| `confidence`| Float | Required, [0.0 - 1.0] | Centroid tracker/detection score from edge model output. |
| `metadata` | Object | Required | Nested parameters (e.g. `queue_depth`, `sku_zone`, `session_seq`). |

---

## 🏷️ Semantic Retail Event Enums

The AI platform enforces 9 core production event enums:

### 1. `ENTRY`
* **Trigger:** Centroid path crosses entry door threshold from outside to inside.
* **Camera:** `ENTRY_CAM_01`
* **Context:** Initiates visitor session (sets `session_seq` to 1).

### 2. `REENTRY`
* **Trigger:** Customer exits threshold briefly and re-enters within same session (e.g. going to car/ATM).
* **Camera:** `ENTRY_CAM_01`
* **Context:** Preserves original tracking token to prevent unique visitor inflating metrics.

### 3. `ZONE_ENTER`
* **Trigger:** Bounding box centroid enters spatial zone boundary polygon.
* **Camera:** `SKINCARE_CAM_02`, `COSMETICS_CAM_03`, `BILLING_CAM_04`
* **Context:** Sets active zone tracking state and enters starting timestamp.

### 4. `ZONE_DWELL`
* **Trigger:** Bounding box centroid remains inside zone polygon for > 30 seconds.
* **Camera:** `SKINCARE_CAM_02`, `COSMETICS_CAM_03`
* **Context:** Emits continuous telemetry showing dwell duration.

### 5. `SHELF_INTERACTION`
* **Trigger:** Centroid remains stationary close to product shelving with hand/arm extension bounding overlap.
* **Camera:** `SKINCARE_CAM_02`, `COSMETICS_CAM_03`
* **Context:** Signals high product consideration/intent.

### 6. `PROMOTION_INTERACTION`
* **Trigger:** Centroid dwells in designated visual display/promo island zone footprint.
* **Camera:** `SKINCARE_CAM_02`, `COSMETICS_CAM_03`
* **Context:** Audits store display and branding visual efficiency index.

### 7. `QUEUE_JOIN` (or legacy `BILLING_QUEUE_JOIN`)
* **Trigger:** Bounding box centroid enters billing polygon queue path and joins line.
* **Camera:** `BILLING_CAM_04`
* **Context:** Logs current line length (`queue_depth`) for real-time queue wait scaling.

### 8. `QUEUE_EXIT` (or legacy `BILLING_QUEUE_ABANDON`)
* **Trigger:** Bounding box centroid exits billing polygon queue path without passing counter register.
* **Camera:** `BILLING_CAM_04`
* **Context:** Flags operational bottleneck and checkout friction alerts.

### 9. `PURCHASE_COMPLETED`
* **Trigger:** Centroid completes cashier check and crosses checkout gate path.
* **Camera:** `EXIT_CAM_05`
* **Context:** Concludes checkout transaction, correlated with POS basket sales data.

### 10. `EXIT`
* **Trigger:** Centroid crosses outer exit gate door threshold.
* **Camera:** `EXIT_CAM_05`
* **Context:** Safely closes visitor session and releases tracking token from pool.
