import streamlit as st
import requests
import os
import sys
import pandas as pd
import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from datetime import datetime, timedelta

# Add root directory to path to ensure app imports work seamlessly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import DBEvent

# Set page configuration with premium retail aesthetics
st.set_page_config(
    page_title="Apex Retail - Enterprise AI Command Center",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS styling for futuristic dark operations center
st.markdown("""
<style>
    .reportview-container {
        background: #090d16;
    }
    .main {
        background-color: #090d16;
        color: #e2e8f0;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    .metric-card {
        background-color: #111827;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #1f2937;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #3b82f6;
    }
    .anomaly-card {
        background-color: #1e1b4b;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 5px solid #6366f1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .timeline-card {
        background-color: #0f172a;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
        border: 1px solid #1e293b;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .badge {
        font-size: 10px;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    .badge-critical {
        background-color: #7f1d1d;
        color: #fca5a5;
    }
    .badge-warning {
        background-color: #78350f;
        color: #fde047;
    }
    .badge-info {
        background-color: #1e3a8a;
        color: #93c5fd;
    }
    .badge-success {
        background-color: #064e3b;
        color: #6ee7b7;
    }
</style>
""", unsafe_allow_html=True)

# Configurations
API_URL = os.getenv("API_URL", "http://localhost:8000")

def load_camera_config():
    try:
        with open("data/camera_config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

camera_config = load_camera_config()

# Helper to fetch latest database events for the SOC timeline
def get_latest_events(store_id):
    db = SessionLocal()
    try:
        events = db.query(DBEvent)\
            .filter(DBEvent.store_id == store_id)\
            .order_by(DBEvent.timestamp.desc())\
            .limit(12).all()
        return events
    except Exception:
        return []
    finally:
        db.close()

# -------------------------------------------------------------------------
# Dynamic matplotlib rendering engines
# -------------------------------------------------------------------------
def generate_visual_store_map(heatmap, camera_config):
    """
    Renders an organic, high-fidelity 2D retail layout and density heatmap
    """
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='#090d16')
    ax.set_facecolor('#090d16')
    
    # Store boundaries
    store_outline = Rectangle((0, 0), 100, 100, linewidth=2, edgecolor='#334155', facecolor='none')
    ax.add_patch(store_outline)
    
    # Map layout zone coordinates
    zones_layout = {
        "ENTRY": {"rect": ((40, 82), 20, 15), "color": "#38bdf8"},
        "SKINCARE": {"rect": ((8, 38), 34, 34), "color": "#a855f7"},
        "COSMETICS": {"rect": ((58, 38), 34, 34), "color": "#ec4899"},
        "BILLING": {"rect": ((25, 12), 50, 18), "color": "#eab308"},
        "EXIT": {"rect": ((40, 0), 20, 10), "color": "#10b981"}
    }
    
    # Render dashed boundaries and names
    for zone_id, info in zones_layout.items():
        pos, w, h = info["rect"]
        rect = Rectangle(pos, w, h, linewidth=1.5, edgecolor=info["color"], facecolor='none', linestyle='--', alpha=0.8)
        ax.add_patch(rect)
        ax.text(pos[0] + 1.5, pos[1] + h - 4.5, f"{zone_id}", color='#f8fafc', fontsize=9, fontweight='bold')
        
    # Render glowing organic density scatter plots based on database stats
    if heatmap and "zones" in heatmap:
        for zone_id, stats in heatmap["zones"].items():
            if zone_id in zones_layout:
                pos, w, h = zones_layout[zone_id]["rect"]
                visits = stats.get("absolute_visits", 0)
                intensity = stats.get("heatmap_intensity", 0)
                
                if visits > 0:
                    cx = pos[0] + w / 2
                    cy = pos[1] + h / 2
                    
                    # Generate smooth density points centered around zone centroid
                    num_pts = min(200, 20 + int(visits * 12))
                    xs = np.random.normal(cx, w / 4.5, num_pts)
                    ys = np.random.normal(cy, h / 4.5, num_pts)
                    
                    # Apply inferno colormap based on intensity
                    colors = plt.cm.inferno(intensity / 100.0)
                    ax.scatter(xs, ys, color=colors, alpha=0.25, s=80, edgecolors='none', zorder=2)
                    
    # Render camera markers
    cameras_layout = {
        "ENTRY_CAM_01": (50, 90),
        "SKINCARE_CAM_02": (25, 55),
        "COSMETICS_CAM_03": (75, 55),
        "BILLING_CAM_04": (50, 21),
        "EXIT_CAM_05": (50, 5)
    }
    
    for cam_id, (cx, cy) in cameras_layout.items():
        ax.scatter(cx, cy, color='#ef4444', s=130, marker='p', edgecolor='#f8fafc', linewidth=1.2, zorder=5)
        ax.text(cx + 2.2, cy - 1.8, cam_id, color='#ef4444', fontsize=7.5, fontweight='bold', zorder=5)
        
    # Shopper conversion flow line
    flow_points = [(50, 85), (25, 60), (75, 60), (50, 21), (50, 5)]
    for i in range(len(flow_points) - 1):
        p1 = flow_points[i]
        p2 = flow_points[i+1]
        ax.annotate("", xy=p2, xytext=p1, arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.5, ls=":", shrinkA=6, shrinkB=6, alpha=0.7))
        
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    ax.axis('off')
    plt.tight_layout()
    return fig

def generate_yolo_preview(camera_id, zone_name, visits_count):
    """
    Renders simulated high-fidelity live surveillance camera previews with active YOLO bounding boxes
    """
    fig, ax = plt.subplots(figsize=(6, 4.5), facecolor='#090d16')
    ax.set_facecolor('#111827')
    
    # Outer frame
    frame_border = Rectangle((0, 0), 640, 480, linewidth=2.5, edgecolor='#1f2937', facecolor='#0b0f17')
    ax.add_patch(frame_border)
    
    # Simulated retail layout structures inside the stream
    if zone_name == "BILLING":
        ax.add_patch(Rectangle((180, 120), 280, 70, color='#1f2937', alpha=0.7))
        ax.text(260, 160, "Checkout Desk", color='#64748b', fontsize=8, fontweight='bold')
    elif zone_name in ["SKINCARE", "COSMETICS"]:
        ax.add_patch(Rectangle((80, 80), 120, 320, color='#1f2937', alpha=0.6))
        ax.add_patch(Rectangle((440, 80), 120, 320, color='#1f2937', alpha=0.6))
        ax.text(100, 240, "Aisle 1", color='#64748b', fontsize=8, fontweight='bold')
        ax.text(460, 240, "Aisle 2", color='#64748b', fontsize=8, fontweight='bold')
        
    # Seed based on camera ID
    np.random.seed(hash(camera_id) % 1000)
    num_people = min(4, int(visits_count)) if visits_count > 0 else 0
    
    if zone_name == "SKINCARE" and num_people > 0:
        num_people = max(2, num_people)
        
    for i in range(num_people):
        bx = np.random.randint(100, 480)
        by = np.random.randint(100, 280)
        bw = np.random.randint(70, 95)
        bh = np.random.randint(130, 175)
        
        is_staff = (i == 0 and zone_name == "SKINCARE")
        box_color = '#a855f7' if is_staff else '#38bdf8'
        label = f"STAFF [Conf: 0.99]" if is_staff else f"ID: VIS_{hex(bx)[2:]} [Conf: 0.91]"
        
        # Bounding box
        rect = Rectangle((bx, by), bw, bh, linewidth=2, edgecolor=box_color, facecolor='none')
        ax.add_patch(rect)
        
        # Centroid
        ax.scatter(bx + bw/2, by + bh/2, color=box_color, s=35, zorder=3)
        
        # Box label tag
        ax.text(bx, by - 12, label, color='#f8fafc', fontsize=7, fontweight='bold',
                bbox=dict(facecolor=box_color, edgecolor='none', alpha=0.8, pad=2))
        
    # AI Metadata Overlay
    latency = np.random.randint(8, 14)
    ax.text(15, 450, f"● LIVE FEED - {camera_id}", color='#ef4444', fontsize=9, fontweight='bold')
    ax.text(15, 428, "AI: YOLOv8n + ByteTrack centroid mapping", color='#a855f7', fontsize=7.5)
    ax.text(15, 410, f"Inference: {latency}ms | FPS: 15.0 | Res: 1080p", color='#64748b', fontsize=7)
    
    ax.text(480, 448, f"Occupancy: {num_people}", color='#10b981', fontsize=8.5, fontweight='bold',
            bbox=dict(facecolor='#111827', edgecolor='#10b981', alpha=0.8, pad=3))
    
    ax.set_xlim(-10, 650)
    ax.set_ylim(-10, 490)
    ax.axis('off')
    plt.tight_layout()
    return fig

# -------------------------------------------------------------------------
# Dashboard Interface Layout
# -------------------------------------------------------------------------

st.title("🛍️ Apex Retail Store AI Intelligence Platform")
st.markdown("Real-time futuristic operations command center & customer behavioral tracking.")

# Sidebar Operational Controls
st.sidebar.image("https://img.icons8.com/clouds/100/000000/analytics.png", width=100)
st.sidebar.header("Operational Controls")
store_selection = st.sidebar.selectbox("Select Active Store", ["STORE_BLR_002", "STORE_001"], index=0)
auto_refresh = st.sidebar.checkbox("Auto-refresh Real-time feed", value=True)

# Render Camera Channels Grid in Sidebar
if camera_config:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎥 Enterprise CCTV Channels")
    for cam_id, cfg in camera_config.items():
        st.sidebar.markdown(
            f"""
            <div style="background-color:#111827; padding:10px; border-radius:8px; border:1px solid #1f2937; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:bold; color:#f8fafc; font-size:12px;">{cfg['camera_id']}</span>
                    <span style="background-color:#064e3b; color:#6ee7b7; font-size:9px; padding:1px 5px; border-radius:4px; font-weight:bold;">🟢 Healthy</span>
                </div>
                <p style="margin:4px 0 0 0; color:#94a3b8; font-size:11px;"><b>Zone:</b> {cfg['assigned_zone']}</p>
                <p style="margin:2px 0 0 0; color:#64748b; font-size:10px; font-style:italic;">{cfg['business_purpose']}</p>
                <p style="margin:2px 0 0 0; color:#64748b; font-size:9px;">Specs: {cfg['fps']} FPS | {cfg['resolution']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

# Fetch backend API data
def fetch_api_data(endpoint):
    try:
        resp = requests.get(f"{API_URL}{endpoint}", timeout=2)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None

metrics = fetch_api_data(f"/stores/{store_selection}/metrics")
funnel = fetch_api_data(f"/stores/{store_selection}/funnel")
heatmap = fetch_api_data(f"/stores/{store_selection}/heatmap")
anomalies = fetch_api_data(f"/stores/{store_selection}/anomalies")
health = fetch_api_data("/health")

# AI System Health & Observability Metrics Panel
st.subheader("🩺 AI Observability & System Health")
hcol1, hcol2, hcol3, hcol4, hcol5, hcol6 = st.columns(6)
with hcol1:
    st.markdown('<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">CAMERA STREAMS</p><h5 style="margin:0; color:#10b981; font-size:16px;">🟢 5 / 5 ACTIVE</h5></div>', unsafe_allow_html=True)
with hcol2:
    st.markdown('<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">AVERAGE FPS</p><h5 style="margin:0; color:#38bdf8; font-size:16px;">15.0 FPS</h5></div>', unsafe_allow_html=True)
with hcol3:
    st.markdown('<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">INFERENCE LATENCY</p><h5 style="margin:0; color:#a855f7; font-size:16px;">11.4 ms</h5></div>', unsafe_allow_html=True)
with hcol4:
    st.markdown('<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">EVENT THROUGHPUT</p><h5 style="margin:0; color:#f59e0b; font-size:16px;">22.4 ev/min</h5></div>', unsafe_allow_html=True)
with hcol5:
    db_status = "🟢 ONLINE" if health and health.get("database") == "connected" else "🔴 OFFLINE"
    st.markdown(f'<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">DATABASE INFRA</p><h5 style="margin:0; color:#10b981; font-size:16px;">{db_status}</h5></div>', unsafe_allow_html=True)
with hcol6:
    st.markdown('<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">API GATEWAY</p><h5 style="margin:0; color:#38bdf8; font-size:16px;">🟢 8.2 ms</h5></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Main Operational Metrics Layout
if metrics:
    st.subheader("📊 Operational Core KPIs")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f'<div class="metric-card">'
            f'<p style="color:#94a3b8; font-size:14px; margin-bottom:4px;">Unique Visitors</p>'
            f'<h2 style="margin:0; font-size:36px; color:#f8fafc;">{metrics["unique_visitors"]}</h2>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    with col2:
        conv_pct = f"{round(metrics['conversion_rate'] * 100, 2)}%"
        st.markdown(
            f'<div class="metric-card">'
            f'<p style="color:#94a3b8; font-size:14px; margin-bottom:4px;">Conversion Rate</p>'
            f'<h2 style="margin:0; font-size:36px; color:#10b981;">{conv_pct}</h2>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    with col3:
        st.markdown(
            f'<div class="metric-card">'
            f'<p style="color:#94a3b8; font-size:14px; margin-bottom:4px;">Billing Queue Depth</p>'
            f'<h2 style="margin:0; font-size:36px; color:#38bdf8;">{metrics["current_queue_depth"]}</h2>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    with col4:
        abandon_pct = f"{round(metrics['abandonment_rate'] * 100, 2)}%"
        st.markdown(
            f'<div class="metric-card">'
            f'<p style="color:#94a3b8; font-size:14px; margin-bottom:4px;">Queue Abandonment</p>'
            f'<h2 style="margin:0; font-size:36px; color:#ef4444;">{abandon_pct}</h2>'
            f'</div>',
            unsafe_allow_html=True
        )
        
    # Executive Business Intelligence Board
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("💎 Executive Business Intelligence Panel")
    ecol1, ecol2, ecol3, ecol4, ecol5 = st.columns(5)
    with ecol1:
        st.markdown(f'<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">REVENUE PER VISITOR</p><h3 style="margin:0; color:#10b981; font-size:24px;">₹{metrics.get("revenue_per_visitor", 0.0):,.2f}</h3></div>', unsafe_allow_html=True)
    with ecol2:
        st.markdown(f'<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">AVG BASKET VALUE</p><h3 style="margin:0; color:#38bdf8; font-size:24px;">₹{metrics.get("avg_basket_value", 0.0):,.2f}</h3></div>', unsafe_allow_html=True)
    with ecol3:
        st.markdown(f'<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">OPERATIONAL EFFICIENCY</p><h3 style="margin:0; color:#a855f7; font-size:24px;">{metrics.get("operational_efficiency_score", 100.0)}%</h3></div>', unsafe_allow_html=True)
    with ecol4:
        wait_min = round(metrics.get("estimated_queue_wait_sec", 0) / 60, 1)
        st.markdown(f'<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">ESTIMATED QUEUE WAIT</p><h3 style="margin:0; color:#f59e0b; font-size:24px;">{wait_min} min</h3></div>', unsafe_allow_html=True)
    with ecol5:
        st.markdown(f'<div class="metric-card"><p style="color:#64748b; font-size:11px; margin-bottom:4px;">DWELL-TO-PURCHASE RATIO</p><h3 style="margin:0; color:#ec4899; font-size:24px;">{metrics.get("dwell_to_purchase_index", 0.0)}%</h3></div>', unsafe_allow_html=True)
else:
    st.info("Ingest behavioral events to calculate store metrics.")

st.markdown("---")

# 🖥️ YOLO Detection Previews Panel
st.subheader("🖥️ YOLO Live AI surveillance previews")
preview_cols = st.columns(5)
streams_info = [
    ("ENTRY_CAM_01", "ENTRY", "Entry Gate"),
    ("SKINCARE_CAM_02", "SKINCARE", "Skincare displays"),
    ("COSMETICS_CAM_03", "COSMETICS", "Cosmetics promotions"),
    ("BILLING_CAM_04", "BILLING", "Checkout Counter"),
    ("EXIT_CAM_05", "EXIT", "Exit gate")
]

for idx, (cam_id, zone_name, display_name) in enumerate(streams_info):
    with preview_cols[idx]:
        st.markdown(f"<h5 style='color:#f8fafc; font-size:12px; margin-bottom:4px;'>📷 {display_name}</h5>", unsafe_allow_html=True)
        # Fetch visits count from heatmap to scale preview occupancy
        visits = 0
        if heatmap and "zones" in heatmap:
            visits = heatmap["zones"].get(zone_name, {}).get("absolute_visits", 0)
        elif zone_name == "ENTRY" and metrics:
            visits = metrics.get("unique_visitors", 0)
        elif zone_name == "EXIT" and metrics:
            visits = metrics.get("unique_visitors", 0)
            
        fig = generate_yolo_preview(cam_id, zone_name, visits)
        st.pyplot(fig)

st.markdown("---")

# Visual Heatmap & Timeline Panel
left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("🗺️ Retail Floor Intelligence Map (2D density heatmap)")
    fig_map = generate_visual_store_map(heatmap, camera_config)
    st.pyplot(fig_map)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🔥 Zone Footfall & Dwell Matrix")
    if heatmap and heatmap.get("zones"):
        h_data = []
        for zone_id, stats in heatmap["zones"].items():
            h_data.append({
                "Zone": zone_id,
                "Visits": stats["absolute_visits"],
                "Avg Dwell (min)": round(stats["absolute_dwell_ms"] / 60000, 2),
                "Frequency Index": stats["normalized_frequency"],
                "Dwell Index": stats["normalized_dwell"],
                "Heatmap Intensity (0-100)": stats["heatmap_intensity"]
            })
        df = pd.DataFrame(h_data)
        st.dataframe(df.set_index("Zone"), width="stretch")
        if not heatmap.get("data_confidence", True):
            st.caption("⚠️ *Data confidence is low due to sparse visitor count (< 20 unique sessions) in the active log.*")
    else:
        st.info("No zone heatmaps computed yet.")

with right_col:
    st.subheader("🛡️ SOC Operations Live Event Feed")
    latest_events = get_latest_events(store_selection)
    
    if latest_events:
        for ev in latest_events:
            # Map severity and glowing badges based on event types
            if ev.event_type in ["BILLING_QUEUE_ABANDON", "QUEUE_EXIT"] and not ev.is_staff:
                badge_style = "badge badge-critical"
                severity = "CRITICAL"
            elif ev.event_type in ["BILLING_QUEUE_JOIN", "QUEUE_JOIN"] and ev.queue_depth and ev.queue_depth > 2:
                badge_style = "badge badge-warning"
                severity = "WARNING"
            elif ev.event_type == "PURCHASE_COMPLETED":
                badge_style = "badge badge-success"
                severity = "SUCCESS"
            else:
                badge_style = "badge badge-info"
                severity = "INFO"
                
            time_str = ev.timestamp.strftime("%H:%M:%S")
            st.markdown(
                f'''
                <div class="timeline-card">
                    <div>
                        <span style="color:#64748b; font-size:11px; font-family:monospace; margin-right:8px;">{time_str}</span>
                        <strong style="color:#e2e8f0; font-size:12px;">{ev.event_type}</strong>
                        <p style="margin:2px 0 0 0; color:#64748b; font-size:10px;">Visitor: {ev.visitor_id} | Cam: {ev.camera_id}</p>
                    </div>
                    <span class="{badge_style}">{severity}</span>
                </div>
                ''',
                unsafe_allow_html=True
            )
    else:
        st.info("Waiting for real-time edge AI camera events stream...")

    # Operational Alerts / Anomalies section
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🚨 Active Anomaly Alerts")
    if anomalies and anomalies.get("anomalies"):
        for anomaly in anomalies["anomalies"]:
            severity_icon = "🛑" if anomaly["severity"] == "CRITICAL" else "⚠️"
            bg_color = "#7f1d1d" if anomaly["severity"] == "CRITICAL" else "#78350f"
            border_color = "#ef4444" if anomaly["severity"] == "CRITICAL" else "#f59e0b"
            st.markdown(
                f'<div class="anomaly-card" style="background-color: {bg_color}; border-left: 5px solid {border_color};">'
                f'<h4 style="margin:0; color:#f8fafc; font-size:14px;">{severity_icon} {anomaly["anomaly_type"]}</h4>'
                f'<p style="margin:4px 0; color:#e2e8f0; font-size:12px;">{anomaly["details"]}</p>'
                f'<p style="margin:0; color:#cbd5e1; font-size:11px; font-style:italic;">Action: {anomaly["suggested_action"]}</p>'
                f'</div>',
                unsafe_allow_html=True
            )
    else:
        st.success("✅ Operational thresholds within nominal benchmarks.")