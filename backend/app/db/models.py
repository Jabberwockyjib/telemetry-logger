"""SQLAlchemy models for telemetry data."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Session(Base):
    """Session model for telemetry data collection sessions.
    
    Attributes:
        id: Primary key.
        name: Session name.
        car_id: Vehicle identifier.
        driver: Driver name.
        track: Track name.
        created_utc: Session creation timestamp (UTC).
        notes: Optional session notes.
        signals: Related signal records.
        frames: Related frame records.
    """
    
    __tablename__ = "sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    car_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    driver: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    track: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    signals: Mapped[list["Signal"]] = relationship("Signal", back_populates="session")
    frames: Mapped[list["Frame"]] = relationship("Frame", back_populates="session")
    
    # Indexes
    __table_args__ = (
        Index("ix_sessions_created_utc", "created_utc"),
        Index("ix_sessions_car_id", "car_id"),
    )


class Signal(Base):
    """Signal model for individual telemetry data points.
    
    Attributes:
        id: Primary key.
        session_id: Foreign key to session.
        source: Data source (e.g., 'obd', 'gps').
        channel: Signal channel/parameter name.
        ts_utc: Timestamp in UTC.
        ts_mono_ns: Monotonic timestamp in nanoseconds.
        value_num: Numeric value.
        value_text: Text value.
        unit: Unit of measurement.
        quality: Data quality indicator.
        session: Related session.
    """
    
    __tablename__ = "signals"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    channel: Mapped[str] = mapped_column(String(100), nullable=False)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ts_mono_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    value_num: Mapped[Optional[float]] = mapped_column(nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="signals")
    
    # Indexes
    __table_args__ = (
        Index("ix_signals_session_id", "session_id"),
        Index("ix_signals_ts_utc", "ts_utc"),
        Index("ix_signals_ts_mono_ns", "ts_mono_ns"),
        Index("ix_signals_source_channel", "source", "channel"),
        Index("ix_signals_session_source", "session_id", "source"),
    )


class Frame(Base):
    """Frame model for aggregated telemetry data snapshots.
    
    Attributes:
        id: Primary key.
        session_id: Foreign key to session.
        ts_utc: Timestamp in UTC.
        ts_mono_ns: Monotonic timestamp in nanoseconds.
        payload_json: JSON payload with frame data.
        session: Related session.
    """
    
    __tablename__ = "frames"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("sessions.id"), nullable=False)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ts_mono_ns: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="frames")
    
    # Indexes
    __table_args__ = (
        Index("ix_frames_session_id", "session_id"),
        Index("ix_frames_ts_utc", "ts_utc"),
        Index("ix_frames_ts_mono_ns", "ts_mono_ns"),
    )
