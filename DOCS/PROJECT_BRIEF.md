# Project Brief (Requirements)

## Objective
Telemetry data logging + live dashboard + 1 Hz pit uplink over Meshtastic.

## Functional Requirements
1. Sessions: create, start, stop, list, notes; all data keyed by `session_id`.
2. Ingest:
   - OBD-II PIDs (configurable rates).
   - GPS NMEA at 5–10 Hz (lat/lon/speed/quality/sats).
   - (Phase 2) Optional camera with sidecar timestamps.
3. Storage: SQL (signals table = narrow timeseries rows; optional frames table for playback).
4. Live: WebSocket pushes compact “current state” frames to the dashboard.
5. Historical queries & export: CSV/Parquet for a session/time range.
6. Uplink: 1 Hz packed subset (lat, lon, speed_kph, rpm, coolant_c, oil_p?, fuel_pct, alert_bits).
7. Replay: scrub through recorded data; map trace and time plots.

## Non-Functional
- Throughput: sustainably log ≥5k rows/min on dev hardware.
- Latency: WS median update <200 ms.
- Resilience: auto-reconnect devices; backoff; never block DB writes.
- Security: local-only by default; CORS restricted; Meshtastic PSK required.
- Portability: dev on macOS/Linux; deploy on Linux.

## Out of Scope (MVP)
- Cloud dashboards and multi-user auth.
- Advanced video overlays.
- Predictive analytics/ML.