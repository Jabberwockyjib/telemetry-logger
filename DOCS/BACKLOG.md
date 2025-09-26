# Backlog (create GitHub issues from these)

## Foundation
- Scaffold FastAPI app & health route.
- SQLAlchemy models + Alembic init & first migration.
- Session routes: create/list/start/stop.
- WebSocket `/ws` with in-proc pub/sub.

## Services
- GPS NMEA async reader (serial) with fix-quality handling.
- OBD async reader with configurable PID sets and rates.
- Batched DB writer (executemany/copy where possible).
- Meshtastic packer + uplink heartbeat @1 Hz.

## Frontend
- Static dashboard (cards, Chart.js rolling plots, Leaflet live map).
- Replay page with scrub bar & range query.

## Export
- CSV & Parquet streaming endpoints.

## Tests
- Unit: packing, timebase.
- Integration: DB IO + WS smoke.

## Ops
- Dockerfile + docker-compose (app + Postgres).
- Makefile basics (lint, test, run) — added after code exists.