"""Database models for Cartelem telemetry system."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Float,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Session(Base):
    """Session model for telemetry data collection sessions."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    car_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    driver: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    track: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    started_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stopped_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    signals = relationship("Signal", back_populates="session", cascade="all, delete-orphan")
    frames = relationship("Frame", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, name='{self.name}', is_active={self.is_active})>"


class Signal(Base):
    """Signal model for individual telemetry data points."""

    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ts_mono_ns: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    value_num: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quality: Mapped[str] = mapped_column(String(20), default="good", nullable=False)

    # Relationships
    session = relationship("Session", back_populates="signals")

    def __repr__(self) -> str:
        return f"<Signal(id={self.id}, source='{self.source}', channel='{self.channel}')>"

    def to_dict(self) -> dict:
        """Convert signal to dictionary for export."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "source": self.source,
            "channel": self.channel,
            "ts_utc": self.ts_utc.isoformat() if self.ts_utc else None,
            "ts_mono_ns": self.ts_mono_ns,
            "value_num": self.value_num,
            "value_text": self.value_text,
            "unit": self.unit,
            "quality": self.quality,
        }


class Frame(Base):
    """Frame model for aggregated telemetry data snapshots."""

    __tablename__ = "frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sessions.id"), nullable=False, index=True
    )
    ts_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ts_mono_ns: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="frames")

    def __repr__(self) -> str:
        return f"<Frame(id={self.id}, session_id={self.session_id})>"


class DeviceProfile(Base):
    """Device profile model for saved hardware configurations."""

    __tablename__ = "device_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Device configurations
    gps_config: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    obd_config: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    meshtastic_config: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    custom_config: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<DeviceProfile(id={self.id}, name='{self.name}', is_default={self.is_default})>"

    def to_dict(self) -> dict:
        """Convert device profile to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_default": self.is_default,
            "created_utc": self.created_utc.isoformat(),
            "updated_utc": self.updated_utc.isoformat(),
            "gps_config": self.gps_config,
            "obd_config": self.obd_config,
            "meshtastic_config": self.meshtastic_config,
            "custom_config": self.custom_config,
        }


class DeviceSetup(Base):
    """Device setup model for tracking setup progress and status."""

    __tablename__ = "device_setup"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    profile_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("device_profiles.id"), nullable=True, index=True
    )
    setup_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'gps', 'obd', 'meshtastic'
    device_name: Mapped[str] = mapped_column(String(255), nullable=False)
    port_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    baud_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # 'pending', 'testing', 'success', 'failed'
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_results: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    created_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    profile = relationship("DeviceProfile")

    def __repr__(self) -> str:
        return f"<DeviceSetup(id={self.id}, type='{self.setup_type}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """Convert device setup to dictionary."""
        return {
            "id": self.id,
            "profile_id": self.profile_id,
            "setup_type": self.setup_type,
            "device_name": self.device_name,
            "port_path": self.port_path,
            "baud_rate": self.baud_rate,
            "status": self.status,
            "error_message": self.error_message,
            "test_results": self.test_results,
            "created_utc": self.created_utc.isoformat(),
            "completed_utc": self.completed_utc.isoformat() if self.completed_utc else None,
        }


# Create indexes for better query performance
Index("idx_signals_session_source", Signal.session_id, Signal.source)
Index("idx_signals_session_channel", Signal.session_id, Signal.channel)
Index("idx_signals_ts_utc", Signal.ts_utc)
Index("idx_frames_session_ts", Frame.session_id, Frame.ts_utc)
Index("idx_device_profiles_default", DeviceProfile.is_default)
Index("idx_device_setup_profile", DeviceSetup.profile_id)
Index("idx_device_setup_type", DeviceSetup.setup_type)
Index("idx_device_setup_status", DeviceSetup.status)