# Cartelem - Async Telemetry Data Collection & Streaming

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance, async telemetry data collection and streaming system designed for automotive and IoT applications. Cartelem provides real-time data collection from OBD-II, GPS, and other sensors with WebSocket streaming, data export, and historical replay capabilities.

## 🚀 Features

### Core Functionality
- **Real-time Data Collection**: OBD-II, GPS, and custom sensor integration
- **WebSocket Streaming**: Live telemetry data with <200ms latency
- **Data Export**: CSV/Parquet export with configurable filters
- **Historical Replay**: Interactive time-based data navigation
- **High Performance**: ≥5k rows/min database throughput
- **Binary Packing**: Compact telemetry data for radio transmission

### Data Sources
- **OBD-II**: Engine parameters, speed, RPM, throttle, coolant temperature
- **GPS**: Position, speed, heading, altitude with NMEA parsing
- **Meshtastic**: Radio uplink for remote telemetry transmission
- **Custom Sensors**: Extensible architecture for additional data sources

### Frontend Dashboard
- **Live Dashboard**: Real-time charts, maps, and status cards
- **Data Replay**: Historical session playback with time scrubber
- **Export Interface**: Direct data download from web interface
- **Mobile Responsive**: Touch-friendly controls and responsive design

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Frontend](#frontend)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🏃 Quick Start

1. **Clone and Install**
   ```bash
   git clone https://github.com/yourusername/cartelem.git
   cd cartelem
   pip install -e .
   ```

2. **Initialize Database**
   ```bash
   alembic upgrade head
   ```

3. **Start Server**
   ```bash
   python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Access Dashboard**
   - Live Dashboard: http://localhost:8000/index.html
   - Data Replay: http://localhost:8000/replay.html
   - API Docs: http://localhost:8000/docs

## 📦 Installation

### Prerequisites
- Python 3.9+
- SQLite (development) or PostgreSQL (production)
- OBD-II adapter (for automotive data)
- GPS device with NMEA output (optional)

### Install Dependencies
```bash
# Core dependencies
pip install fastapi uvicorn sqlalchemy alembic pydantic aiosqlite

# Optional dependencies for full functionality
pip install pandas pyarrow pyserial obd  # Note: obd requires Python < 3.12
```

### Development Setup
```bash
# Clone repository
git clone https://github.com/yourusername/cartelem.git
cd cartelem

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
black backend/ tests/
ruff check backend/ tests/
```

## ⚙️ Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=sqlite+aiosqlite:///./cartelem.db

# Development settings
DEBUG=true
LOG_LEVEL=INFO

# GPS Configuration
GPS_PORT=/dev/ttyUSB0
GPS_BAUDRATE=9600
GPS_RATE_HZ=10

# OBD Configuration
OBD_PORT=/dev/ttyUSB1
OBD_BAUDRATE=38400
OBD_RATE_HZ=5

# Meshtastic Configuration
MESHTASTIC_RATE_HZ=1
```

### Database Configuration
- **Development**: SQLite with `aiosqlite` (default)
- **Production**: PostgreSQL with `asyncpg`
- **Migrations**: Managed with Alembic

## 🎯 Usage

### Starting and Stopping Telemetry
```bash
# Start telemetry logging (creates session automatically)
curl -X POST http://localhost:8000/api/v1/telemetry/start

# Check telemetry status
curl http://localhost:8000/api/v1/telemetry/status

# Stop telemetry logging
curl -X POST http://localhost:8000/api/v1/telemetry/stop
```

### Manual Session Management
```bash
# Create a new telemetry session manually
curl -X POST http://localhost:8000/api/v1/sessions \
  -H 'Content-Type: application/json' \
  -d '{"name": "Track Day", "car_id": "CAR001", "driver": "John Doe"}'

# Start data collection for specific session
curl -X POST http://localhost:8000/api/v1/sessions/1/start

# Stop data collection
curl -X POST http://localhost:8000/api/v1/sessions/1/stop
```

### Data Export
```bash
# Export signals as CSV
curl http://localhost:8000/api/v1/export/sessions/1/signals.csv

# Export with filters
curl "http://localhost:8000/api/v1/export/sessions/1/signals.csv?sources=gps&channels=latitude,longitude"

# Export as Parquet
curl http://localhost:8000/api/v1/export/sessions/1/signals.parquet
```

### WebSocket Connection
```javascript
// Connect to live telemetry stream
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?session_id=1');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Telemetry data:', data);
};
```

## 📚 API Documentation

### Core Endpoints

#### Telemetry Control
- `POST /api/v1/telemetry/start` - Start telemetry logging
- `POST /api/v1/telemetry/stop` - Stop telemetry logging
- `GET /api/v1/telemetry/status` - Get current telemetry status

#### Sessions
- `POST /api/v1/sessions` - Create new session
- `GET /api/v1/sessions` - List sessions
- `POST /api/v1/sessions/{id}/start` - Start data collection
- `POST /api/v1/sessions/{id}/stop` - Stop data collection
- `GET /api/v1/sessions/{id}/signals` - Get session signals

#### Export
- `GET /api/v1/export/sessions/{id}/signals.csv` - Export signals as CSV
- `GET /api/v1/export/sessions/{id}/signals.parquet` - Export signals as Parquet
- `GET /api/v1/export/sessions/{id}/frames.csv` - Export frames as CSV

#### WebSocket
- `WS /api/v1/ws?session_id={id}` - Real-time telemetry stream

### Query Parameters

#### Export Filters
- `start_time`: ISO datetime for filtering start
- `end_time`: ISO datetime for filtering end
- `sources`: Array of source names (gps, obd, meshtastic)
- `channels`: Array of channel names (latitude, speed, RPM, etc.)

#### Pagination
- `limit`: Maximum number of records (default: 1000)
- `offset`: Number of records to skip (default: 0)

## 🖥️ Frontend

### Live Dashboard (`/index.html`)
- Real-time telemetry visualization
- Interactive charts (Chart.js)
- Live GPS map (Leaflet)
- Status cards for all data sources
- WebSocket connection management
- **Start/Stop Telemetry Controls**: One-click telemetry session management
- **Session Status Display**: Current session ID and elapsed time

### Data Replay (`/replay.html`)
- Historical session playback
- Time scrubber with play/pause controls
- Session statistics and metadata
- Export functionality
- GPS track visualization

### Features
- **Responsive Design**: Works on desktop and mobile
- **Real-time Updates**: <200ms data latency
- **Interactive Controls**: Touch-friendly interface
- **Export Integration**: Direct download from UI
- **Error Handling**: Graceful connection management

## 🔧 Development

### Project Structure
```
cartelem/
├── backend/
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── db/            # Database models and CRUD
│   │   ├── services/      # Data collection services
│   │   ├── utils/         # Utilities and schemas
│   │   └── main.py        # FastAPI application
│   └── alembic/           # Database migrations
├── frontend/
│   ├── index.html         # Live dashboard
│   ├── replay.html        # Data replay
│   ├── js/                # JavaScript modules
│   └── css/               # Stylesheets
├── tests/                 # Test suite
├── scripts/               # Utility scripts
└── docs/                  # Documentation
```

### Key Components

#### Services
- **GPS Service**: NMEA parsing and serial communication
- **OBD Service**: OBD-II protocol implementation
- **Database Writer**: High-performance data batching
- **WebSocket Bus**: Real-time data broadcasting
- **Meshtastic Service**: Radio uplink transmission

#### Database Models
- **Sessions**: Telemetry session metadata
- **Signals**: Individual telemetry measurements
- **Frames**: Snapshot data for export

### Testing
```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_export.py -v
pytest tests/test_gps_service.py -v
pytest tests/test_obd_service.py -v

# Run with coverage
pytest --cov=backend --cov-report=html
```

### Code Quality
```bash
# Format code
black backend/ tests/

# Lint code
ruff check backend/ tests/

# Type checking
mypy backend/
```

## 🚀 Deployment

### Production Setup

#### 1. Database Migration
```bash
# Set production database URL
export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/cartelem

# Run migrations
alembic upgrade head
```

#### 2. Environment Configuration
```env
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/cartelem
LOG_LEVEL=WARNING
```

#### 3. Process Management
```bash
# Using systemd
sudo systemctl enable cartelem
sudo systemctl start cartelem

# Using Docker
docker build -t cartelem .
docker run -p 8000:8000 cartelem
```

#### 4. Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api/v1/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Standards
- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Maintain test coverage >90%
- Use conventional commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) for database ORM
- [Chart.js](https://www.chartjs.org/) for data visualization
- [Leaflet](https://leafletjs.com/) for interactive maps
- [python-OBD](https://github.com/brendan-w/python-OBD) for OBD-II support

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/cartelem/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cartelem/discussions)
- **Documentation**: [Project Wiki](https://github.com/yourusername/cartelem/wiki)

---

**Cartelem** - High-performance telemetry data collection and streaming for the modern age.