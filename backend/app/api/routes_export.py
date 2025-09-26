"""Export routes for CSV and Parquet data streaming."""

import asyncio
import csv
import io
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.crud import signal_crud, session_crud, frame_crud
from ..db.base import get_db
from ..db.models import Signal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/sessions/{session_id}/signals.csv")
async def export_signals_csv(
    session_id: int,
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    sources: Optional[List[str]] = Query(None, description="Filter by data sources"),
    channels: Optional[List[str]] = Query(None, description="Filter by channels"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export signals as CSV with streaming support.
    
    Args:
        session_id: Session ID to export.
        start_time: Optional start time filter.
        end_time: Optional end time filter.
        sources: Optional list of sources to filter by.
        channels: Optional list of channels to filter by.
        db: Database session.
        
    Returns:
        Streaming CSV response.
    """
    # Verify session exists
    session = await session_crud.get_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Create CSV generator
    csv_generator = generate_signals_csv(
        db, session_id, start_time, end_time, sources, channels
    )
    
    # Create filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"session_{session_id}_signals_{timestamp}.csv"
    
    return StreamingResponse(
        csv_generator,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/sessions/{session_id}/signals.parquet")
async def export_signals_parquet(
    session_id: int,
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    sources: Optional[List[str]] = Query(None, description="Filter by data sources"),
    channels: Optional[List[str]] = Query(None, description="Filter by channels"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export signals as Parquet with streaming support.
    
    Args:
        session_id: Session ID to export.
        start_time: Optional start time filter.
        end_time: Optional end time filter.
        sources: Optional list of sources to filter by.
        channels: Optional list of channels to filter by.
        db: Database session.
        
    Returns:
        Streaming Parquet response.
    """
    # Verify session exists
    session = await session_crud.get_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Create Parquet generator
    parquet_generator = generate_signals_parquet(
        db, session_id, start_time, end_time, sources, channels
    )
    
    # Create filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"session_{session_id}_signals_{timestamp}.parquet"
    
    return StreamingResponse(
        parquet_generator,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/sessions/{session_id}/frames.csv")
async def export_frames_csv(
    session_id: int,
    start_time: Optional[datetime] = Query(None, description="Start time (ISO format)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO format)"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export frames as CSV with streaming support.
    
    Args:
        session_id: Session ID to export.
        start_time: Optional start time filter.
        end_time: Optional end time filter.
        db: Database session.
        
    Returns:
        Streaming CSV response.
    """
    # Verify session exists
    session = await session_crud.get_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Create CSV generator
    csv_generator = generate_frames_csv(db, session_id, start_time, end_time)
    
    # Create filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"session_{session_id}_frames_{timestamp}.csv"
    
    return StreamingResponse(
        csv_generator,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def generate_signals_csv(
    db: AsyncSession,
    session_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    sources: Optional[List[str]] = None,
    channels: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """Generate CSV data for signals with streaming.
    
    Args:
        db: Database session.
        session_id: Session ID.
        start_time: Optional start time filter.
        end_time: Optional end time filter.
        sources: Optional sources filter.
        channels: Optional channels filter.
        
    Yields:
        CSV data chunks.
    """
    # Create CSV buffer
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    header = [
        "id", "session_id", "source", "channel", "ts_utc", "ts_mono_ns",
        "value_num", "value_text", "unit", "quality"
    ]
    writer.writerow(header)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)
    
    # Stream data in batches
    batch_size = 1000
    offset = 0
    
    while True:
        # Fetch batch of signals
        signals = await signal_crud.get_signals_paginated(
            db=db,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            sources=sources,
            channels=channels,
            limit=batch_size,
            offset=offset
        )
        
        if not signals:
            break
        
        # Write batch to CSV
        for signal in signals:
            row = [
                signal.id,
                signal.session_id,
                signal.source,
                signal.channel,
                signal.ts_utc.isoformat() if signal.ts_utc else "",
                signal.ts_mono_ns,
                signal.value_num,
                signal.value_text,
                signal.unit,
                signal.quality
            ]
            writer.writerow(row)
        
        # Yield CSV chunk
        csv_data = output.getvalue()
        if csv_data:
            yield csv_data
            output.seek(0)
            output.truncate(0)
        
        offset += batch_size
        
        # Small delay to prevent overwhelming the client
        await asyncio.sleep(0.001)


async def generate_signals_parquet(
    db: AsyncSession,
    session_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    sources: Optional[List[str]] = None,
    channels: Optional[List[str]] = None,
) -> AsyncGenerator[bytes, None]:
    """Generate Parquet data for signals with streaming.
    
    Args:
        db: Database session.
        session_id: Session ID.
        start_time: Optional start time filter.
        end_time: Optional end time filter.
        sources: Optional sources filter.
        channels: Optional channels filter.
        
    Yields:
        Parquet data chunks.
    """
    try:
        import pandas as pd
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError:
        # Fallback to CSV if Parquet libraries not available
        logger.warning("Parquet libraries not available, falling back to CSV")
        csv_gen = generate_signals_csv(db, session_id, start_time, end_time, sources, channels)
        async for chunk in csv_gen:
            yield chunk.encode('utf-8')
        return
    
    # Create Parquet buffer
    output = io.BytesIO()
    
    # Stream data in batches
    batch_size = 10000
    offset = 0
    first_batch = True
    
    while True:
        # Fetch batch of signals
        signals = await signal_crud.get_signals_paginated(
            db=db,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            sources=sources,
            channels=channels,
            limit=batch_size,
            offset=offset
        )
        
        if not signals:
            break
        
        # Convert to DataFrame
        data = []
        for signal in signals:
            data.append({
                "id": signal.id,
                "session_id": signal.session_id,
                "source": signal.source,
                "channel": signal.channel,
                "ts_utc": signal.ts_utc,
                "ts_mono_ns": signal.ts_mono_ns,
                "value_num": signal.value_num,
                "value_text": signal.value_text,
                "unit": signal.unit,
                "quality": signal.quality
            })
        
        df = pd.DataFrame(data)
        
        # Convert to PyArrow table
        table = pa.Table.from_pandas(df)
        
        # Write to Parquet
        if first_batch:
            # First batch - create new file
            pq.write_table(table, output)
            first_batch = False
        else:
            # Subsequent batches - append to existing file
            # Note: This is a simplified approach. For production, consider using
            # a more sophisticated streaming Parquet writer
            temp_buffer = io.BytesIO()
            pq.write_table(table, temp_buffer)
            output.write(temp_buffer.getvalue())
        
        offset += batch_size
        
        # Small delay to prevent overwhelming the client
        await asyncio.sleep(0.001)
    
    # Yield the complete Parquet file
    output.seek(0)
    yield output.getvalue()


async def generate_frames_csv(
    db: AsyncSession,
    session_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> AsyncGenerator[str, None]:
    """Generate CSV data for frames with streaming.
    
    Args:
        db: Database session.
        session_id: Session ID.
        start_time: Optional start time filter.
        end_time: Optional end time filter.
        
    Yields:
        CSV data chunks.
    """
    # Create CSV buffer
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    header = ["id", "session_id", "ts_utc", "ts_mono_ns", "payload_json"]
    writer.writerow(header)
    yield output.getvalue()
    output.seek(0)
    output.truncate(0)
    
    # Stream data in batches
    batch_size = 1000
    offset = 0
    
    while True:
        # Fetch batch of frames
        frames = await frame_crud.get_frames_paginated(
            db=db,
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            limit=batch_size,
            offset=offset
        )
        
        if not frames:
            break
        
        # Write batch to CSV
        for frame in frames:
            row = [
                frame.id,
                frame.session_id,
                frame.ts_utc.isoformat() if frame.ts_utc else "",
                frame.ts_mono_ns,
                frame.payload_json
            ]
            writer.writerow(row)
        
        # Yield CSV chunk
        csv_data = output.getvalue()
        if csv_data:
            yield csv_data
            output.seek(0)
            output.truncate(0)
        
        offset += batch_size
        
        # Small delay to prevent overwhelming the client
        await asyncio.sleep(0.001)
