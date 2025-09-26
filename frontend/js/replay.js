/**
 * Data replay functionality for historical telemetry visualization.
 */

class DataReplay {
    constructor() {
        this.currentSession = null;
        this.sessionData = [];
        this.currentTimeIndex = 0;
        this.isPlaying = false;
        this.playbackSpeed = 1.0;
        this.playbackInterval = null;
        
        // Chart instances
        this.speedRpmChart = null;
        this.engineChart = null;
        
        // Map instance
        this.replayMap = null;
        this.trackLayer = null;
        this.markerLayer = null;
        
        // UI elements
        this.sessionSelect = document.getElementById('sessionSelect');
        this.timeSlider = document.getElementById('timeSlider');
        this.timeDisplay = document.getElementById('timeDisplay');
        this.playPauseBtn = document.getElementById('playPauseBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.exportBtn = document.getElementById('exportBtn');
        this.sessionLoading = document.getElementById('sessionLoading');
        this.replayStats = document.getElementById('replayStats');
        
        this.initializeEventListeners();
        this.loadSessions();
        this.initializeCharts();
        this.initializeMap();
    }
    
    /**
     * Initialize event listeners for UI controls.
     */
    initializeEventListeners() {
        // Session selection
        this.sessionSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                this.loadSessionData(parseInt(e.target.value));
            } else {
                this.clearSession();
            }
        });
        
        // Time slider
        this.timeSlider.addEventListener('input', (e) => {
            if (this.sessionData.length > 0) {
                this.currentTimeIndex = Math.floor(
                    (parseInt(e.target.value) / 100) * (this.sessionData.length - 1)
                );
                this.updateDisplay();
            }
        });
        
        // Playback controls
        this.playPauseBtn.addEventListener('click', () => {
            this.togglePlayback();
        });
        
        this.resetBtn.addEventListener('click', () => {
            this.resetPlayback();
        });
        
        this.exportBtn.addEventListener('click', () => {
            this.exportData();
        });
    }
    
    /**
     * Load available sessions from the API.
     */
    async loadSessions() {
        try {
            this.sessionLoading.style.display = 'block';
            
            const response = await fetch('/api/v1/sessions');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const sessions = await response.json();
            
            // Clear existing options
            this.sessionSelect.innerHTML = '<option value="">Select a session...</option>';
            
            // Add session options
            sessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session.id;
                option.textContent = `${session.name} (${new Date(session.created_utc).toLocaleDateString()})`;
                this.sessionSelect.appendChild(option);
            });
            
        } catch (error) {
            console.error('Failed to load sessions:', error);
            this.showError('Failed to load sessions. Please try again.');
        } finally {
            this.sessionLoading.style.display = 'none';
        }
    }
    
    /**
     * Load session data for replay.
     */
    async loadSessionData(sessionId) {
        try {
            this.sessionLoading.style.display = 'block';
            this.currentSession = sessionId;
            
            // Load session details
            const sessionResponse = await fetch(`/api/v1/sessions/${sessionId}`);
            if (!sessionResponse.ok) {
                throw new Error(`Failed to load session: ${sessionResponse.statusText}`);
            }
            const session = await sessionResponse.json();
            
            // Load signals data
            const signalsResponse = await fetch(`/api/v1/sessions/${sessionId}/signals`);
            if (!signalsResponse.ok) {
                throw new Error(`Failed to load signals: ${signalsResponse.statusText}`);
            }
            const signals = await signalsResponse.json();
            
            // Process and sort data by timestamp
            this.sessionData = signals.sort((a, b) => 
                new Date(a.ts_utc) - new Date(b.ts_utc)
            );
            
            // Update UI
            this.updateSessionStats();
            this.initializePlayback();
            this.updateDisplay();
            
            // Enable controls
            this.timeSlider.disabled = false;
            this.playPauseBtn.disabled = false;
            this.resetBtn.disabled = false;
            this.exportBtn.disabled = false;
            
            this.replayStats.style.display = 'grid';
            
        } catch (error) {
            console.error('Failed to load session data:', error);
            this.showError('Failed to load session data. Please try again.');
        } finally {
            this.sessionLoading.style.display = 'none';
        }
    }
    
    /**
     * Update session statistics display.
     */
    updateSessionStats() {
        if (this.sessionData.length === 0) return;
        
        const startTime = new Date(this.sessionData[0].ts_utc);
        const endTime = new Date(this.sessionData[this.sessionData.length - 1].ts_utc);
        const duration = Math.round((endTime - startTime) / 1000);
        
        const sources = new Set(this.sessionData.map(s => s.source));
        const channels = new Set(this.sessionData.map(s => s.channel));
        
        document.getElementById('totalSignals').textContent = this.sessionData.length.toLocaleString();
        document.getElementById('duration').textContent = `${duration}s`;
        document.getElementById('dataSources').textContent = sources.size;
        document.getElementById('channels').textContent = channels.size;
    }
    
    /**
     * Initialize playback controls.
     */
    initializePlayback() {
        this.currentTimeIndex = 0;
        this.timeSlider.value = 0;
        this.timeSlider.max = 100;
        
        // Update charts with initial data
        this.updateCharts();
        this.updateMap();
    }
    
    /**
     * Toggle playback state.
     */
    togglePlayback() {
        if (this.isPlaying) {
            this.pausePlayback();
        } else {
            this.startPlayback();
        }
    }
    
    /**
     * Start playback.
     */
    startPlayback() {
        if (this.sessionData.length === 0) return;
        
        this.isPlaying = true;
        this.playPauseBtn.textContent = '⏸️ Pause';
        
        this.playbackInterval = setInterval(() => {
            if (this.currentTimeIndex < this.sessionData.length - 1) {
                this.currentTimeIndex++;
                this.updateTimeSlider();
                this.updateDisplay();
            } else {
                this.pausePlayback();
            }
        }, 100 / this.playbackSpeed); // Adjust speed
    }
    
    /**
     * Pause playback.
     */
    pausePlayback() {
        this.isPlaying = false;
        this.playPauseBtn.textContent = '▶️ Play';
        
        if (this.playbackInterval) {
            clearInterval(this.playbackInterval);
            this.playbackInterval = null;
        }
    }
    
    /**
     * Reset playback to beginning.
     */
    resetPlayback() {
        this.pausePlayback();
        this.currentTimeIndex = 0;
        this.updateTimeSlider();
        this.updateDisplay();
    }
    
    /**
     * Update time slider position.
     */
    updateTimeSlider() {
        if (this.sessionData.length > 0) {
            const progress = (this.currentTimeIndex / (this.sessionData.length - 1)) * 100;
            this.timeSlider.value = progress;
        }
    }
    
    /**
     * Update display with current data point.
     */
    updateDisplay() {
        if (this.sessionData.length === 0) {
            this.timeDisplay.textContent = 'No data';
            return;
        }
        
        const currentData = this.sessionData[this.currentTimeIndex];
        const timestamp = new Date(currentData.ts_utc);
        
        this.timeDisplay.textContent = `${timestamp.toLocaleTimeString()} (${this.currentTimeIndex + 1}/${this.sessionData.length})`;
        
        // Update summary cards
        this.updateSummaryCards(currentData);
        
        // Update charts
        this.updateCharts();
        
        // Update map
        this.updateMap();
    }
    
    /**
     * Update summary cards with current data.
     */
    updateSummaryCards(currentData) {
        // Group data by source and channel
        const dataByChannel = {};
        this.sessionData.slice(0, this.currentTimeIndex + 1).forEach(signal => {
            dataByChannel[signal.channel] = signal;
        });
        
        // Update GPS data
        const lat = dataByChannel['latitude']?.value_num;
        const lon = dataByChannel['longitude']?.value_num;
        const speed = dataByChannel['speed_kph']?.value_num;
        const heading = dataByChannel['heading_deg']?.value_num;
        
        document.getElementById('replayLat').textContent = lat ? lat.toFixed(6) : '--';
        document.getElementById('replayLon').textContent = lon ? lon.toFixed(6) : '--';
        document.getElementById('replaySpeed').textContent = speed ? `${speed.toFixed(1)} km/h` : '--';
        document.getElementById('replayHeading').textContent = heading ? `${heading.toFixed(1)}°` : '--';
        
        // Update vehicle data
        const rpm = dataByChannel['RPM']?.value_num;
        const throttle = dataByChannel['THROTTLE_POS']?.value_num;
        const engineLoad = dataByChannel['ENGINE_LOAD']?.value_num;
        const coolantTemp = dataByChannel['COOLANT_TEMP']?.value_num;
        
        document.getElementById('replayRpm').textContent = rpm ? `${Math.round(rpm)}` : '--';
        document.getElementById('replayThrottle').textContent = throttle ? `${throttle.toFixed(1)}%` : '--';
        document.getElementById('replayEngineLoad').textContent = engineLoad ? `${engineLoad.toFixed(1)}%` : '--';
        document.getElementById('replayCoolantTemp').textContent = coolantTemp ? `${coolantTemp.toFixed(1)}°C` : '--';
    }
    
    /**
     * Initialize Chart.js instances.
     */
    initializeCharts() {
        // Speed & RPM Chart
        const speedRpmCtx = document.getElementById('speedRpmChart').getContext('2d');
        this.speedRpmChart = new Chart(speedRpmCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Speed (km/h)',
                        data: [],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        yAxisID: 'y'
                    },
                    {
                        label: 'RPM',
                        data: [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                second: 'HH:mm:ss'
                            }
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Speed (km/h)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'RPM'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    }
                }
            }
        });
        
        // Engine Parameters Chart
        const engineCtx = document.getElementById('engineChart').getContext('2d');
        this.engineChart = new Chart(engineCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Throttle (%)',
                        data: [],
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243, 156, 18, 0.1)'
                    },
                    {
                        label: 'Engine Load (%)',
                        data: [],
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.1)'
                    },
                    {
                        label: 'Coolant Temp (°C)',
                        data: [],
                        borderColor: '#1abc9c',
                        backgroundColor: 'rgba(26, 188, 156, 0.1)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                second: 'HH:mm:ss'
                            }
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Value'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true
                    }
                }
            }
        });
    }
    
    /**
     * Update charts with current data.
     */
    updateCharts() {
        if (this.sessionData.length === 0) return;
        
        // Get data up to current time index
        const currentData = this.sessionData.slice(0, this.currentTimeIndex + 1);
        
        // Group data by channel
        const dataByChannel = {};
        currentData.forEach(signal => {
            if (!dataByChannel[signal.channel]) {
                dataByChannel[signal.channel] = [];
            }
            dataByChannel[signal.channel].push({
                x: new Date(signal.ts_utc),
                y: signal.value_num
            });
        });
        
        // Update Speed & RPM Chart
        this.speedRpmChart.data.labels = currentData.map(s => new Date(s.ts_utc));
        this.speedRpmChart.data.datasets[0].data = dataByChannel['speed_kph'] || [];
        this.speedRpmChart.data.datasets[1].data = dataByChannel['RPM'] || [];
        this.speedRpmChart.update('none');
        
        // Update Engine Chart
        this.engineChart.data.labels = currentData.map(s => new Date(s.ts_utc));
        this.engineChart.data.datasets[0].data = dataByChannel['THROTTLE_POS'] || [];
        this.engineChart.data.datasets[1].data = dataByChannel['ENGINE_LOAD'] || [];
        this.engineChart.data.datasets[2].data = dataByChannel['COOLANT_TEMP'] || [];
        this.engineChart.update('none');
    }
    
    /**
     * Initialize Leaflet map.
     */
    initializeMap() {
        this.replayMap = L.map('replayMap').setView([37.7749, -122.4194], 13);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(this.replayMap);
        
        // Create layers for track and marker
        this.trackLayer = L.layerGroup().addTo(this.replayMap);
        this.markerLayer = L.layerGroup().addTo(this.replayMap);
    }
    
    /**
     * Update map with current data.
     */
    updateMap() {
        if (this.sessionData.length === 0) return;
        
        // Clear existing layers
        this.trackLayer.clearLayers();
        this.markerLayer.clearLayers();
        
        // Get GPS data up to current time index
        const gpsData = this.sessionData
            .slice(0, this.currentTimeIndex + 1)
            .filter(s => s.source === 'gps' && s.channel === 'latitude')
            .map(signal => {
                const lat = signal.value_num;
                const lonSignal = this.sessionData.find(s => 
                    s.ts_utc === signal.ts_utc && 
                    s.source === 'gps' && 
                    s.channel === 'longitude'
                );
                const lon = lonSignal?.value_num;
                
                if (lat && lon) {
                    return [lat, lon];
                }
                return null;
            })
            .filter(coord => coord !== null);
        
        if (gpsData.length > 0) {
            // Draw track line
            if (gpsData.length > 1) {
                const trackLine = L.polyline(gpsData, {
                    color: '#3498db',
                    weight: 3,
                    opacity: 0.7
                });
                this.trackLayer.addLayer(trackLine);
            }
            
            // Add current position marker
            const currentPos = gpsData[gpsData.length - 1];
            const marker = L.circleMarker(currentPos, {
                radius: 8,
                fillColor: '#e74c3c',
                color: '#c0392b',
                weight: 2,
                opacity: 1,
                fillOpacity: 0.8
            });
            
            // Add popup with current data
            const currentData = this.sessionData[this.currentTimeIndex];
            const timestamp = new Date(currentData.ts_utc);
            marker.bindPopup(`
                <strong>Position</strong><br>
                Time: ${timestamp.toLocaleTimeString()}<br>
                Lat: ${currentPos[0].toFixed(6)}<br>
                Lon: ${currentPos[1].toFixed(6)}
            `);
            
            this.markerLayer.addLayer(marker);
            
            // Fit map to track
            if (gpsData.length > 1) {
                this.replayMap.fitBounds(gpsData);
            } else {
                this.replayMap.setView(currentPos, 15);
            }
        }
    }
    
    /**
     * Export current session data.
     */
    async exportData() {
        if (!this.currentSession) return;
        
        try {
            // Export as CSV
            const response = await fetch(`/api/v1/export/sessions/${this.currentSession}/signals.csv`);
            if (!response.ok) {
                throw new Error(`Export failed: ${response.statusText}`);
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `session_${this.currentSession}_signals.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
        } catch (error) {
            console.error('Export failed:', error);
            this.showError('Export failed. Please try again.');
        }
    }
    
    /**
     * Clear current session data.
     */
    clearSession() {
        this.pausePlayback();
        this.currentSession = null;
        this.sessionData = [];
        this.currentTimeIndex = 0;
        
        // Reset UI
        this.timeSlider.disabled = true;
        this.timeSlider.value = 0;
        this.playPauseBtn.disabled = true;
        this.resetBtn.disabled = true;
        this.exportBtn.disabled = true;
        this.timeDisplay.textContent = 'No session selected';
        this.replayStats.style.display = 'none';
        
        // Clear charts
        if (this.speedRpmChart) {
            this.speedRpmChart.data.labels = [];
            this.speedRpmChart.data.datasets.forEach(dataset => dataset.data = []);
            this.speedRpmChart.update();
        }
        
        if (this.engineChart) {
            this.engineChart.data.labels = [];
            this.engineChart.data.datasets.forEach(dataset => dataset.data = []);
            this.engineChart.update();
        }
        
        // Clear map
        if (this.trackLayer) this.trackLayer.clearLayers();
        if (this.markerLayer) this.markerLayer.clearLayers();
        
        // Clear summary cards
        const summaryElements = [
            'replayLat', 'replayLon', 'replaySpeed', 'replayHeading',
            'replayRpm', 'replayThrottle', 'replayEngineLoad', 'replayCoolantTemp'
        ];
        summaryElements.forEach(id => {
            document.getElementById(id).textContent = '--';
        });
    }
    
    /**
     * Show error message to user.
     */
    showError(message) {
        // Simple error display - could be enhanced with a proper notification system
        alert(`Error: ${message}`);
    }
}

// Initialize replay when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DataReplay();
});
