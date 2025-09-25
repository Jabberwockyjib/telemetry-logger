# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GPS service (`backend/app/services/gps_service.py`) with NMEA parsing capabilities:
  - Reads NMEA data from configurable serial ports with automatic reconnection and backoff logic
  - Parses GGA (Global Positioning System Fix Data), RMC (Recommended Minimum Navigation Information), and VTG (Track Made Good and Ground Speed) sentences
  - Converts degrees decimal minutes to decimal degrees for latitude/longitude
  - Timestamps all data with UTC and monotonic timestamps
  - Publishes parsed GPS data to WebSocket bus for real-time streaming
  - Configurable data collection rate and serial port settings
  - Comprehensive error handling and logging
- WebSocket bus (`backend/app/services/websocket_bus.py`) for real-time data streaming:
  - Pub/sub pattern for broadcasting telemetry data to connected clients
  - Periodic heartbeat functionality to maintain connection health
  - Session-based connection management
  - Graceful connection cleanup and resource management
- WebSocket API endpoint (`/api/v1/ws?session_id=`) for real-time telemetry data streaming
- WebSocket test page (`/api/v1/ws/test`) for testing WebSocket connections
- Session management API endpoints:
  - `POST /api/v1/sessions` - Create new telemetry session
  - `GET /api/v1/sessions` - List sessions with pagination
  - `POST /api/v1/sessions/{id}/start` - Start data collection services
  - `POST /api/v1/sessions/{id}/stop` - Stop data collection services
- Pydantic schemas for session requests and responses with validation
- Service manager (`services/manager.py`) for coordinating telemetry data collection:
  - Tracks active sessions and manages service lifecycle
  - Stub implementations for OBD-II, GPS, and Meshtastic services
  - Async task management with proper cleanup
- Comprehensive test suite for session endpoints, service manager, WebSocket functionality, and GPS service
- Database models and CRUD operations for sessions, signals, and frames
- Alembic migration system with initial schema
- Database initialization scripts
- `pyserial>=3.5` dependency for serial port communication
- OBD-II service (`backend/app/services/obd_service.py`) with python-OBD integration:
  - Configurable PID set with per-PID collection rates
  - Automatic PID discovery and unsupported PID handling
  - Real-time OBD data collection with WebSocket streaming
  - Graceful error handling and automatic reconnection
  - Comprehensive PID support (speed, RPM, throttle, engine load, etc.)
  - Quality indicators and unit conversion for all readings
- `obd>=0.7.1` dependency for OBD-II communication (Python < 3.12 compatible)
- Database writer service (`backend/app/services/db_writer.py`) for high-performance telemetry data batching:
  - Single DB writer task consuming queues from all services
  - Configurable batch inserts into `signals` table with size and timeout controls
  - Optional `frames` JSON snapshots with configurable intervals
  - High-performance processing targeting ≥5k rows/min throughput
  - Queue-based architecture with overflow protection and drop counting
  - Comprehensive performance benchmarking and metrics collection
  - Integration with GPS and OBD services for automatic data collection

### Changed
- Updated FastAPI app to include session routes, WebSocket routes, and service manager integration
- Enhanced application lifespan management for proper service cleanup including WebSocket bus shutdown
- Service manager now integrates with WebSocket bus for real-time data broadcasting
- OBD service integration with service manager for real-time automotive data collection
- GPS and OBD services now send telemetry data to database writer for persistent storage
- Service manager integrates with database writer for coordinated data collection and storage

### Technical Details
- Full async/await support throughout the application
- Type hints and docstrings for all public functions
- Proper error handling and HTTP status codes
- Database session dependency injection
- Service task lifecycle management with cancellation support
