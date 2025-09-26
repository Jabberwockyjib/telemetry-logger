# Cartelem Telemetry Dashboard

A real-time telemetry dashboard for the Cartelem project, providing live visualization of GPS, OBD-II, and Meshtastic data through WebSocket connections.

## Features

- **Real-time Data Visualization**: Live charts and maps updated via WebSocket
- **GPS Tracking**: Interactive map with live position updates and track recording
- **OBD-II Data**: Rolling plots for vehicle parameters (speed, RPM, throttle, etc.)
- **Summary Cards**: Key metrics displayed in clean, organized cards
- **Responsive Design**: Works on desktop and mobile devices
- **Minimal UI**: Clean, modern interface focused on data clarity

## Quick Start

### Prerequisites

- Modern web browser with WebSocket support
- Cartelem backend server running
- Active telemetry session

### Installation

1. **Clone or download** the frontend files to your web server
2. **Ensure dependencies** are accessible:
   - Chart.js (via CDN)
   - Leaflet (via CDN)
3. **Configure backend URL** if different from default

### Usage

1. **Open** `index.html` in your web browser
2. **Select a session** from the dropdown menu
3. **Click "Connect"** to establish WebSocket connection
4. **View live data** in charts, map, and summary cards

## File Structure

```
frontend/
├── index.html          # Main HTML page
├── css/
│   └── styles.css      # Styling and responsive design
├── js/
│   ├── app.js          # Main application logic and WebSocket handling
│   ├── charts.js       # Chart.js integration for rolling plots
│   └── map.js          # Leaflet integration for live map
└── README.md           # This file
```

## Components

### Summary Cards
- **GPS Status**: Latitude, longitude, speed, satellite count
- **Vehicle Status**: OBD speed, RPM, throttle position, engine load
- **Engine Status**: Coolant temperature, fuel level, intake temperature, MAF
- **System Status**: Meshtastic frames, bytes transmitted, database signals, uptime

### Charts
- **Speed & RPM**: Dual-axis chart showing vehicle speed and engine RPM
- **Engine Parameters**: Throttle position, engine load, and coolant temperature
- **Configurable Time Range**: 1, 5, 10, or 30 minutes
- **Real-time Updates**: Smooth rolling plots with data point limiting

### Live Map
- **GPS Tracking**: Real-time position updates with animated marker
- **Track Recording**: Continuous path recording with configurable point limit
- **Interactive Popup**: Detailed position information on marker click
- **Auto-centering**: Automatically fits map to track bounds

## Configuration

### WebSocket Connection
The dashboard connects to the backend WebSocket endpoint:
```
ws://localhost:8000/ws?session_id={SESSION_ID}
```

### Chart Configuration
- **Time Range**: Configurable via dropdown (1-30 minutes)
- **Data Points**: Limited to 1000 points per dataset for performance
- **Update Rate**: Real-time updates with smooth animations

### Map Configuration
- **Default Center**: San Francisco (37.7749, -122.4194)
- **Zoom Levels**: 3-18 with appropriate controls
- **Track Points**: Limited to 1000 points for performance
- **Tile Provider**: OpenStreetMap (configurable)

## Data Sources

### GPS Data
- Latitude/longitude coordinates
- Altitude and speed
- Heading and satellite count
- HDOP (Horizontal Dilution of Precision)

### OBD-II Data
- Vehicle speed and RPM
- Throttle position and engine load
- Coolant and intake temperatures
- Fuel level and MAF (Mass Air Flow)
- Timing advance and fuel pressure

### Meshtastic Data
- Frame transmission statistics
- Bytes transmitted
- Error counts and status

## Browser Compatibility

- **Chrome**: 60+ (recommended)
- **Firefox**: 55+
- **Safari**: 12+
- **Edge**: 79+

## Performance Considerations

- **Data Limiting**: Charts and maps limit data points for smooth performance
- **Update Throttling**: Real-time updates optimized for 1-10 Hz data rates
- **Memory Management**: Automatic cleanup of old data points
- **Responsive Design**: Optimized for various screen sizes

## Troubleshooting

### Connection Issues
- **Check backend server**: Ensure Cartelem backend is running
- **Verify session**: Select an active session from dropdown
- **Network connectivity**: Check WebSocket connection in browser dev tools
- **CORS issues**: Ensure proper CORS configuration on backend

### Display Issues
- **Chart not updating**: Check WebSocket data flow and console errors
- **Map not loading**: Verify Leaflet CDN accessibility
- **Styling problems**: Check CSS file loading and browser compatibility

### Performance Issues
- **Slow updates**: Reduce chart time range or data point limits
- **High memory usage**: Check for memory leaks in browser dev tools
- **Mobile performance**: Use responsive design features

## Development

### Adding New Charts
1. **Define chart config** in `charts.js`
2. **Add canvas element** to `index.html`
3. **Update data mapping** in `app.js`
4. **Test with real data** from WebSocket

### Adding New Map Features
1. **Extend map class** in `map.js`
2. **Add new layers** or markers as needed
3. **Update event handlers** for interactivity
4. **Test with GPS data** from WebSocket

### Customizing Styling
1. **Modify CSS variables** in `styles.css`
2. **Update color schemes** for charts and maps
3. **Adjust responsive breakpoints** for mobile
4. **Test across browsers** and devices

## API Reference

### WebSocket Messages
```javascript
// Connection message
{
  "type": "connection",
  "session_id": 123,
  "timestamp": "2024-01-01T12:00:00Z"
}

// Telemetry data
{
  "type": "telemetry_data",
  "session_id": 123,
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "source": "gps",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "speed_kph": 65.0
  }
}

// Heartbeat
{
  "type": "heartbeat",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Chart Data Format
```javascript
{
  "timestamp": "2024-01-01T12:00:00Z",
  "value": 65.0,
  "unit": "km/h",
  "quality": "good"
}
```

### Map Data Format
```javascript
{
  "latitude": 37.7749,
  "longitude": -122.4194,
  "altitude": 10.5,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## License

This project is part of the Cartelem telemetry system. See the main project license for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review browser console for error messages
3. Verify backend server status and logs
4. Check WebSocket connection in browser dev tools
