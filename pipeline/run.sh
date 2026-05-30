#!/bin/bash
# One-click script to run the detection pipeline across all three standard camera angles

STORE_ID="STORE_BLR_002"
LAYOUT_PATH="data/store_layout.json"
OUTPUT_PATH="outputs/events.jsonl"
VIDEO_DIR="C:/Users/deepy/Downloads/CCTV Footage-20260529T160731Z-3-00144614ea/CCTV Footage"

# Ensure output path is cleared
echo "Clearing old event log..."
rm -f "$OUTPUT_PATH"
mkdir -p outputs

echo "================================================================="
echo "Apex Retail Store Intelligence - Detection & Tracking Pipeline"
echo "Store: $STORE_ID"
echo "================================================================="

# Process Camera 1: Entry/Exit threshold
if [ -f "$VIDEO_DIR/CAM 1.mp4" ]; then
    echo "Processing CAM 1 (Entry/Exit)..."
    python pipeline/detect.py --video "$VIDEO_DIR/CAM 1.mp4" --store-id "$STORE_ID" --camera-id "CAM_ENTRY_01" --layout-json "$LAYOUT_PATH" --output-jsonl "$OUTPUT_PATH"
else
    echo "CAM 1.mp4 not found. Processing via high-fidelity simulation..."
    python pipeline/detect.py --store-id "$STORE_ID" --camera-id "CAM_ENTRY_01" --layout-json "$LAYOUT_PATH" --output-jsonl "$OUTPUT_PATH" --simulation
fi

# Process Camera 2: Main floor zone coverage (Skincare, Haircare, Cosmetics)
if [ -f "$VIDEO_DIR/CAM 2.mp4" ]; then
    echo "Processing CAM 2 (Floor Coverage)..."
    python pipeline/detect.py --video "$VIDEO_DIR/CAM 2.mp4" --store-id "$STORE_ID" --camera-id "CAM_FLOOR_01" --layout-json "$LAYOUT_PATH" --output-jsonl "$OUTPUT_PATH"
else
    echo "CAM 2.mp4 not found. Processing via high-fidelity simulation..."
    python pipeline/detect.py --store-id "$STORE_ID" --camera-id "CAM_FLOOR_01" --layout-json "$LAYOUT_PATH" --output-jsonl "$OUTPUT_PATH" --simulation
fi

# Process Camera 3: Billing counter area
if [ -f "$VIDEO_DIR/CAM 3.mp4" ]; then
    echo "Processing CAM 3 (Billing Counter)..."
    python pipeline/detect.py --video "$VIDEO_DIR/CAM 3.mp4" --store-id "$STORE_ID" --camera-id "CAM_BILLING_01" --layout-json "$LAYOUT_PATH" --output-jsonl "$OUTPUT_PATH"
else
    echo "CAM 3.mp4 not found. Processing via high-fidelity simulation..."
    python pipeline/detect.py --store-id "$STORE_ID" --camera-id "CAM_BILLING_01" --layout-json "$LAYOUT_PATH" --output-jsonl "$OUTPUT_PATH" --simulation
fi

echo "================================================================="
echo "Pipeline execution completed successfully!"
echo "Events emitted to: $OUTPUT_PATH"
echo "================================================================="
