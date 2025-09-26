# Cursor Prompts (copy into Cursor “/chat” one by one)

## 01—Initialize Python backend (no business logic yet)
"Create backend/app with a FastAPI app factory, `routes_health.py` returning {status:'ok'}, and a minimal `pyproject.toml` using fastapi, uvicorn[standard], sqlalchemy, alembic, pydantic, asyncio, aiosqlite. Set up ruff/black/mypy configs. Create `.env.example` with DATABASE_URL for SQLite dev. Add a simple `main.py` to run app. Follow `.cursorrules`. Write unit test `tests/test_health.py`. Do not implement domain features yet."

## 02—DB models & Alembic migration
"Add SQLAlchemy models for `sessions`, `signals`, `frames` exactly as in docs/ARCHITECTURE.md; add indices shown; generate first Alembic migration; provide DB init script. Include CRUD helpers for batch inserts. Add tests that create an in-memory SQLite DB and verify migrations apply."

## 03—Session routes + lifecycle manager
"Implement endpoints: POST /api/sessions, POST /api/sessions/{id}/start, POST /api/sessions/{id}/stop, GET /api/sessions. Build a `services/manager.py` that tracks active session_id and starts/stops data services (stubs only). Include Pydantic schemas, typing, and docstrings. Add tests."

## 04—WebSocket live bus
"Create `services/websocket_bus.py` (pub/sub), and `/ws?session_id=` route that streams JSON frames. Include a periodic heartbeat (no data) until services exist. Test: client can connect and receive heartbeats."

## 05—GPS service
"Implement `gps_service.py` that reads NMEA from a serial port (config), parses GGA/RMC/VTG, timestamps (UTC + monotonic), pushes to DB queue, and publishes last-known values to WS bus. Include reconnect/backoff. Configurable rate. Unit test parsing; integration test with sample NMEA log."

## 06—OBD service
"Implement `obd_service.py` using python-OBD in async wrapper. Allow a configurable PID set and per-PID rates. On each reading, append to DB queue and update WS last-known values with units and quality. Include graceful handling when a PID is unsupported."

## 07—DB writer
"Add a single DB writer task consuming queues from services, batching inserts into `signals` and building optional `frames` JSON snapshots. Target ≥5k rows/min in a simple benchmark test."

## 08—Meshtastic uplink
"Implement `packing.py` with binary packing described in docs (lat/lon*1e7 etc.). Add `meshtastic_service.py` to publish a 1 Hz frame using last-known values. Provide a CLI to send a test frame. Add tests for packing."

## 09—Frontend dashboard
"Create `frontend/index.html`, `js/app.js`, `js/charts.js`, `js/map.js`, `css/styles.css`. Connect to `/ws`, render rolling plots (Chart.js), live map (Leaflet), and summary cards. Minimal, clean UI. Include a README with basic usage."

## 10—Exports + Replay
"Add CSV/Parquet export endpoints and a `/replay` HTML page that queries historical data, renders charts, and provides a scrub bar for time navigation. Include tests for CSV/Parquet streaming."

(Each prompt ends with:) "Open a PR named with Conventional Commits; add CHANGELOG entry under 'Unreleased'; ensure CI passes."