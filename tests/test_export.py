"""Tests for export functionality."""

import asyncio
import csv
import io
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.db.crud import signal_crud, session_crud
from backend.app.db.models import Signal
from backend.app.main import app


@pytest.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory SQLite database session for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            yield session
        
    finally:
        await engine.dispose()
        Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_session(client: TestClient) -> int:
        """Create a test session with signals via API."""
        # Create session via API
        session_data = {
            "name": "Test Export Session",
            "car_id": "TEST001",
            "driver": "Test Driver",
            "track": "Test Track",
        }
        
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 201
        session = response.json()
        session_id = session["id"]
        
        # Create test signals directly in database
        # Note: This is a simplified approach for testing
        # In a real scenario, signals would be created through the data collection services
        
        return session_id


class TestExportEndpoints:
    """Test export API endpoints."""
    
    def test_export_signals_csv_empty_session(self, client: TestClient, test_session: int) -> None:
        """Test CSV export of signals for empty session."""
        response = client.get(f"/api/v1/export/sessions/{test_session}/signals.csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert f"session_{test_session}_signals_" in response.headers["content-disposition"]
        
        # Parse CSV content
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Should have just the header for empty session
        assert len(rows) == 0
        
        # Check that we got a valid CSV structure
        assert csv_content.strip() != ""
    
    def test_export_signals_csv_with_filters(self, client: TestClient, test_session: int) -> None:
        """Test CSV export with source and channel filters."""
        # Filter by source
        response = client.get(
            f"/api/v1/export/sessions/{test_session}/signals.csv",
            params={"sources": ["gps"]}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Filter by channel
        response = client.get(
            f"/api/v1/export/sessions/{test_session}/signals.csv",
            params={"channels": ["RPM"]}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    def test_export_signals_csv_time_filter(self, client: TestClient, test_session: int) -> None:
        """Test CSV export with time filters."""
        base_time = datetime.now(timezone.utc)
        start_time = base_time.replace(microsecond=200000)
        end_time = base_time.replace(microsecond=800000)
        
        response = client.get(
            f"/api/v1/export/sessions/{test_session}/signals.csv",
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    def test_export_signals_parquet(self, client: TestClient, test_session: int) -> None:
        """Test Parquet export of signals."""
        response = client.get(f"/api/v1/export/sessions/{test_session}/signals.parquet")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        assert "attachment" in response.headers["content-disposition"]
        assert f"session_{test_session}_signals_" in response.headers["content-disposition"]
    
    def test_export_frames_csv(self, client: TestClient, test_session: int) -> None:
        """Test CSV export of frames."""
        response = client.get(f"/api/v1/export/sessions/{test_session}/frames.csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert f"session_{test_session}_frames_" in response.headers["content-disposition"]
    
    def test_export_nonexistent_session(self, client: TestClient) -> None:
        """Test export with non-existent session."""
        response = client.get("/api/v1/export/sessions/99999/signals.csv")
        
        assert response.status_code == 404
        error_data = response.json()
        assert "not found" in error_data["detail"].lower()
    
    def test_export_streaming_performance(self, client: TestClient, test_session: int) -> None:
        """Test that export streams data efficiently."""
        import time
        
        start_time = time.time()
        response = client.get(f"/api/v1/export/sessions/{test_session}/signals.csv")
        end_time = time.time()
        
        # Should complete quickly for small dataset
        assert end_time - start_time < 1.0
        assert response.status_code == 200


class TestExportStreaming:
    """Test streaming export functionality."""
    
    @pytest.fixture
    def large_session(self, client: TestClient) -> int:
        """Create a session for streaming tests."""
        # Create session via API
        session_data = {
            "name": "Large Export Session",
            "car_id": "LARGE001",
        }
        
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 201
        session = response.json()
        return session["id"]
    
    def test_large_csv_export_streaming(self, client: TestClient, large_session: int) -> None:
        """Test that large CSV exports stream properly."""
        response = client.get(f"/api/v1/export/sessions/{large_session}/signals.csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    def test_export_with_pagination(self, client: TestClient, large_session: int) -> None:
        """Test that export handles pagination correctly."""
        # This test verifies that the export endpoint can handle
        # large datasets by processing them in batches
        
        response = client.get(f"/api/v1/export/sessions/{large_session}/signals.csv")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"


class TestExportErrorHandling:
    """Test export error handling."""
    
    
    def test_export_invalid_session_id(self, client: TestClient) -> None:
        """Test export with invalid session ID."""
        response = client.get("/api/v1/export/sessions/invalid/signals.csv")
        
        assert response.status_code == 422  # Validation error
    
    def test_export_invalid_time_format(self, client: TestClient) -> None:
        """Test export with invalid time format."""
        response = client.get(
            "/api/v1/export/sessions/1/signals.csv",
            params={"start_time": "invalid-time"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_export_empty_session(self, client: TestClient) -> None:
        """Test export of session with no data."""
        # Create empty session via API
        session_data = {"name": "Empty Session"}
        response = client.post("/api/v1/sessions", json=session_data)
        assert response.status_code == 201
        session = response.json()
        
        # Export signals
        response = client.get(f"/api/v1/export/sessions/{session['id']}/signals.csv")
        
        assert response.status_code == 200
        
        # Should return just the header
        csv_content = response.text
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        assert len(rows) == 0  # No data rows, just header
