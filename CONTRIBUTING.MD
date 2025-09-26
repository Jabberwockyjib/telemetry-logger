# Contributing to Cartelem

Thank you for your interest in contributing to Cartelem! This document provides comprehensive guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Documentation](#documentation)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct that ensures a welcoming environment for all contributors. Please be respectful, inclusive, and constructive in all interactions.

## Getting Started

### Prerequisites
- Python 3.9+
- Git
- SQLite (for development)
- Basic understanding of async Python, FastAPI, and SQLAlchemy

### Quick Start
1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a new branch** for your feature or bugfix
4. **Set up development environment** (see below)
5. **Make your changes** following our guidelines
6. **Add tests** for new functionality
7. **Ensure all tests pass**
8. **Submit a pull request**

## Development Setup

### 1. Repository Setup
```bash
# Clone your fork
git clone https://github.com/yourusername/cartelem.git
cd cartelem

# Add upstream remote
git remote add upstream https://github.com/originalowner/cartelem.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### 2. Database Setup
```bash
# Initialize database
alembic upgrade head

# Create test database
sqlite3 test.db < schema.sql
```

### 3. Pre-commit Hooks (Optional)
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### 4. IDE Configuration

#### VS Code
Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

#### PyCharm
- Set Python interpreter to `./venv/bin/python`
- Enable pytest as test runner
- Configure code style to use Black formatter

## Project Structure

```
cartelem/
├── backend/
│   ├── app/
│   │   ├── api/           # API route handlers
│   │   ├── db/            # Database models and CRUD
│   │   ├── services/      # Business logic services
│   │   ├── utils/         # Utility functions and schemas
│   │   └── main.py        # FastAPI application
│   └── alembic/           # Database migrations
├── frontend/
│   ├── index.html         # Live dashboard
│   ├── replay.html        # Data replay interface
│   ├── js/                # JavaScript modules
│   └── css/               # Stylesheets
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── docs/                  # Documentation
└── pyproject.toml         # Project configuration
```

### Key Components

- **API Routes** (`backend/app/api/`): FastAPI route handlers
- **Database Layer** (`backend/app/db/`): SQLAlchemy models and CRUD operations
- **Services** (`backend/app/services/`): Business logic and data collection
- **Frontend** (`frontend/`): HTML, CSS, and JavaScript for web interface
- **Tests** (`tests/`): Comprehensive test suite

## Code Style Guidelines

### Python Code Style

We follow **PEP 8** with additional rules:

#### General Rules
- **Line length**: 88 characters (Black formatter standard)
- **Imports**: Use absolute imports, group by standard library, third-party, local
- **Type hints**: Required for all function parameters and return values
- **Docstrings**: Required for all public functions, classes, and modules

#### Function Guidelines
```python
async def process_telemetry_data(
    session_id: int,
    data: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> TelemetryResult:
    """Process telemetry data for a session.
    
    Args:
        session_id: ID of the session to process data for.
        data: Dictionary containing telemetry data.
        timestamp: Optional timestamp override.
        
    Returns:
        TelemetryResult object with processing results.
        
    Raises:
        ValueError: If session_id is invalid.
        ProcessingError: If data processing fails.
    """
    # Implementation here
    pass
```

#### Class Guidelines
```python
class TelemetryService:
    """Service for handling telemetry data collection and processing."""
    
    def __init__(self, config: ServiceConfig) -> None:
        """Initialize telemetry service.
        
        Args:
            config: Service configuration object.
        """
        self.config = config
        self._is_running = False
```

#### Error Handling
```python
# Use specific exception types
try:
    result = await process_data(data)
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise HTTPException(status_code=422, detail=str(e))
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    raise HTTPException(status_code=500, detail="Internal processing error")
```

### Frontend Code Style

#### JavaScript
- Use **ES6+** features
- Follow **Airbnb JavaScript Style Guide**
- Use **async/await** for asynchronous operations
- Include JSDoc comments for functions

#### CSS
- Use **BEM methodology** for class naming
- Follow **mobile-first** responsive design
- Use **CSS custom properties** for theming

### Database Guidelines

#### SQLAlchemy Models
```python
class Signal(Base):
    """Telemetry signal model."""
    
    __tablename__ = "signals"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    source: Mapped[str] = mapped_column(String(50), index=True)
    channel: Mapped[str] = mapped_column(String(100), index=True)
    ts_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    value_num: Mapped[Optional[float]] = mapped_column(Float)
    
    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="signals")
```

#### Migrations
- Use **descriptive names** for migration files
- Include **both upgrade and downgrade** functions
- Test migrations on **sample data**

## Testing Guidelines

### Test Structure
```
tests/
├── conftest.py           # Pytest configuration and fixtures
├── test_health.py        # Health endpoint tests
├── test_sessions.py      # Session management tests
├── test_export.py        # Export functionality tests
├── test_gps_service.py   # GPS service tests
├── test_obd_service.py   # OBD service tests
├── test_db_writer.py     # Database writer tests
├── test_packing.py       # Binary packing tests
└── test_websocket.py     # WebSocket tests
```

### Test Categories

#### Unit Tests
- Test individual functions and methods
- Mock external dependencies
- Focus on business logic

#### Integration Tests
- Test component interactions
- Use real database (in-memory SQLite)
- Test API endpoints end-to-end

#### Performance Tests
- Benchmark critical paths
- Test with large datasets
- Monitor memory usage

### Writing Tests

#### Test Function Structure
```python
async def test_create_session_success(client: TestClient) -> None:
    """Test successful session creation."""
    # Arrange
    session_data = {
        "name": "Test Session",
        "car_id": "CAR001",
        "driver": "Test Driver",
    }
    
    # Act
    response = client.post("/api/v1/sessions", json=session_data)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Session"
    assert data["car_id"] == "CAR001"
    assert "id" in data
    assert "created_utc" in data
```

#### Test Fixtures
```python
@pytest.fixture
async def test_session(async_db_session: AsyncSession) -> int:
    """Create a test session with sample data."""
    session = await session_crud.create(
        db=async_db_session,
        name="Test Session",
        car_id="TEST001",
    )
    return session.id
```

#### Running Tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_sessions.py -v

# Run with coverage
pytest --cov=backend --cov-report=html

# Run only fast tests
pytest -m "not slow"

# Run integration tests
pytest -m integration
```

### Test Requirements
- **Coverage**: Minimum 90% code coverage
- **Speed**: Unit tests should complete in <1 second
- **Isolation**: Tests should not depend on each other
- **Deterministic**: Tests should produce consistent results

## Pull Request Process

### 1. Before Submitting
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New functionality has tests
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] No merge conflicts

### 2. PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

### 3. Review Process
1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainers
3. **Testing** on different environments
4. **Documentation** review
5. **Approval** and merge

### 4. Commit Message Format
Use **Conventional Commits** format:
```
feat: add new telemetry data source
fix: resolve WebSocket connection issue
docs: update API documentation
test: add integration tests for export
refactor: improve database query performance
```

## Issue Reporting

### Bug Reports
When reporting bugs, please include:

1. **Environment Information**
   - Python version
   - Operating system
   - Cartelem version
   - Database type and version

2. **Steps to Reproduce**
   - Clear, numbered steps
   - Sample data if applicable
   - Expected vs actual behavior

3. **Error Information**
   - Full error messages
   - Stack traces
   - Log files (if applicable)

4. **Additional Context**
   - Screenshots (if UI related)
   - Related issues
   - Workarounds (if any)

### Feature Requests
When requesting features, please include:

1. **Problem Description**
   - What problem does this solve?
   - Who would benefit from this feature?

2. **Proposed Solution**
   - Detailed description of the feature
   - API changes (if applicable)
   - UI/UX considerations

3. **Alternatives Considered**
   - Other solutions you've considered
   - Why this approach is preferred

### Issue Templates
Use the provided GitHub issue templates for consistent reporting.

## Documentation

### Code Documentation
- **Docstrings**: Required for all public functions
- **Type hints**: Required for all function signatures
- **Comments**: Explain complex logic and business rules
- **README**: Keep project README up to date

### API Documentation
- **OpenAPI/Swagger**: Auto-generated from FastAPI
- **Examples**: Include usage examples
- **Error codes**: Document all possible error responses

### User Documentation
- **Installation guides**: Step-by-step setup instructions
- **Usage examples**: Common use cases and workflows
- **Troubleshooting**: Common issues and solutions

## Release Process

### Version Numbering
We use **Semantic Versioning** (SemVer):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist
- [ ] All tests pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] Release notes prepared
- [ ] GitHub release created
- [ ] PyPI package published (if applicable)

### Release Steps
1. **Create release branch** from main
2. **Update version** in pyproject.toml
3. **Update CHANGELOG.md** with release notes
4. **Create pull request** for release
5. **Merge and tag** release
6. **Create GitHub release** with notes
7. **Publish package** to PyPI (if applicable)

## Getting Help

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Pull Requests**: Code review and collaboration

### Resources
- **Documentation**: [Project Wiki](https://github.com/yourusername/cartelem/wiki)
- **API Reference**: [API Documentation](API.md)
- **Deployment Guide**: [Deployment Documentation](DEPLOYMENT.md)

### Code Review Guidelines
- **Be constructive**: Focus on improving the code
- **Be specific**: Point out exact issues and suggest fixes
- **Be respectful**: Maintain a positive tone
- **Be thorough**: Check for edge cases and potential issues

## Recognition

Contributors will be recognized in:
- **CONTRIBUTORS.md**: List of all contributors
- **Release notes**: Credit for significant contributions
- **GitHub**: Contributor statistics and activity

Thank you for contributing to Cartelem! Your efforts help make this project better for everyone.