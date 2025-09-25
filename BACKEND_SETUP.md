# Backend Setup Guide

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   # or
   pip install -e .
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env as needed
   ```

3. **Run the application:**
   ```bash
   python main.py
   # or for development with auto-reload:
   python run_dev.py
   ```

4. **Test the health endpoint:**
   ```bash
   curl http://localhost:8000/api/v1/health
   # Should return: {"status": "ok"}
   ```

5. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## Project Structure

```
backend/app/
├── main.py              # FastAPI app factory
├── config.py            # Application settings
└── api/
    └── routes_health.py # Health check endpoint

tests/
└── test_health.py       # Unit tests

main.py                  # Simple runner script
run_dev.py              # Development server with auto-reload
pyproject.toml          # Project configuration and dependencies
.env.example            # Environment variables template
```

## Development Tools

- **Linting:** `ruff check .`
- **Formatting:** `black .`
- **Type checking:** `mypy backend/`
- **Testing:** `pytest tests/ -v`

## Next Steps

This is a minimal FastAPI setup. The following components are planned:

- Database models and migrations (SQLAlchemy + Alembic)
- OBD-II and GPS data ingestion services
- WebSocket streaming for live data
- Meshtastic uplink service
- Session management and data export
