# Cartelem User Setup Guide

## 🚀 Quick Start

This guide will help you set up Cartelem for telemetry data collection from your vehicle and sensors.

## 📋 Prerequisites

### Required Equipment
- **Computer**: Windows, macOS, or Linux with Python 3.9+
- **OBD-II Adapter**: ELM327-based USB adapter
- **Vehicle**: 1996+ vehicle with OBD-II port

### Optional Equipment
- **GPS Device**: NMEA-compatible GPS with serial output
- **Meshtastic Device**: For radio telemetry transmission
- **Network**: Internet connection for remote access

## ⚙️ Installation

### 1. Download and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/cartelem.git
cd cartelem

# Install Python dependencies
pip install -r requirements.txt

# Initialize the database
alembic upgrade head
```

### 2. Hardware Setup

#### OBD-II Adapter
1. **Locate OBD Port**: Usually under the dashboard, driver's side
2. **Connect Adapter**: Plug ELM327 adapter into OBD port
3. **Connect to Computer**: Use USB cable to connect adapter
4. **Note Port Path**: 
   - Linux: `/dev/ttyUSB0` (check with `ls /dev/tty*`)
   - Windows: `COM3` (check Device Manager)
   - macOS: `/dev/cu.usbserial-*`

#### GPS Device (Optional)
1. **Connect GPS**: Use USB or serial connection
2. **Configure NMEA**: Ensure device outputs NMEA 0183
3. **Note Settings**: Port path and baud rate (typically 4800)

#### Meshtastic Device (Optional)
1. **Connect Device**: Use USB connection
2. **Configure Radio**: Set frequency, power, and telemetry mode
3. **Test Connection**: Verify device responds to commands

### 3. Configuration

#### Create Environment File
```bash
# Copy the example configuration
cp env.example .env

# Edit the configuration
nano .env  # or use your preferred editor
```

#### Basic Configuration
```env
# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./cartelem.db

# GPS Configuration
GPS_PORT=/dev/ttyUSB0
GPS_BAUDRATE=4800
GPS_RATE_HZ=10

# OBD Configuration
OBD_PORT=/dev/ttyUSB1
OBD_BAUDRATE=38400
OBD_RATE_HZ=5

# Application Settings
DEBUG=true
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

#### Port Detection
```bash
# Linux/macOS - List serial ports
ls /dev/tty*

# Windows - Check Device Manager for COM ports
# Look for "Ports (COM & LPT)" section
```

## 🚀 Running Cartelem

### Start the Application
```bash
# Development mode with auto-reload
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Access the Dashboard
Open your web browser and navigate to:
- **Local**: http://localhost:8000
- **Network**: http://YOUR_IP_ADDRESS:8000

## 📊 Using Cartelem

### 1. Create a Session
1. Open the **Live Dashboard**
2. Click **"Create New Session"**
3. Enter session details:
   - Session name (e.g., "Track Day 1")
   - Car ID (e.g., "CAR001")
   - Driver name
   - Track/location
4. Click **"Create Session"**

### 2. Start Data Collection
1. Select your session from the dropdown
2. Click **"Start Session"**
3. Verify data is flowing:
   - GPS coordinates updating on map
   - Charts showing real-time data
   - Status indicators showing "Connected"

### 3. Monitor Real-time Data
- **GPS Map**: Real-time position tracking
- **Speed/RPM Chart**: Engine performance data
- **Engine Parameters**: Temperature, load, throttle
- **Status Cards**: Connection status for each service

### 4. Stop and Export Data
1. Click **"Stop Session"** when complete
2. Navigate to **"Data Replay"** page
3. Select your session
4. Use time scrubber to review data
5. Click **"Export CSV"** or **"Export Parquet"**

## 🔧 Troubleshooting

### Common Issues

#### OBD-II Adapter Not Detected
**Symptoms**: OBD service shows "Not Connected"
**Solutions**:
- Check USB connection and try different port
- Verify adapter compatibility with your vehicle
- Update port path in configuration
- Test with different OBD-II adapter

#### GPS Device Not Responding
**Symptoms**: GPS service shows "Not Connected" or no position
**Solutions**:
- Ensure GPS has clear sky view
- Check baud rate configuration
- Verify NMEA output is enabled
- Test with different GPS device

#### WebSocket Connection Issues
**Symptoms**: Dashboard shows "Disconnected"
**Solutions**:
- Refresh the web page
- Check if server is running
- Verify firewall settings
- Try different browser

### Diagnostic Commands

#### Check Serial Ports
```bash
# Linux/macOS
ls /dev/tty*

# Windows
# Use Device Manager to check COM ports
```

#### Test Serial Communication
```bash
# Test GPS device
python -c "import serial; s=serial.Serial('/dev/ttyUSB0', 4800); print(s.readline())"

# Test OBD device
python -c "import serial; s=serial.Serial('/dev/ttyUSB1', 38400); s.write(b'ATZ\r'); print(s.readline())"
```

#### Check Application Logs
```bash
# View application logs
tail -f logs/cartelem.log

# Check system resources
top
htop
```

## 📱 Mobile Access

### Local Network Access
1. Find your computer's IP address
2. Access from mobile device: `http://YOUR_IP:8000`
3. Bookmark for easy access

### Remote Access (Advanced)
1. Configure port forwarding on router
2. Set up dynamic DNS service
3. Configure SSL certificates
4. Access via domain name

## 🔒 Security Considerations

### Development
- Default configuration is suitable for local development
- No authentication required
- All data stored locally

### Production
- Enable authentication
- Use HTTPS with SSL certificates
- Configure firewall rules
- Regular database backups
- Monitor system resources

## 📈 Performance Optimization

### System Requirements
- **Minimum**: 4GB RAM, 10GB storage
- **Recommended**: 8GB+ RAM, SSD storage
- **Network**: Stable connection for remote access

### Optimization Tips
- Use SSD storage for better database performance
- Close unnecessary applications
- Monitor system resources
- Regular database maintenance

## 🆘 Getting Help

### Documentation
- **User Guide**: This document
- **API Documentation**: http://localhost:8000/docs
- **Deployment Guide**: See DEPLOYMENT.md

### Community Support
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Community questions
- **Wiki**: Community-maintained documentation

### Professional Support
- **Custom Development**: Tailored solutions
- **Integration Services**: Hardware integration help
- **Training**: On-site or remote training

## 📝 Configuration Reference

### Environment Variables
See `env.example` for complete configuration options including:
- Database settings
- Hardware configuration
- Performance tuning
- Security settings
- Monitoring options

### OBD PID Configuration
Default PIDs collected:
- **SPEED**: Vehicle speed (10 Hz)
- **RPM**: Engine RPM (10 Hz)
- **THROTTLE_POS**: Throttle position (5 Hz)
- **COOLANT_TEMP**: Coolant temperature (2 Hz)
- **ENGINE_LOAD**: Engine load (5 Hz)

### GPS Configuration
Supported NMEA sentences:
- **GGA**: Global Positioning System Fix Data
- **RMC**: Recommended Minimum Navigation Information
- **VTG**: Track Made Good and Ground Speed

## 🎯 Use Cases

### Track Day Data Collection
- Monitor engine performance
- Track lap times and speeds
- Analyze driving patterns
- Export data for analysis

### Fleet Management
- Monitor multiple vehicles
- Track fuel efficiency
- Monitor driver behavior
- Generate reports

### Research and Development
- Test new sensors
- Validate algorithms
- Performance benchmarking
- Data analysis

### Hobby and Education
- Learn about telemetry
- Experiment with sensors
- Build custom dashboards
- Share data with community

## 🔄 Updates and Maintenance

### Regular Maintenance
- Update Python dependencies
- Backup database regularly
- Monitor system performance
- Check for security updates

### Upgrading Cartelem
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Restart application
```

### Data Backup
```bash
# Backup SQLite database
cp cartelem.db backup_$(date +%Y%m%d).db

# Backup with compression
tar -czf backup_$(date +%Y%m%d).tar.gz cartelem.db
```

## 📊 Data Export and Analysis

### Supported Formats
- **CSV**: Comma-separated values for Excel/Google Sheets
- **Parquet**: Efficient binary format for data analysis
- **JSON**: Structured data for programming

### Analysis Tools
- **Excel/Google Sheets**: Basic analysis and visualization
- **Python**: pandas, matplotlib, seaborn
- **R**: Statistical analysis and visualization
- **Tableau**: Advanced data visualization

### Sample Analysis
```python
import pandas as pd
import matplotlib.pyplot as plt

# Load exported data
df = pd.read_csv('session_data.csv')

# Plot speed over time
plt.plot(df['ts_utc'], df['value_num'])
plt.title('Speed Over Time')
plt.xlabel('Time')
plt.ylabel('Speed (kph)')
plt.show()
```

## 🎉 Success!

You're now ready to start collecting telemetry data with Cartelem! 

For additional help, visit the [Documentation](docs.html) page or check the [GitHub repository](https://github.com/yourusername/cartelem) for updates and community support.

Happy telemetry collecting! 🚗📊
