# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
- Comprehensive test suite for session endpoints and service manager
- Database models and CRUD operations for sessions, signals, and frames
- Alembic migration system with initial schema
- Database initialization scripts

### Changed
- Updated FastAPI app to include session routes and service manager integration
- Enhanced application lifespan management for proper service cleanup

### Technical Details
- Full async/await support throughout the application
- Type hints and docstrings for all public functions
- Proper error handling and HTTP status codes
- Database session dependency injection
- Service task lifecycle management with cancellation support
