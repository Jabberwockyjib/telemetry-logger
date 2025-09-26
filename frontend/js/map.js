/**
 * Cartelem Telemetry Dashboard - Map Module
 * Handles Leaflet live map for GPS track visualization
 */

class TelemetryMap {
    constructor() {
        this.map = null;
        this.trackLayer = null;
        this.markerLayer = null;
        this.currentPosition = null;
        this.trackPoints = [];
        this.maxTrackPoints = 1000;
        
        // Map configuration
        this.mapConfig = {
            center: [37.7749, -122.4194], // San Francisco default
            zoom: 13,
            minZoom: 3,
            maxZoom: 18
        };
        
        // Track styling
        this.trackStyle = {
            color: '#3498db',
            weight: 4,
            opacity: 0.8
        };
        
        // Marker styling
        this.markerConfig = {
            icon: null,
            popup: null
        };
        
        this.init();
    }
    
    init() {
        console.log('Initializing telemetry map...');
        
        // Create map
        this.createMap();
        
        // Create layers
        this.createLayers();
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('Map initialized successfully');
    }
    
    createMap() {
        const mapElement = document.getElementById('map');
        if (!mapElement) {
            console.error('Map element not found');
            return;
        }
        
        // Create Leaflet map
        this.map = L.map('map', {
            center: this.mapConfig.center,
            zoom: this.mapConfig.zoom,
            minZoom: this.mapConfig.minZoom,
            maxZoom: this.mapConfig.maxZoom,
            zoomControl: true,
            attributionControl: true
        });
        
        // Add tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19
        }).addTo(this.map);
        
        console.log('Map created successfully');
    }
    
    createLayers() {
        // Create track layer for GPS path
        this.trackLayer = L.layerGroup().addTo(this.map);
        
        // Create marker layer for current position
        this.markerLayer = L.layerGroup().addTo(this.map);
        
        // Create custom marker icon
        this.createMarkerIcon();
        
        console.log('Map layers created successfully');
    }
    
    createMarkerIcon() {
        // Create custom marker icon
        const markerHtml = `
            <div style="
                width: 20px;
                height: 20px;
                background: #e74c3c;
                border: 3px solid #fff;
                border-radius: 50%;
                box-shadow: 0 2px 10px rgba(0,0,0,0.3);
                animation: pulse 2s infinite;
            "></div>
            <style>
                @keyframes pulse {
                    0% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.2); opacity: 0.7; }
                    100% { transform: scale(1); opacity: 1; }
                }
            </style>
        `;
        
        this.markerConfig.icon = L.divIcon({
            html: markerHtml,
            className: 'custom-marker',
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });
        
        // Create popup template
        this.markerConfig.popup = `
            <div class="map-popup">
                <h4>Current Position</h4>
                <p><strong>Latitude:</strong> <span id="popup-lat">--</span></p>
                <p><strong>Longitude:</strong> <span id="popup-lon">--</span></p>
                <p><strong>Altitude:</strong> <span id="popup-alt">--</span> m</p>
                <p><strong>Speed:</strong> <span id="popup-speed">--</span> km/h</p>
                <p><strong>Heading:</strong> <span id="popup-heading">--</span>°</p>
                <p><strong>Satellites:</strong> <span id="popup-sats">--</span></p>
                <p><strong>Last Update:</strong> <span id="popup-time">--</span></p>
            </div>
        `;
    }
    
    setupEventListeners() {
        // Map click event
        this.map.on('click', (e) => {
            console.log('Map clicked at:', e.latlng);
        });
        
        // Map zoom event
        this.map.on('zoomend', () => {
            console.log('Map zoom level:', this.map.getZoom());
        });
        
        // Map move event
        this.map.on('moveend', () => {
            console.log('Map center:', this.map.getCenter());
        });
    }
    
    updatePosition(latitude, longitude, altitude = null) {
        if (!this.map) return;
        
        const latlng = [latitude, longitude];
        const timestamp = new Date().toLocaleTimeString();
        
        // Update current position
        this.currentPosition = {
            lat: latitude,
            lng: longitude,
            alt: altitude,
            timestamp: timestamp
        };
        
        // Add point to track
        this.addTrackPoint(latitude, longitude);
        
        // Update marker
        this.updateMarker(latitude, longitude, altitude);
        
        // Update popup content
        this.updatePopup(latitude, longitude, altitude, timestamp);
        
        // Auto-center map on first position
        if (this.trackPoints.length === 1) {
            this.map.setView(latlng, this.mapConfig.zoom);
        }
        
        console.log(`Position updated: ${latitude}, ${longitude}`);
    }
    
    addTrackPoint(latitude, longitude) {
        // Add point to track array
        this.trackPoints.push([latitude, longitude]);
        
        // Limit track points for performance
        if (this.trackPoints.length > this.maxTrackPoints) {
            this.trackPoints.shift();
        }
        
        // Update track layer
        this.updateTrackLayer();
    }
    
    updateTrackLayer() {
        if (!this.trackLayer || this.trackPoints.length < 2) return;
        
        // Clear existing track
        this.trackLayer.clearLayers();
        
        // Create polyline for track
        const polyline = L.polyline(this.trackPoints, this.trackStyle);
        
        // Add to track layer
        this.trackLayer.addLayer(polyline);
        
        // Fit map to track bounds
        if (this.trackPoints.length > 1) {
            const bounds = L.latLngBounds(this.trackPoints);
            this.map.fitBounds(bounds, { padding: [20, 20] });
        }
    }
    
    updateMarker(latitude, longitude, altitude) {
        if (!this.markerLayer) return;
        
        // Clear existing marker
        this.markerLayer.clearLayers();
        
        // Create new marker
        const marker = L.marker([latitude, longitude], {
            icon: this.markerConfig.icon
        });
        
        // Add popup
        marker.bindPopup(this.markerConfig.popup, {
            closeButton: true,
            autoClose: false,
            closeOnClick: false
        });
        
        // Add to marker layer
        this.markerLayer.addLayer(marker);
        
        // Open popup by default
        marker.openPopup();
    }
    
    updatePopup(latitude, longitude, altitude, timestamp) {
        // Update popup content if marker exists
        const marker = this.markerLayer.getLayers()[0];
        if (marker && marker.getPopup()) {
            const popup = marker.getPopup();
            const content = popup.getContent();
            
            // Update popup content with current data
            const updatedContent = content
                .replace(/<span id="popup-lat">[^<]*<\/span>/, `<span id="popup-lat">${latitude.toFixed(6)}</span>`)
                .replace(/<span id="popup-lon">[^<]*<\/span>/, `<span id="popup-lon">${longitude.toFixed(6)}</span>`)
                .replace(/<span id="popup-alt">[^<]*<\/span>/, `<span id="popup-alt">${altitude ? altitude.toFixed(1) : '--'}</span>`)
                .replace(/<span id="popup-time">[^<]*<\/span>/, `<span id="popup-time">${timestamp}</span>`);
            
            popup.setContent(updatedContent);
        }
    }
    
    clear() {
        console.log('Clearing map data...');
        
        // Clear track points
        this.trackPoints = [];
        
        // Clear layers
        if (this.trackLayer) {
            this.trackLayer.clearLayers();
        }
        
        if (this.markerLayer) {
            this.markerLayer.clearLayers();
        }
        
        // Reset current position
        this.currentPosition = null;
        
        // Reset map view
        if (this.map) {
            this.map.setView(this.mapConfig.center, this.mapConfig.zoom);
        }
        
        console.log('Map cleared successfully');
    }
    
    // Method to set map center
    setCenter(latitude, longitude, zoom = null) {
        if (!this.map) return;
        
        const targetZoom = zoom || this.map.getZoom();
        this.map.setView([latitude, longitude], targetZoom);
    }
    
    // Method to fit map to track
    fitToTrack() {
        if (!this.map || this.trackPoints.length < 2) return;
        
        const bounds = L.latLngBounds(this.trackPoints);
        this.map.fitBounds(bounds, { padding: [20, 20] });
    }
    
    // Method to get map statistics
    getMapStats() {
        return {
            trackPoints: this.trackPoints.length,
            currentPosition: this.currentPosition,
            mapCenter: this.map ? this.map.getCenter() : null,
            mapZoom: this.map ? this.map.getZoom() : null,
            bounds: this.map ? this.map.getBounds() : null
        };
    }
    
    // Method to export track data
    exportTrackData() {
        return {
            trackPoints: this.trackPoints.map(point => ({
                latitude: point[0],
                longitude: point[1]
            })),
            currentPosition: this.currentPosition,
            timestamp: new Date().toISOString()
        };
    }
    
    // Method to add custom markers
    addCustomMarker(latitude, longitude, options = {}) {
        if (!this.markerLayer) return null;
        
        const defaultOptions = {
            icon: this.markerConfig.icon,
            popup: 'Custom marker'
        };
        
        const markerOptions = { ...defaultOptions, ...options };
        const marker = L.marker([latitude, longitude], markerOptions);
        
        if (markerOptions.popup) {
            marker.bindPopup(markerOptions.popup);
        }
        
        this.markerLayer.addLayer(marker);
        return marker;
    }
    
    // Method to remove custom markers
    removeCustomMarker(marker) {
        if (marker && this.markerLayer) {
            this.markerLayer.removeLayer(marker);
        }
    }
}
