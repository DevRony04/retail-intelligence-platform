from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Index, JSON, UniqueConstraint
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, UUID4, validator
from typing import Optional, Dict, Any
from datetime import datetime
from app.database import Base

# ==========================================
# 1. DATABASE MODELS (SQLAlchemy)
# ==========================================

class DBEvent(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True)
    store_id = Column(String(50), nullable=False, index=True)
    camera_id = Column(String(50), nullable=False)
    visitor_id = Column(String(50), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    zone_id = Column(String(50), nullable=True, index=True)
    dwell_ms = Column(Integer, default=0)
    is_staff = Column(Boolean, default=False, index=True)
    confidence = Column(Float, default=1.0)
    
    # Flattened metadata fields for high-performance SQL indexing
    queue_depth = Column(Integer, nullable=True)
    sku_zone = Column(String(100), nullable=True)
    session_seq = Column(Integer, default=1)
    
    # Audit timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # High-performance compound indexes for real-time analytics queries
    __table_args__ = (
        Index("idx_store_time_type", "store_id", "timestamp", "event_type"),
        Index("idx_store_visitor", "store_id", "visitor_id"),
        UniqueConstraint("event_id", name="uq_event_id"),
    )

# ==========================================
# 2. SCHEMA MODELS (Pydantic Validation)
# ==========================================

class EventMetadataSchema(BaseModel):
    queue_depth: Optional[int] = Field(None, description="Current depth of the billing queue")
    sku_zone: Optional[str] = Field(None, description="SKU zone category label")
    session_seq: int = Field(1, description="Sequential index of this event in the visitor session")

class EventSchema(BaseModel):
    event_id: str = Field(..., description="Globally unique UUIDv4")
    store_id: str = Field(..., description="Store Identifier")
    camera_id: str = Field(..., description="Camera ID producing the event")
    visitor_id: str = Field(..., description="Session-aware Re-ID visitor token")
    event_type: str = Field(..., description="Behavioral event type")
    timestamp: datetime = Field(..., description="ISO-8601 UTC timestamp")
    zone_id: Optional[str] = Field(None, description="Named zone of interaction")
    dwell_ms: int = Field(0, description="Dwell duration in milliseconds")
    is_staff: bool = Field(False, description="Flag indicating store employee")
    confidence: float = Field(..., description="Detection confidence score [0.0 - 1.0]")
    metadata: EventMetadataSchema = Field(..., description="Custom event metadata fields")

    @validator("event_type")
    def validate_event_type(cls, v):
        allowed = {
            "ENTRY", "EXIT", "ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL", 
            "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON", "REENTRY",
            "QUEUE_JOIN", "QUEUE_EXIT", "PURCHASE_COMPLETED", "SHELF_INTERACTION", "PROMOTION_INTERACTION"
        }
        if v not in allowed:
            raise ValueError(f"event_type must be one of {allowed}")
        return v

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat().replace("+00:00", "Z")
        }
        schema_extra = {
            "example": {
                "event_id": "c8a2f1a3-ef11-4828-97fb-fa2bfa2b3a19",
                "store_id": "STORE_BLR_002",
                "camera_id": "CAM_ENTRY_01",
                "visitor_id": "VIS_c8a2f1",
                "event_type": "ZONE_DWELL",
                "timestamp": "2026-03-03T14:22:10Z",
                "zone_id": "SKINCARE",
                "dwell_ms": 8400,
                "is_staff": False,
                "confidence": 0.91,
                "metadata": {
                    "queue_depth": None,
                    "sku_zone": "MOISTURISER",
                    "session_seq": 5
                }
            }
        }
