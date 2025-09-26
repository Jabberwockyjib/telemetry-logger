# Cartelem API Documentation

## Overview

The Cartelem API provides RESTful endpoints for telemetry data collection, session management, and data export. All endpoints are versioned under `/api/v1/` and return JSON responses.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication. In production deployments, consider implementing API keys or OAuth2.

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "id": 1,
  "name": "Session Name",
  "created_utc": "2024-01-01T00:00:00Z",
  "status": "active"
}
```

### Error Response
```json
{
  "detail": "Error message describing what went wrong"
}
```

## HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

## Endpoints

### Health Check

#### GET /health
Check API health status.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Session Management

#### POST /sessions
Create a new telemetry session.

**Request Body:**
```json
{
  "name": "Track Day Session",
  "car_id": "CAR001",
  "driver": "John Doe",
  "track": "Laguna Seca",
  "notes": "Optional session notes"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Track Day Session",
  "car_id": "CAR001",
  "driver": "John Doe",
  "track": "Laguna Seca",
  "notes": "Optional session notes",
  "created_utc": "2024-01-01T00:00:00Z",
  "is_active": false
}
```

#### GET /sessions
List all telemetry sessions.

**Query Parameters:**
- `limit` (integer, optional): Maximum number of sessions to return (default: 100, max: 1000)
- `offset` (integer, optional): Number of sessions to skip (default: 0)

**Response:**
```json
{
  "sessions": [
    {
      "id": 1,
      "name": "Track Day Session",
      "car_id": "CAR001",
      "driver": "John Doe",
      "track": "Laguna Seca",
      "notes": "Optional session notes",
      "created_utc": "2024-01-01T00:00:00Z",
      "is_active": false
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

#### POST /sessions/{session_id}/start
Start data collection for a session.

**Response:**
```json
{
  "session_id": 1,
  "status": "started",
  "message": "Data collection started for session 1",
  "started_at": "2024-01-01T00:00:00Z"
}
```

#### POST /sessions/{session_id}/stop
Stop data collection for a session.

**Response:**
```json
{
  "session_id": 1,
  "status": "stopped",
  "message": "Data collection stopped for session 1",
  "stopped_at": "2024-01-01T00:00:00Z"
}
```

#### GET /sessions/{session_id}/signals
Get telemetry signals for a session.

**Query Parameters:**
- `limit` (integer, optional): Maximum number of signals to return (default: 10000, max: 100000)
- `offset` (integer, optional): Number of signals to skip (default: 0)

**Response:**
```json
[
  {
    "id": 1,
    "session_id": 1,
    "source": "gps",
    "channel": "latitude",
    "ts_utc": "2024-01-01T00:00:00Z",
    "ts_mono_ns": 1000000000,
    "value_num": 37.7749,
    "value_text": null,
    "unit": "deg",
    "quality": "good"
  }
]
```

### Data Export

#### GET /export/sessions/{session_id}/signals.csv
Export session signals as CSV.

**Query Parameters:**
- `start_time` (string, optional): ISO datetime for filtering start
- `end_time` (string, optional): ISO datetime for filtering end
- `sources` (array, optional): Filter by data sources (gps, obd, meshtastic)
- `channels` (array, optional): Filter by channel names

**Response:**
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename=session_{id}_signals_{timestamp}.csv`

**Example:**
```bash
curl "http://localhost:8000/api/v1/export/sessions/1/signals.csv?sources=gps&channels=latitude,longitude"
```

#### GET /export/sessions/{session_id}/signals.parquet
Export session signals as Parquet.

**Query Parameters:** Same as CSV export

**Response:**
- Content-Type: `application/octet-stream`
- Content-Disposition: `attachment; filename=session_{id}_signals_{timestamp}.parquet`

#### GET /export/sessions/{session_id}/frames.csv
Export session frames as CSV.

**Query Parameters:**
- `start_time` (string, optional): ISO datetime for filtering start
- `end_time` (string, optional): ISO datetime for filtering end

**Response:**
- Content-Type: `text/csv`
- Content-Disposition: `attachment; filename=session_{id}_frames_{timestamp}.csv`

### WebSocket Streaming

#### WS /ws?session_id={session_id}
Real-time telemetry data stream.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?session_id=1');
```

**Message Types:**

1. **Connection Message**
```json
{
  "type": "connection",
  "session_id": 1,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

2. **Heartbeat Message**
```json
{
  "type": "heartbeat",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

3. **Telemetry Data**
```json
{
  "type": "telemetry",
  "source": "gps",
  "channel": "latitude",
  "value": 37.7749,
  "unit": "deg",
  "quality": "good",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

4. **Echo Message** (for testing)
```json
{
  "type": "echo",
  "message": "test message",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Data Models

### Session
```json
{
  "id": 1,
  "name": "Session Name",
  "car_id": "CAR001",
  "driver": "John Doe",
  "track": "Track Name",
  "notes": "Optional notes",
  "created_utc": "2024-01-01T00:00:00Z",
  "is_active": false
}
```

### Signal
```json
{
  "id": 1,
  "session_id": 1,
  "source": "gps",
  "channel": "latitude",
  "ts_utc": "2024-01-01T00:00:00Z",
  "ts_mono_ns": 1000000000,
  "value_num": 37.7749,
  "value_text": null,
  "unit": "deg",
  "quality": "good"
}
```

### Frame
```json
{
  "id": 1,
  "session_id": 1,
  "ts_utc": "2024-01-01T00:00:00Z",
  "ts_mono_ns": 1000000000,
  "payload_json": "{\"latitude\": 37.7749, \"longitude\": -122.4194}"
}
```

## Data Sources and Channels

### GPS Data
- **Source**: `gps`
- **Channels**:
  - `latitude` (degrees)
  - `longitude` (degrees)
  - `altitude` (meters)
  - `speed_kph` (km/h)
  - `heading_deg` (degrees)
  - `satellites` (count)
  - `hdop` (horizontal dilution of precision)

### OBD-II Data
- **Source**: `obd`
- **Channels**:
  - `RPM` (revolutions per minute)
  - `SPEED` (km/h)
  - `THROTTLE_POS` (percentage)
  - `ENGINE_LOAD` (percentage)
  - `COOLANT_TEMP` (Celsius)
  - `INTAKE_TEMP` (Celsius)
  - `FUEL_LEVEL` (percentage)
  - `MAF` (mass air flow, g/s)

### Meshtastic Data
- **Source**: `meshtastic`
- **Channels**:
  - `packet_count` (count)
  - `transmit_power` (dBm)
  - `signal_strength` (dBm)
  - `snr` (signal-to-noise ratio)

## Error Handling

### Validation Errors (422)
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Not Found Errors (404)
```json
{
  "detail": "Session 999 not found"
}
```

### Server Errors (500)
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for production deployments.

## CORS

CORS is enabled for development with `allow_origins=["*"]`. For production, configure specific origins.

## Examples

### Complete Workflow

1. **Create Session**
```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H 'Content-Type: application/json' \
  -d '{"name": "Test Session", "car_id": "CAR001"}'
```

2. **Start Data Collection**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/1/start
```

3. **Monitor Real-time Data**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?session_id=1');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'telemetry') {
        console.log(`${data.source}.${data.channel}: ${data.value} ${data.unit}`);
    }
};
```

4. **Stop Data Collection**
```bash
curl -X POST http://localhost:8000/api/v1/sessions/1/stop
```

5. **Export Data**
```bash
curl http://localhost:8000/api/v1/export/sessions/1/signals.csv > session_data.csv
```

### Filtered Export
```bash
# Export only GPS data from last hour
curl "http://localhost:8000/api/v1/export/sessions/1/signals.csv?sources=gps&start_time=2024-01-01T10:00:00Z&end_time=2024-01-01T11:00:00Z"
```

### Pagination
```bash
# Get first 100 signals
curl "http://localhost:8000/api/v1/sessions/1/signals?limit=100&offset=0"

# Get next 100 signals
curl "http://localhost:8000/api/v1/sessions/1/signals?limit=100&offset=100"
```

## SDK Examples

### Python
```python
import requests
import websocket
import json

# Create session
response = requests.post('http://localhost:8000/api/v1/sessions', 
                        json={'name': 'Python Test'})
session_id = response.json()['id']

# Start collection
requests.post(f'http://localhost:8000/api/v1/sessions/{session_id}/start')

# WebSocket connection
def on_message(ws, message):
    data = json.loads(message)
    if data['type'] == 'telemetry':
        print(f"{data['source']}.{data['channel']}: {data['value']}")

ws = websocket.WebSocketApp(f'ws://localhost:8000/api/v1/ws?session_id={session_id}',
                           on_message=on_message)
ws.run_forever()
```

### JavaScript
```javascript
// Create session
const response = await fetch('http://localhost:8000/api/v1/sessions', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: 'JS Test'})
});
const session = await response.json();

// Start collection
await fetch(`http://localhost:8000/api/v1/sessions/${session.id}/start`, {
    method: 'POST'
});

// WebSocket connection
const ws = new WebSocket(`ws://localhost:8000/api/v1/ws?session_id=${session.id}`);
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'telemetry') {
        console.log(`${data.source}.${data.channel}: ${data.value} ${data.unit}`);
    }
};
```

## Testing

### WebSocket Test Page
Visit `http://localhost:8000/api/v1/ws/test` for an interactive WebSocket testing interface.

### API Documentation
Visit `http://localhost:8000/docs` for interactive API documentation with Swagger UI.

## Support

For API support and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/cartelem/issues)
- Documentation: [Project Wiki](https://github.com/yourusername/cartelem/wiki)
- Discussions: [GitHub Discussions](https://github.com/yourusername/cartelem/discussions)
