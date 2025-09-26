# Architecture Outline

- FastAPI app with async services started by a lifecycle manager.
- DB writer consumes queues from services and performs batched inserts.
- WebSocket bus publishes compact frames (last-known values).
- Meshtastic uplink task aggregates last-known values each second and packs binary payload.
- Frontend connects to WS for live; uses REST for history/replay.

Tables:
- sessions(id, name, car_id, driver, track, created_utc, notes)
- signals(id, session_id, source, channel, ts_utc, ts_mono_ns, value_num, value_text, unit, quality)
- frames(id, session_id, ts_utc, ts_mono_ns, payload_json)