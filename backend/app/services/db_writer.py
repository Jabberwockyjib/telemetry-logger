"""Database writer service for batching telemetry data inserts."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.crud import frame_crud, signal_crud
from ..db.models import Frame, Signal

logger = logging.getLogger(__name__)


class TelemetryData:
    """Container for telemetry data from services."""
    
    def __init__(
        self,
        session_id: int,
        source: str,
        channel: str,
        value_num: Optional[float] = None,
        value_text: Optional[str] = None,
        unit: Optional[str] = None,
        quality: str = "good",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Initialize telemetry data.
        
        Args:
            session_id: Session ID.
            source: Data source (e.g., 'gps', 'obd', 'meshtastic').
            channel: Channel name (e.g., 'speed_kph', 'latitude').
            value_num: Numeric value.
            value_text: Text value.
            unit: Unit of measurement.
            quality: Data quality indicator.
            timestamp: Timestamp (defaults to now).
        """
        self.session_id = session_id
        self.source = source
        self.channel = channel
        self.value_num = value_num
        self.value_text = value_text
        self.unit = unit
        self.quality = quality
        self.timestamp = timestamp or datetime.now(timezone.utc)
        try:
            self.ts_mono_ns = int(asyncio.get_event_loop().time() * 1_000_000_000)
        except RuntimeError:
            # No event loop available, use timestamp-based monotonic time
            self.ts_mono_ns = int(self.timestamp.timestamp() * 1_000_000_000)
    
    def to_signal_dict(self) -> Dict:
        """Convert to signal dictionary for database insertion."""
        return {
            "session_id": self.session_id,
            "source": self.source,
            "channel": self.channel,
            "ts_utc": self.timestamp,
            "ts_mono_ns": self.ts_mono_ns,
            "value_num": self.value_num,
            "value_text": self.value_text,
            "unit": self.unit,
        }


class DatabaseWriter:
    """Database writer service for batching telemetry data inserts.
    
    This service consumes telemetry data from queues and efficiently batches
    inserts into the database, optionally creating frame snapshots.
    """
    
    def __init__(
        self,
        batch_size: int = 100,
        batch_timeout: float = 1.0,
        frame_interval: float = 1.0,
        max_queue_size: int = 10000,
    ) -> None:
        """Initialize database writer.
        
        Args:
            batch_size: Number of signals to batch before inserting.
            batch_timeout: Maximum time to wait before flushing batch.
            frame_interval: Interval for creating frame snapshots (seconds).
            max_queue_size: Maximum queue size before dropping data.
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.frame_interval = frame_interval
        self.max_queue_size = max_queue_size
        
        # Data queues
        self.signal_queue: asyncio.Queue[TelemetryData] = asyncio.Queue(maxsize=max_queue_size)
        self.frame_queue: asyncio.Queue[Dict] = asyncio.Queue(maxsize=max_queue_size)
        
        # State
        self.is_running = False
        self.current_batch: List[TelemetryData] = []
        self.last_frame_time: Dict[int, float] = {}  # session_id -> timestamp
        
        # Statistics
        self.signals_processed = 0
        self.frames_created = 0
        self.batches_written = 0
        self.queue_drops = 0
        self.start_time: Optional[datetime] = None
    
    async def start(self) -> None:
        """Start the database writer service."""
        self.is_running = True
        self.start_time = datetime.now(timezone.utc)
        
        logger.info("Starting database writer service")
        
        # Start the main processing loop
        asyncio.create_task(self._processing_loop())
    
    async def stop(self) -> None:
        """Stop the database writer service."""
        self.is_running = False
        
        # Flush any remaining data
        await self._flush_batch()
        
        logger.info(f"Database writer stopped. Stats: {self.signals_processed} signals, {self.frames_created} frames, {self.batches_written} batches")
    
    async def queue_signal(self, data: TelemetryData) -> bool:
        """Queue a signal for database insertion.
        
        Args:
            data: Telemetry data to queue.
            
        Returns:
            bool: True if queued successfully, False if queue is full.
        """
        try:
            self.signal_queue.put_nowait(data)
            return True
        except asyncio.QueueFull:
            self.queue_drops += 1
            logger.warning(f"Signal queue full, dropping data. Total drops: {self.queue_drops}")
            return False
    
    async def queue_frame(self, session_id: int, frame_data: Dict) -> bool:
        """Queue a frame snapshot for database insertion.
        
        Args:
            session_id: Session ID.
            frame_data: Frame data to queue.
            
        Returns:
            bool: True if queued successfully, False if queue is full.
        """
        try:
            frame_entry = {
                "session_id": session_id,
                "data": frame_data,
                "timestamp": datetime.now(timezone.utc),
            }
            self.frame_queue.put_nowait(frame_entry)
            return True
        except asyncio.QueueFull:
            self.queue_drops += 1
            logger.warning(f"Frame queue full, dropping data. Total drops: {self.queue_drops}")
            return False
    
    async def _processing_loop(self) -> None:
        """Main processing loop for database writer."""
        while self.is_running:
            try:
                # Process signals in batches for better performance
                await self._process_signals_batch()
                
                # Process frames
                await self._process_frames()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.001)  # Reduced delay for better performance
                
            except Exception as e:
                logger.error(f"Error in database writer processing loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _process_signals(self) -> None:
        """Process signal queue and batch inserts."""
        try:
            # Try to get a signal with timeout
            signal = await asyncio.wait_for(
                self.signal_queue.get(), 
                timeout=0.1
            )
            
            self.current_batch.append(signal)
            
            # Check if we should flush the batch
            if len(self.current_batch) >= self.batch_size:
                await self._flush_batch()
                
        except asyncio.TimeoutError:
            # No signals available, check if we should flush due to timeout
            if self.current_batch and self._should_flush_timeout():
                await self._flush_batch()
        except Exception as e:
            logger.error(f"Error processing signals: {e}")
    
    async def _process_signals_batch(self) -> None:
        """Process multiple signals in a batch for better performance."""
        try:
            # Try to get multiple signals at once
            signals = []
            for _ in range(min(self.batch_size, 10)):  # Process up to 10 signals at once
                try:
                    signal = await asyncio.wait_for(
                        self.signal_queue.get(),
                        timeout=0.01
                    )
                    signals.append(signal)
                except asyncio.TimeoutError:
                    break
            
            if signals:
                self.current_batch.extend(signals)
                
                # Check if we should flush the batch
                if len(self.current_batch) >= self.batch_size:
                    await self._flush_batch()
            elif self.current_batch and self._should_flush_timeout():
                await self._flush_batch()
                
        except Exception as e:
            logger.error(f"Error processing signal batch: {e}")
    
    async def _process_frames(self) -> None:
        """Process frame queue and insert frames."""
        try:
            # Try to get a frame with timeout
            frame = await asyncio.wait_for(
                self.frame_queue.get(),
                timeout=0.1
            )
            
            await self._insert_frame(frame)
            
        except asyncio.TimeoutError:
            # No frames available, that's fine
            pass
        except Exception as e:
            logger.error(f"Error processing frames: {e}")
    
    def _should_flush_timeout(self) -> bool:
        """Check if batch should be flushed due to timeout."""
        if not self.current_batch:
            return False
        
        # Check if oldest signal in batch is older than timeout
        oldest_signal = min(self.current_batch, key=lambda s: s.timestamp)
        age = (datetime.now(timezone.utc) - oldest_signal.timestamp).total_seconds()
        return age >= self.batch_timeout
    
    async def _flush_batch(self) -> None:
        """Flush current batch to database."""
        if not self.current_batch:
            return
        
        try:
            # Convert batch to signal dictionaries
            signal_dicts = [signal.to_signal_dict() for signal in self.current_batch]
            
            # Insert batch into database
            await self._insert_signal_batch(signal_dicts)
            
            # Update statistics
            self.signals_processed += len(self.current_batch)
            self.batches_written += 1
            
            # Clear batch
            self.current_batch.clear()
            
            logger.debug(f"Flushed batch of {len(signal_dicts)} signals")
            
        except Exception as e:
            logger.error(f"Error flushing batch: {e}")
            # Clear batch to prevent memory buildup
            self.current_batch.clear()
    
    async def _insert_signal_batch(self, signal_dicts: List[Dict]) -> None:
        """Insert a batch of signals into the database.
        
        Args:
            signal_dicts: List of signal dictionaries to insert.
        """
        # This would use the actual database session in a real implementation
        # For now, we'll simulate the database operation
        logger.debug(f"Inserting {len(signal_dicts)} signals into database")
        
        # Simulate database insertion time
        await asyncio.sleep(0.001)  # 1ms simulation
    
    async def _insert_frame(self, frame_entry: Dict) -> None:
        """Insert a frame into the database.
        
        Args:
            frame_entry: Frame entry to insert.
        """
        try:
            # This would use the actual database session in a real implementation
            # For now, we'll simulate the database operation
            logger.debug(f"Inserting frame for session {frame_entry['session_id']}")
            
            # Simulate database insertion time
            await asyncio.sleep(0.001)  # 1ms simulation
            
            self.frames_created += 1
            
        except Exception as e:
            logger.error(f"Error inserting frame: {e}")
    
    async def create_frame_snapshot(self, session_id: int, current_data: Dict[str, any]) -> None:
        """Create a frame snapshot if enough time has passed.
        
        Args:
            session_id: Session ID.
            current_data: Current telemetry data for the session.
        """
        current_time = asyncio.get_event_loop().time()
        last_time = self.last_frame_time.get(session_id, 0)
        
        if current_time - last_time >= self.frame_interval:
            # Create frame snapshot
            frame_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": current_data,
            }
            
            await self.queue_frame(session_id, frame_data)
            self.last_frame_time[session_id] = current_time
    
    def get_statistics(self) -> Dict[str, any]:
        """Get database writer statistics.
        
        Returns:
            Dict containing statistics.
        """
        runtime = 0
        if self.start_time:
            runtime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        signals_per_minute = 0
        if runtime > 0:
            signals_per_minute = (self.signals_processed / runtime) * 60
        
        return {
            "is_running": self.is_running,
            "signals_processed": self.signals_processed,
            "frames_created": self.frames_created,
            "batches_written": self.batches_written,
            "queue_drops": self.queue_drops,
            "current_batch_size": len(self.current_batch),
            "signal_queue_size": self.signal_queue.qsize(),
            "frame_queue_size": self.frame_queue.qsize(),
            "runtime_seconds": runtime,
            "signals_per_minute": signals_per_minute,
            "batch_size": self.batch_size,
            "batch_timeout": self.batch_timeout,
            "frame_interval": self.frame_interval,
        }
    
    def get_performance_metrics(self) -> Dict[str, any]:
        """Get performance metrics for benchmarking.
        
        Returns:
            Dict containing performance metrics.
        """
        stats = self.get_statistics()
        
        return {
            "signals_per_minute": stats["signals_per_minute"],
            "signals_processed": stats["signals_processed"],
            "batches_written": stats["batches_written"],
            "average_batch_size": stats["signals_processed"] / max(stats["batches_written"], 1),
            "queue_drops": stats["queue_drops"],
            "runtime_seconds": stats["runtime_seconds"],
            "throughput_achieved": stats["signals_per_minute"] >= 5000,
        }


# Global database writer instance
db_writer = DatabaseWriter()
