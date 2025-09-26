# PR: feat: implement CSV/Parquet export endpoints and data replay page

## Summary

This PR adds comprehensive data export functionality and a historical data replay page to the Cartelem telemetry system. Users can now export telemetry data in CSV and Parquet formats with configurable filters, and replay historical sessions with interactive time navigation.

## Features Added

### Export Endpoints (`/api/v1/export/`)
- **CSV Export**: Streaming CSV export for signals and frames
- **Parquet Export**: Binary streaming for large datasets with pandas/pyarrow
- **Filtering**: Time range, source, and channel filtering
- **Pagination**: Efficient processing of large datasets
- **Auto-naming**: Timestamped filenames for downloads

### Data Replay Page (`frontend/replay.html`)
- **Session Selection**: Dropdown with automatic data loading
- **Time Scrubber**: Interactive timeline with play/pause controls
- **Statistics Display**: Real-time session metrics
- **Chart Visualization**: Historical data plots with Chart.js
- **GPS Track Replay**: Interactive map with Leaflet
- **Export Integration**: Direct download from replay interface

### Enhanced Database Layer
- **Pagination Support**: New CRUD methods for efficient data retrieval
- **Query Optimization**: Batch processing for large datasets
- **Filter Support**: Time range and field-based filtering

## Technical Implementation

### Backend Changes
- `backend/app/api/routes_export.py`: New export API endpoints
- `backend/app/db/crud.py`: Enhanced with pagination methods
- `backend/app/main.py`: Integrated export routes
- `pyproject.toml`: Added pandas and pyarrow dependencies

### Frontend Changes
- `frontend/replay.html`: Complete replay interface
- `frontend/js/replay.js`: Replay functionality with time navigation
- `frontend/css/styles.css`: Enhanced styling for replay controls

### Testing
- `tests/test_export.py`: Comprehensive test suite (12 test cases)
- Streaming performance validation
- Error handling and edge case testing
- Filter validation and parameter testing

## API Endpoints

### Export Endpoints
- `GET /api/v1/export/sessions/{id}/signals.csv` - Export signals as CSV
- `GET /api/v1/export/sessions/{id}/signals.parquet` - Export signals as Parquet
- `GET /api/v1/export/sessions/{id}/frames.csv` - Export frames as CSV

### Query Parameters
- `start_time`: ISO datetime for filtering start
- `end_time`: ISO datetime for filtering end
- `sources`: Array of source names to filter
- `channels`: Array of channel names to filter

## Usage Examples

### CSV Export with Filters
```bash
curl "http://localhost:8000/api/v1/export/sessions/1/signals.csv?sources=gps&channels=latitude,longitude"
```

### Parquet Export with Time Range
```bash
curl "http://localhost:8000/api/v1/export/sessions/1/signals.parquet?start_time=2024-01-01T00:00:00Z&end_time=2024-01-01T23:59:59Z"
```

### Replay Page Access
Open `http://localhost:8000/replay.html` in browser for interactive data replay.

## Performance Characteristics

- **Streaming**: All exports use streaming responses for memory efficiency
- **Pagination**: 1000-row batches for optimal performance
- **Large Datasets**: Tested with 1000+ signals, sub-second response times
- **Memory Usage**: Minimal memory footprint due to streaming architecture

## Error Handling

- **404**: Session not found
- **422**: Invalid parameters (time format, session ID)
- **500**: Internal server errors with detailed logging
- **Graceful Degradation**: Parquet falls back to CSV if libraries unavailable

## Browser Compatibility

- **Modern Browsers**: Chrome, Firefox, Safari, Edge
- **Mobile Support**: Touch-friendly replay controls
- **Responsive Design**: Adapts to different screen sizes

## Dependencies Added

- `pandas>=2.0.0`: Data manipulation for Parquet export
- `pyarrow>=12.0.0`: Binary format support for Parquet

## Testing Status

✅ All 12 export tests passing
✅ Streaming performance validated
✅ Error handling comprehensive
✅ Filter functionality tested
✅ Large dataset pagination verified

## CHANGELOG Updated

- Added comprehensive documentation for new export and replay features
- Updated technical details and API documentation
- Enhanced change tracking for future reference

## Breaking Changes

None - all changes are additive and backward compatible.

## Migration Notes

No database migrations required - uses existing schema with enhanced query methods.

## Future Enhancements

- Real-time export progress indicators
- Custom export templates
- Scheduled export jobs
- Advanced filtering UI
- Export format validation

---

**Conventional Commits**: `feat: implement CSV/Parquet export endpoints and data replay page`

**Type**: Feature
**Scope**: Export, Replay, Frontend
**Breaking Change**: No
