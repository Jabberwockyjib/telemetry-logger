"""Tests for database writer service."""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.db_writer import DatabaseWriter, TelemetryData


class TestTelemetryData:
    """Test TelemetryData class."""
    
    def test_telemetry_data_initialization(self) -> None:
        """Test TelemetryData initialization."""
        data = TelemetryData(
            session_id=1,
            source="gps",
            channel="latitude",
            value_num=37.7749,
            unit="degrees",
            quality="good",
        )
        
        assert data.session_id == 1
        assert data.source == "gps"
        assert data.channel == "latitude"
        assert data.value_num == 37.7749
        assert data.value_text is None
        assert data.unit == "degrees"
        assert data.quality == "good"
        assert isinstance(data.timestamp, datetime)
        assert data.ts_mono_ns > 0
    
    def test_telemetry_data_with_text_value(self) -> None:
        """Test TelemetryData with text value."""
        data = TelemetryData(
            session_id=1,
            source="obd",
            channel="status",
            value_text="connected",
            quality="good",
        )
        
        assert data.value_num is None
        assert data.value_text == "connected"
    
    def test_telemetry_data_to_signal_dict(self) -> None:
        """Test conversion to signal dictionary."""
        data = TelemetryData(
            session_id=1,
            source="gps",
            channel="latitude",
            value_num=37.7749,
            unit="degrees",
        )
        
        signal_dict = data.to_signal_dict()
        
        assert signal_dict["session_id"] == 1
        assert signal_dict["source"] == "gps"
        assert signal_dict["channel"] == "latitude"
        assert signal_dict["value_num"] == 37.7749
        assert signal_dict["value_text"] is None
        assert signal_dict["unit"] == "degrees"
        assert "ts_utc" in signal_dict
        assert "ts_mono_ns" in signal_dict


class TestDatabaseWriter:
    """Test DatabaseWriter class."""
    
    def test_database_writer_initialization(self) -> None:
        """Test DatabaseWriter initialization."""
        writer = DatabaseWriter(
            batch_size=50,
            batch_timeout=0.5,
            frame_interval=2.0,
            max_queue_size=5000,
        )
        
        assert writer.batch_size == 50
        assert writer.batch_timeout == 0.5
        assert writer.frame_interval == 2.0
        assert writer.max_queue_size == 5000
        assert writer.is_running is False
        assert len(writer.current_batch) == 0
        assert writer.signals_processed == 0
        assert writer.frames_created == 0
    
    def test_database_writer_default_initialization(self) -> None:
        """Test DatabaseWriter with default parameters."""
        writer = DatabaseWriter()
        
        assert writer.batch_size == 100
        assert writer.batch_timeout == 1.0
        assert writer.frame_interval == 1.0
        assert writer.max_queue_size == 10000
    
    async def test_start_and_stop(self) -> None:
        """Test starting and stopping database writer."""
        writer = DatabaseWriter()
        
        # Start writer
        await writer.start()
        assert writer.is_running is True
        assert writer.start_time is not None
        
        # Stop writer
        await writer.stop()
        assert writer.is_running is False
    
    async def test_queue_signal_success(self) -> None:
        """Test successful signal queuing."""
        writer = DatabaseWriter()
        
        data = TelemetryData(
            session_id=1,
            source="gps",
            channel="latitude",
            value_num=37.7749,
        )
        
        result = await writer.queue_signal(data)
        assert result is True
        assert writer.signal_queue.qsize() == 1
    
    async def test_queue_signal_queue_full(self) -> None:
        """Test signal queuing when queue is full."""
        writer = DatabaseWriter(max_queue_size=1)
        
        # Fill the queue
        data1 = TelemetryData(1, "gps", "lat", 37.7749)
        await writer.queue_signal(data1)
        
        # Try to add another signal
        data2 = TelemetryData(1, "gps", "lon", -122.4194)
        result = await writer.queue_signal(data2)
        
        assert result is False
        assert writer.queue_drops == 1
    
    async def test_queue_frame_success(self) -> None:
        """Test successful frame queuing."""
        writer = DatabaseWriter()
        
        frame_data = {"latitude": 37.7749, "longitude": -122.4194}
        result = await writer.queue_frame(1, frame_data)
        
        assert result is True
        assert writer.frame_queue.qsize() == 1
    
    async def test_queue_frame_queue_full(self) -> None:
        """Test frame queuing when queue is full."""
        writer = DatabaseWriter(max_queue_size=1)
        
        # Fill the queue
        frame_data1 = {"lat": 37.7749}
        await writer.queue_frame(1, frame_data1)
        
        # Try to add another frame
        frame_data2 = {"lon": -122.4194}
        result = await writer.queue_frame(1, frame_data2)
        
        assert result is False
        assert writer.queue_drops == 1
    
    async def test_batch_flushing_by_size(self) -> None:
        """Test batch flushing when batch size is reached."""
        writer = DatabaseWriter(batch_size=3, batch_timeout=10.0)
        await writer.start()
        
        # Add signals to reach batch size
        for i in range(3):
            data = TelemetryData(1, "gps", f"channel_{i}", value_num=float(i))
            await writer.queue_signal(data)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Check that batch was flushed
        assert len(writer.current_batch) == 0
        assert writer.signals_processed == 3
        assert writer.batches_written == 1
        
        await writer.stop()
    
    async def test_batch_flushing_by_timeout(self) -> None:
        """Test batch flushing by timeout."""
        writer = DatabaseWriter(batch_size=100, batch_timeout=0.1)
        await writer.start()
        
        # Add one signal
        data = TelemetryData(1, "gps", "latitude", 37.7749)
        await writer.queue_signal(data)
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Check that batch was flushed by timeout
        assert len(writer.current_batch) == 0
        assert writer.signals_processed == 1
        assert writer.batches_written == 1
        
        await writer.stop()
    
    async def test_frame_processing(self) -> None:
        """Test frame processing."""
        writer = DatabaseWriter()
        await writer.start()
        
        # Queue a frame
        frame_data = {"latitude": 37.7749, "longitude": -122.4194}
        await writer.queue_frame(1, frame_data)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Check that frame was processed
        assert writer.frames_created == 1
        
        await writer.stop()
    
    async def test_create_frame_snapshot(self) -> None:
        """Test frame snapshot creation."""
        writer = DatabaseWriter(frame_interval=0.1)
        await writer.start()
        
        # Create first frame snapshot
        current_data = {"latitude": 37.7749, "longitude": -122.4194}
        await writer.create_frame_snapshot(1, current_data)
        
        # Wait a bit
        await asyncio.sleep(0.05)
        
        # Create another frame snapshot (should be queued)
        current_data2 = {"latitude": 37.7750, "longitude": -122.4195}
        await writer.create_frame_snapshot(1, current_data2)
        
        # Wait for processing
        await asyncio.sleep(0.2)
        
        # Check that frames were created
        assert writer.frames_created >= 1
        
        await writer.stop()
    
    def test_get_statistics(self) -> None:
        """Test getting statistics."""
        writer = DatabaseWriter()
        
        stats = writer.get_statistics()
        
        assert "is_running" in stats
        assert "signals_processed" in stats
        assert "frames_created" in stats
        assert "batches_written" in stats
        assert "queue_drops" in stats
        assert "current_batch_size" in stats
        assert "signal_queue_size" in stats
        assert "frame_queue_size" in stats
        assert "runtime_seconds" in stats
        assert "signals_per_minute" in stats
    
    def test_get_performance_metrics(self) -> None:
        """Test getting performance metrics."""
        writer = DatabaseWriter()
        
        metrics = writer.get_performance_metrics()
        
        assert "signals_per_minute" in metrics
        assert "signals_processed" in metrics
        assert "batches_written" in metrics
        assert "average_batch_size" in metrics
        assert "queue_drops" in metrics
        assert "runtime_seconds" in metrics
        assert "throughput_achieved" in metrics


class TestDatabaseWriterPerformance:
    """Performance tests for DatabaseWriter."""
    
    async def test_high_throughput_benchmark(self) -> None:
        """Test high throughput performance benchmark."""
        writer = DatabaseWriter(
            batch_size=100,
            batch_timeout=0.1,
            max_queue_size=50000,
        )
        
        await writer.start()
        
        # Generate high volume of signals
        start_time = asyncio.get_event_loop().time()
        signal_count = 1000
        
        # Create and queue signals as fast as possible
        for i in range(signal_count):
            data = TelemetryData(
                session_id=1,
                source="benchmark",
                channel=f"signal_{i}",
                value_num=float(i),
            )
            await writer.queue_signal(data)
        
        # Wait for all signals to be processed
        while writer.signal_queue.qsize() > 0 or len(writer.current_batch) > 0:
            await asyncio.sleep(0.01)
        
        # Wait a bit more for final processing
        await asyncio.sleep(0.1)
        
        end_time = asyncio.get_event_loop().time()
        runtime = end_time - start_time
        
        # Get performance metrics
        metrics = writer.get_performance_metrics()
        
        # Verify performance
        assert writer.signals_processed == signal_count
        assert metrics["signals_per_minute"] > 0
        assert runtime > 0
        
        # Log performance for verification
        print(f"Processed {signal_count} signals in {runtime:.2f} seconds")
        print(f"Throughput: {metrics['signals_per_minute']:.0f} signals/minute")
        print(f"Average batch size: {metrics['average_batch_size']:.1f}")
        
        await writer.stop()
    
    async def test_5000_signals_per_minute_benchmark(self) -> None:
        """Test benchmark targeting ≥5k signals per minute."""
        writer = DatabaseWriter(
            batch_size=50,
            batch_timeout=0.05,
            max_queue_size=10000,
        )
        
        await writer.start()
        
        # Target: 5000 signals per minute = ~83 signals per second
        # Run for 10 seconds to get a good measurement
        target_duration = 10.0
        target_signals = int(5000 * target_duration / 60)  # ~833 signals
        
        start_time = asyncio.get_event_loop().time()
        
        # Generate signals at high rate
        for i in range(target_signals):
            data = TelemetryData(
                session_id=1,
                source="benchmark",
                channel=f"signal_{i}",
                value_num=float(i),
            )
            await writer.queue_signal(data)
            
            # Small delay to simulate real-world rate
            if i % 100 == 0:
                await asyncio.sleep(0.001)
        
        # Wait for all signals to be processed
        while writer.signal_queue.qsize() > 0 or len(writer.current_batch) > 0:
            await asyncio.sleep(0.01)
        
        # Wait for final processing
        await asyncio.sleep(0.2)
        
        end_time = asyncio.get_event_loop().time()
        actual_duration = end_time - start_time
        
        # Get performance metrics
        metrics = writer.get_performance_metrics()
        
        # Verify performance target
        assert writer.signals_processed == target_signals
        assert metrics["signals_per_minute"] >= 5000, f"Expected ≥5000 signals/min, got {metrics['signals_per_minute']:.0f}"
        assert metrics["throughput_achieved"] is True
        
        # Log performance for verification
        print(f"Benchmark Results:")
        print(f"  Target: 5000 signals/minute")
        print(f"  Actual: {metrics['signals_per_minute']:.0f} signals/minute")
        print(f"  Processed: {writer.signals_processed} signals")
        print(f"  Duration: {actual_duration:.2f} seconds")
        print(f"  Batches: {writer.batches_written}")
        print(f"  Average batch size: {metrics['average_batch_size']:.1f}")
        print(f"  Queue drops: {writer.queue_drops}")
        
        await writer.stop()
    
    async def test_concurrent_signal_and_frame_processing(self) -> None:
        """Test concurrent processing of signals and frames."""
        writer = DatabaseWriter(
            batch_size=20,
            batch_timeout=0.1,
            frame_interval=0.05,
        )
        
        await writer.start()
        
        # Generate both signals and frames concurrently
        signal_count = 500
        frame_count = 50
        
        # Create signals
        for i in range(signal_count):
            data = TelemetryData(
                session_id=1,
                source="concurrent_test",
                channel=f"signal_{i}",
                value_num=float(i),
            )
            await writer.queue_signal(data)
        
        # Create frames
        for i in range(frame_count):
            frame_data = {
                "signal_count": i,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await writer.queue_frame(1, frame_data)
        
        # Wait for processing
        while writer.signal_queue.qsize() > 0 or writer.frame_queue.qsize() > 0 or len(writer.current_batch) > 0:
            await asyncio.sleep(0.01)
        
        # Wait for final processing
        await asyncio.sleep(0.2)
        
        # Verify results
        assert writer.signals_processed == signal_count
        assert writer.frames_created == frame_count
        
        # Log results
        print(f"Concurrent processing results:")
        print(f"  Signals processed: {writer.signals_processed}")
        print(f"  Frames created: {writer.frames_created}")
        print(f"  Batches written: {writer.batches_written}")
        
        await writer.stop()


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
