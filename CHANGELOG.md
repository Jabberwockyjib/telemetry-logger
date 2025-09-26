# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Session Creation UI**: Added "Create New Session" button and modal form on dashboard
- **Session Form Fields**: Name (required), Car ID, Driver Name, Track/Location, Notes
- **Form Validation**: Client-side validation for required fields and length limits
- **Success Notifications**: Toast notifications for successful session creation
- **Session Info Display**: Updated dashboard to show created session details
- **Database Schema**: Added `notes` field to sessions table
- **API Integration**: Frontend form submits to `/api/v1/sessions` endpoint
- **Loading States**: Form submission with loading spinner and disabled states
- **Error Handling**: Form error display and API error handling
- **Modal UI**: Responsive modal with proper styling and accessibility
- **Comprehensive Tests**: 7 backend integration tests and 20 frontend tests for session creation
- Telemetry start/stop controls for simplified session management
- One-click telemetry logging with automatic session creation
- Real-time session status display with elapsed time
- Backend API endpoints for telemetry control (`/api/v1/telemetry/start`, `/api/v1/telemetry/stop`, `/api/v1/telemetry/status`)
- Frontend dashboard integration with start/stop buttons
- Session management improvements with `is_active` column
- Comprehensive tests for telemetry controls (backend and frontend)
- Device scanning functionality with fresh port detection
- Real-time device scanning API endpoint (`/api/v1/devices/scan`)
- Dynamic port dropdown updates in setup wizard
- Toast notification system for user feedback
- Comprehensive device scanning tests

### Fixed
- Button visibility and contrast issues across all frontend pages
- CSS variable definitions for consistent theming
- WCAG accessibility compliance for button colors and focus states
- Missing button styles in setup wizard and documentation pages
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
- Binary packing utilities (`backend/app/utils/packing.py`) for compact telemetry data:
  - High-precision scaling for lat/lon (1e7), altitude (1e2), speed (1e2), temperature (1e1)
  - Support for GPS and OBD field types with configurable scaling factors
  - Compact binary format: 6 bytes per field (type + field_id + 4-byte scaled value)
  - Comprehensive validation with range checking and error reporting
  - Roundtrip packing/unpacking with precision preservation
  - 33 comprehensive unit tests covering all functionality
- Meshtastic service (`backend/app/services/meshtastic_service.py`) for 1 Hz frame publishing:
  - Aggregates last-known values from GPS and OBD services
  - Publishes compact binary payloads at configurable rate (default 1 Hz)
  - Payload size optimization with priority-based field reduction
  - Integration with database writer for frame storage
  - WebSocket status broadcasting for real-time monitoring
  - Comprehensive statistics and performance tracking
- CLI testing tool (`scripts/test_meshtastic.py`) for frame testing:
  - Packing functionality validation and demonstration
  - Meshtastic service lifecycle testing
  - Custom test frame generation and transmission
  - Comprehensive test data validation and performance metrics
- Frontend dashboard (`frontend/`) for real-time telemetry visualization:
  - Clean, minimal HTML interface with responsive design
  - WebSocket connection to `/ws` endpoint for live data streaming
  - Chart.js integration for rolling plots (speed/RPM, engine parameters)
  - Leaflet integration for live GPS map with track recording
  - Summary cards for GPS, vehicle, engine, and system status
  - Real-time data updates with smooth animations and performance optimization
  - Configurable chart time ranges (1-30 minutes) and data point limiting
  - Interactive map with auto-centering, track recording, and detailed popups
  - Comprehensive README with usage instructions and troubleshooting
- CSV/Parquet export endpoints (`/api/v1/export/`) for data export:
  - Streaming CSV export for signals and frames with configurable filters
  - Parquet export with binary streaming for large datasets
  - Time range filtering (start_time, end_time) for historical data
  - Source and channel filtering for targeted data export
  - Pagination support for efficient large dataset processing
  - Automatic filename generation with timestamps
  - Comprehensive error handling and validation
- Data replay page (`frontend/replay.html`) for historical telemetry visualization:
  - Session selection dropdown with automatic loading
  - Time scrubber with play/pause controls for data navigation
  - Real-time statistics display (total signals, duration, sources, channels)
  - Historical chart visualization with Chart.js integration
  - GPS track replay with Leaflet map integration
  - Export functionality for downloaded data analysis
  - Responsive design with touch-friendly controls
- Comprehensive export test suite (`tests/test_export.py`):
  - 12 test cases covering all export functionality
  - Streaming performance validation
  - Error handling and edge case testing
  - Filter validation and parameter testing
  - Large dataset pagination testing

### Fixed
- Device setup wizard "Scan devices" button now works correctly
- Port dropdowns update dynamically when scanning for devices
- Preserves user selections when ports are rescanned
- Handles empty device lists gracefully
- Shows loading states and success/error feedback

### Changed
- Updated FastAPI app to include session routes, WebSocket routes, export routes, and service manager integration
- Enhanced application lifespan management for proper service cleanup including WebSocket bus shutdown
- Service manager now integrates with WebSocket bus for real-time data broadcasting
- OBD service integration with service manager for real-time automotive data collection
- GPS and OBD services now send telemetry data to database writer for persistent storage
- Service manager integrates with database writer for coordinated data collection and storage
- GPS and OBD services now send telemetry data to Meshtastic service for radio uplink
- Service manager integrates with Meshtastic service for 1 Hz frame publishing
- Added pagination support to CRUD operations for efficient data export
- Enhanced database models with additional query methods for export functionality

### Technical Details
- Full async/await support throughout the application
- Type hints and docstrings for all public functions
- Proper error handling and HTTP status codes
- Database session dependency injection
- Service task lifecycle management with cancellation support
