/**
 * Cartelem Telemetry Dashboard - Main Application
 * Handles WebSocket connection, data processing, and UI updates
 */

class TelemetryApp {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.isConnected = false;
        this.dataBuffer = new Map();
        this.maxBufferSize = 1000;
        this.startTime = Date.now();
        this.telemetryRunning = false;
        this.currentSessionId = null;
        this.sessionStartTime = null;
        this.elapsedInterval = null;
        
        // Initialize components
        this.charts = null;
        this.map = null;
        
        // Bind methods
        this.connect = this.connect.bind(this);
        this.disconnect = this.disconnect.bind(this);
        this.handleMessage = this.handleMessage.bind(this);
        this.updateUI = this.updateUI.bind(this);
        this.startTelemetry = this.startTelemetry.bind(this);
        this.stopTelemetry = this.stopTelemetry.bind(this);
        this.updateTelemetryStatus = this.updateTelemetryStatus.bind(this);
        
        // Initialize the app
        this.init();
    }
    
    init() {
        console.log('Initializing Cartelem Telemetry Dashboard...');
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Initialize charts and map
        this.charts = new TelemetryCharts();
        this.map = new TelemetryMap();
        
        // Load available sessions
        this.loadSessions();
        
        // Check telemetry status
        this.checkTelemetryStatus();
        
        console.log('Dashboard initialized successfully');
    }
    
    setupEventListeners() {
        // Connection controls
        document.getElementById('connect-btn').addEventListener('click', this.connect);
        document.getElementById('disconnect-btn').addEventListener('click', this.disconnect);
        
        // Telemetry controls
        document.getElementById('start-telemetry-btn').addEventListener('click', this.startTelemetry);
        document.getElementById('stop-telemetry-btn').addEventListener('click', this.stopTelemetry);
        
        // Session selection
        document.getElementById('session-select').addEventListener('change', (e) => {
            this.sessionId = e.target.value;
        });
        
        // Chart range selection
        document.getElementById('chart-range').addEventListener('change', (e) => {
            const range = parseInt(e.target.value);
            this.charts.setTimeRange(range);
        });
        
        // Handle page unload
        window.addEventListener('beforeunload', () => {
            if (this.isConnected) {
                this.disconnect();
            }
        });
    }
    
    async loadSessions() {
        try {
            const response = await fetch('/api/v1/sessions');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const sessions = await response.json();
            const select = document.getElementById('session-select');
            
            // Clear existing options
            select.innerHTML = '<option value="">Select a session...</option>';
            
            // Add session options
            sessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session.id;
                option.textContent = `${session.name} (${session.car_id || 'Unknown'})`;
                select.appendChild(option);
            });
            
            console.log(`Loaded ${sessions.length} sessions`);
        } catch (error) {
            console.error('Failed to load sessions:', error);
            this.showError('Failed to load sessions. Please refresh the page.');
        }
    }
    
    async checkTelemetryStatus() {
        try {
            const response = await fetch('/api/v1/telemetry/status');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const status = await response.json();
            this.updateTelemetryUI(status);
            
        } catch (error) {
            console.error('Failed to check telemetry status:', error);
        }
    }
    
    async startTelemetry() {
        const startBtn = document.getElementById('start-telemetry-btn');
        const loading = startBtn.querySelector('.loading');
        
        // Show loading state
        startBtn.disabled = true;
        loading.style.display = 'inline-block';
        startBtn.textContent = 'Starting...';
        
        try {
            const response = await fetch('/api/v1/telemetry/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_name: `Session ${new Date().toLocaleString()}`
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            // Update UI state
            this.telemetryRunning = true;
            this.currentSessionId = result.session_id;
            this.sessionStartTime = new Date();
            
            this.updateTelemetryUI({
                is_running: true,
                session_id: result.session_id,
                session_name: result.session_name,
                start_time: this.sessionStartTime.toISOString()
            });
            
            // Start elapsed time counter
            this.startElapsedTimer();
            
            // Show success message
            this.showSuccess(`Telemetry started successfully! Session: ${result.session_name}`);
            
            // Refresh sessions list
            this.loadSessions();
            
        } catch (error) {
            console.error('Failed to start telemetry:', error);
            this.showError(`Failed to start telemetry: ${error.message}`);
        } finally {
            // Reset button state
            startBtn.disabled = false;
            loading.style.display = 'none';
            startBtn.textContent = 'Start Telemetry';
        }
    }
    
    async stopTelemetry() {
        const stopBtn = document.getElementById('stop-telemetry-btn');
        const loading = stopBtn.querySelector('.loading');
        
        // Show loading state
        stopBtn.disabled = true;
        loading.style.display = 'inline-block';
        stopBtn.textContent = 'Stopping...';
        
        try {
            const response = await fetch('/api/v1/telemetry/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            
            // Update UI state
            this.telemetryRunning = false;
            this.currentSessionId = null;
            this.sessionStartTime = null;
            
            this.updateTelemetryUI({
                is_running: false,
                session_id: null,
                session_name: null,
                start_time: null
            });
            
            // Stop elapsed time counter
            this.stopElapsedTimer();
            
            // Show success message
            this.showSuccess(`Telemetry stopped successfully! Session ${result.session_id} ended.`);
            
            // Refresh sessions list
            this.loadSessions();
            
        } catch (error) {
            console.error('Failed to stop telemetry:', error);
            this.showError(`Failed to stop telemetry: ${error.message}`);
        } finally {
            // Reset button state
            stopBtn.disabled = false;
            loading.style.display = 'none';
            stopBtn.textContent = 'Stop Telemetry';
        }
    }
    
    updateTelemetryUI(status) {
        const startBtn = document.getElementById('start-telemetry-btn');
        const stopBtn = document.getElementById('stop-telemetry-btn');
        const sessionIdDisplay = document.getElementById('session-id-display');
        const elapsedTimeDisplay = document.getElementById('elapsed-time-display');
        
        if (status.is_running) {
            // Telemetry is running
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
            
            sessionIdDisplay.textContent = `Session ${status.session_id}`;
            sessionIdDisplay.style.color = '#27ae60';
            
            if (status.start_time) {
                this.sessionStartTime = new Date(status.start_time);
                this.startElapsedTimer();
            }
            
        } else {
            // Telemetry is not running
            startBtn.style.display = 'inline-block';
            stopBtn.style.display = 'none';
            
            sessionIdDisplay.textContent = 'No active session';
            sessionIdDisplay.style.color = '#666';
            
            elapsedTimeDisplay.textContent = '';
            this.stopElapsedTimer();
        }
    }
    
    startElapsedTimer() {
        this.stopElapsedTimer(); // Clear any existing timer
        
        this.elapsedInterval = setInterval(() => {
            if (this.sessionStartTime) {
                const elapsed = Math.floor((Date.now() - this.sessionStartTime.getTime()) / 1000);
                const hours = Math.floor(elapsed / 3600);
                const minutes = Math.floor((elapsed % 3600) / 60);
                const seconds = elapsed % 60;
                
                const timeStr = hours > 0 
                    ? `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
                    : `${minutes}:${seconds.toString().padStart(2, '0')}`;
                
                document.getElementById('elapsed-time-display').textContent = timeStr;
            }
        }, 1000);
    }
    
    stopElapsedTimer() {
        if (this.elapsedInterval) {
            clearInterval(this.elapsedInterval);
            this.elapsedInterval = null;
        }
    }
    
    connect() {
        if (!this.sessionId) {
            this.showError('Please select a session first.');
            return;
        }
        
        if (this.isConnected) {
            console.log('Already connected');
            return;
        }
        
        console.log(`Connecting to session ${this.sessionId}...`);
        
        try {
            // Build WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/api/v1/ws?session_id=${this.sessionId}`;
            
            // Create WebSocket connection
            this.ws = new WebSocket(wsUrl);
            
            // Set up event handlers
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.updateConnectionStatus(true);
                this.startTime = Date.now();
            };
            
            this.ws.onmessage = this.handleMessage;
            
            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.isConnected = false;
                this.updateConnectionStatus(false);
                
                // Attempt to reconnect after 3 seconds if not manually disconnected
                if (event.code !== 1000) {
                    setTimeout(() => {
                        if (!this.isConnected) {
                            console.log('Attempting to reconnect...');
                            this.connect();
                        }
                    }, 3000);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.showError('Connection error. Please check your network.');
            };
            
        } catch (error) {
            console.error('Failed to connect:', error);
            this.showError('Failed to establish connection.');
        }
    }
    
    disconnect() {
        if (this.ws) {
            console.log('Disconnecting...');
            this.ws.close(1000, 'User disconnected');
            this.ws = null;
        }
        
        this.isConnected = false;
        this.updateConnectionStatus(false);
        this.sessionId = null;
        
        // Clear data
        this.dataBuffer.clear();
        this.charts.clear();
        this.map.clear();
        this.clearUI();
    }
    
    handleMessage(event) {
        try {
            const message = JSON.parse(event.data);
            
            switch (message.type) {
                case 'connection':
                    console.log('Connection message:', message);
                    break;
                    
                case 'telemetry_data':
                    this.processTelemetryData(message);
                    break;
                    
                case 'heartbeat':
                    // Update uptime
                    this.updateUptime();
                    break;
                    
                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    }
    
    processTelemetryData(message) {
        const { session_id, timestamp, data } = message;
        
        // Store data in buffer
        const key = `${data.source}_${data.pid || 'data'}`;
        if (!this.dataBuffer.has(key)) {
            this.dataBuffer.set(key, []);
        }
        
        const buffer = this.dataBuffer.get(key);
        buffer.push({
            timestamp: new Date(timestamp),
            value: data.value || data.data,
            unit: data.unit,
            quality: data.quality || 'good'
        });
        
        // Limit buffer size
        if (buffer.length > this.maxBufferSize) {
            buffer.shift();
        }
        
        // Update UI components
        this.updateUI(data);
        this.charts.updateData(key, buffer);
        
        // Update map if GPS data
        if (data.source === 'gps' && data.latitude && data.longitude) {
            this.map.updatePosition(data.latitude, data.longitude, data.altitude);
        }
    }
    
    updateUI(data) {
        const { source, pid, value, unit, quality } = data;
        
        // Update summary cards based on data source and type
        if (source === 'gps') {
            this.updateGPSCard(data);
        } else if (source === 'obd' && pid) {
            this.updateOBDCard(pid, value, unit, quality);
        } else if (source === 'meshtastic') {
            this.updateMeshtasticCard(data);
        }
    }
    
    updateGPSCard(data) {
        const fields = {
            'latitude': 'gps-latitude',
            'longitude': 'gps-longitude',
            'speed_kph': 'gps-speed',
            'satellites': 'gps-satellites'
        };
        
        Object.entries(fields).forEach(([field, elementId]) => {
            if (data[field] !== undefined) {
                this.updateMetric(elementId, data[field], data.unit || this.getUnit(field));
            }
        });
    }
    
    updateOBDCard(pid, value, unit, quality) {
        const pidMap = {
            'SPEED': 'obd-speed',
            'RPM': 'obd-rpm',
            'THROTTLE_POS': 'obd-throttle',
            'ENGINE_LOAD': 'obd-engine-load',
            'COOLANT_TEMP': 'obd-coolant-temp',
            'FUEL_LEVEL': 'obd-fuel-level',
            'INTAKE_TEMP': 'obd-intake-temp',
            'MAF': 'obd-maf'
        };
        
        const elementId = pidMap[pid];
        if (elementId) {
            this.updateMetric(elementId, value, unit, quality);
        }
    }
    
    updateMeshtasticCard(data) {
        if (data.frames_published !== undefined) {
            this.updateMetric('meshtastic-frames', data.frames_published, 'frames');
        }
        if (data.bytes_transmitted !== undefined) {
            this.updateMetric('meshtastic-bytes', data.bytes_transmitted, 'bytes');
        }
    }
    
    updateMetric(elementId, value, unit, quality = 'good') {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        // Format value
        let formattedValue = '--';
        if (value !== null && value !== undefined) {
            if (typeof value === 'number') {
                formattedValue = value.toFixed(1);
            } else {
                formattedValue = String(value);
            }
        }
        
        // Update value
        element.textContent = formattedValue;
        
        // Update quality class
        element.className = `value ${quality}`;
        
        // Add update animation
        element.classList.add('updated');
        setTimeout(() => {
            element.classList.remove('updated');
        }, 300);
        
        // Update unit if provided
        const unitElement = element.nextElementSibling;
        if (unitElement && unit) {
            unitElement.textContent = unit;
        }
    }
    
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        const sessionInfoElement = document.getElementById('session-info');
        const connectBtn = document.getElementById('connect-btn');
        const disconnectBtn = document.getElementById('disconnect-btn');
        const sessionSelect = document.getElementById('session-select');
        
        if (connected) {
            statusElement.textContent = 'Connected';
            statusElement.className = 'status-connected';
            sessionInfoElement.textContent = `Session: ${this.sessionId}`;
            connectBtn.disabled = true;
            disconnectBtn.disabled = false;
            sessionSelect.disabled = true;
        } else {
            statusElement.textContent = 'Disconnected';
            statusElement.className = 'status-disconnected';
            sessionInfoElement.textContent = '';
            connectBtn.disabled = false;
            disconnectBtn.disabled = true;
            sessionSelect.disabled = false;
        }
    }
    
    updateUptime() {
        const uptimeMs = Date.now() - this.startTime;
        const uptimeMinutes = Math.floor(uptimeMs / 60000);
        this.updateMetric('uptime', uptimeMinutes, 'min');
    }
    
    clearUI() {
        // Clear all metric values
        const metricElements = document.querySelectorAll('.metric .value');
        metricElements.forEach(element => {
            element.textContent = '--';
            element.className = 'value';
        });
        
        // Clear unit text
        const unitElements = document.querySelectorAll('.metric .unit');
        unitElements.forEach(element => {
            element.textContent = '';
        });
    }
    
    getUnit(field) {
        const units = {
            'latitude': '°N',
            'longitude': '°W',
            'speed_kph': 'km/h',
            'satellites': 'sats',
            'SPEED': 'km/h',
            'RPM': 'RPM',
            'THROTTLE_POS': '%',
            'ENGINE_LOAD': '%',
            'COOLANT_TEMP': '°C',
            'FUEL_LEVEL': '%',
            'INTAKE_TEMP': '°C',
            'MAF': 'g/s'
        };
        return units[field] || '';
    }
    
    showError(message) {
        console.error(message);
        // You could implement a toast notification system here
        alert(message);
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.telemetryApp = new TelemetryApp();
});
