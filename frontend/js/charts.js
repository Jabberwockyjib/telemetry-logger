/**
 * Cartelem Telemetry Dashboard - Charts Module
 * Handles Chart.js rolling plots for telemetry data visualization
 */

class TelemetryCharts {
    constructor() {
        this.charts = new Map();
        this.timeRange = 300; // 5 minutes default
        this.maxDataPoints = 100;
        
        // Chart configurations
        this.chartConfigs = {
            'speed-rpm': {
                title: 'Speed & RPM',
                canvasId: 'speed-rpm-chart',
                datasets: [
                    {
                        label: 'Speed (km/h)',
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        yAxisID: 'y'
                    },
                    {
                        label: 'RPM',
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        yAxisID: 'y1'
                    }
                ]
            },
            'engine': {
                title: 'Engine Parameters',
                canvasId: 'engine-chart',
                datasets: [
                    {
                        label: 'Throttle (%)',
                        borderColor: '#f39c12',
                        backgroundColor: 'rgba(243, 156, 18, 0.1)',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Engine Load (%)',
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.1)',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Coolant Temp (°C)',
                        borderColor: '#e67e22',
                        backgroundColor: 'rgba(230, 126, 34, 0.1)',
                        yAxisID: 'y1'
                    }
                ]
            }
        };
        
        this.init();
    }
    
    init() {
        console.log('Initializing telemetry charts...');
        
        // Create charts
        this.createChart('speed-rpm');
        this.createChart('engine');
        
        console.log('Charts initialized successfully');
    }
    
    createChart(chartKey) {
        const config = this.chartConfigs[chartKey];
        const canvas = document.getElementById(config.canvasId);
        
        if (!canvas) {
            console.error(`Canvas element not found: ${config.canvasId}`);
            return;
        }
        
        const ctx = canvas.getContext('2d');
        
        const chartConfig = {
            type: 'line',
            data: {
                labels: [],
                datasets: config.datasets.map(dataset => ({
                    ...dataset,
                    data: [],
                    fill: false,
                    tension: 0.1,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#3498db',
                        borderWidth: 1,
                        callbacks: {
                            title: (context) => {
                                const date = new Date(context[0].label);
                                return date.toLocaleTimeString();
                            },
                            label: (context) => {
                                const dataset = context.dataset;
                                const value = context.parsed.y;
                                const unit = this.getUnitFromLabel(dataset.label);
                                return `${dataset.label}: ${value.toFixed(1)}${unit}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            displayFormats: {
                                second: 'HH:mm:ss',
                                minute: 'HH:mm'
                            }
                        },
                        title: {
                            display: true,
                            text: 'Time'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Speed (km/h) / Throttle (%) / Engine Load (%)'
                        },
                        grid: {
                            color: 'rgba(0, 0, 0, 0.1)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'RPM / Temperature (°C)'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                },
                animation: {
                    duration: 0 // Disable animation for real-time updates
                }
            }
        };
        
        const chart = new Chart(ctx, chartConfig);
        this.charts.set(chartKey, chart);
        
        console.log(`Created chart: ${chartKey}`);
    }
    
    updateData(dataKey, dataBuffer) {
        if (!dataBuffer || dataBuffer.length === 0) return;
        
        // Determine which chart to update based on data key
        let chartKey = null;
        let datasetIndex = -1;
        
        if (dataKey.includes('SPEED')) {
            chartKey = 'speed-rpm';
            datasetIndex = 0; // Speed dataset
        } else if (dataKey.includes('RPM')) {
            chartKey = 'speed-rpm';
            datasetIndex = 1; // RPM dataset
        } else if (dataKey.includes('THROTTLE_POS')) {
            chartKey = 'engine';
            datasetIndex = 0; // Throttle dataset
        } else if (dataKey.includes('ENGINE_LOAD')) {
            chartKey = 'engine';
            datasetIndex = 1; // Engine Load dataset
        } else if (dataKey.includes('COOLANT_TEMP')) {
            chartKey = 'engine';
            datasetIndex = 2; // Coolant Temp dataset
        }
        
        if (chartKey === null || datasetIndex === -1) return;
        
        const chart = this.charts.get(chartKey);
        if (!chart) return;
        
        // Filter data by time range
        const now = new Date();
        const cutoffTime = new Date(now.getTime() - this.timeRange * 1000);
        
        const filteredData = dataBuffer.filter(point => point.timestamp >= cutoffTime);
        
        if (filteredData.length === 0) return;
        
        // Update chart data
        const dataset = chart.data.datasets[datasetIndex];
        dataset.data = filteredData.map(point => ({
            x: point.timestamp,
            y: point.value
        }));
        
        // Update labels (timestamps)
        chart.data.labels = filteredData.map(point => point.timestamp);
        
        // Limit data points for performance
        if (dataset.data.length > this.maxDataPoints) {
            const excess = dataset.data.length - this.maxDataPoints;
            dataset.data.splice(0, excess);
            chart.data.labels.splice(0, excess);
        }
        
        // Update chart
        chart.update('none');
    }
    
    setTimeRange(seconds) {
        this.timeRange = seconds;
        console.log(`Chart time range set to ${seconds} seconds`);
        
        // Clear all charts to force data refresh
        this.charts.forEach(chart => {
            chart.data.datasets.forEach(dataset => {
                dataset.data = [];
            });
            chart.data.labels = [];
            chart.update('none');
        });
    }
    
    clear() {
        console.log('Clearing all charts...');
        
        this.charts.forEach(chart => {
            chart.data.datasets.forEach(dataset => {
                dataset.data = [];
            });
            chart.data.labels = [];
            chart.update('none');
        });
    }
    
    getUnitFromLabel(label) {
        const unitMap = {
            'Speed (km/h)': ' km/h',
            'RPM': ' RPM',
            'Throttle (%)': '%',
            'Engine Load (%)': '%',
            'Coolant Temp (°C)': '°C'
        };
        return unitMap[label] || '';
    }
    
    // Method to add new chart types dynamically
    addChart(chartKey, config) {
        this.chartConfigs[chartKey] = config;
        this.createChart(chartKey);
    }
    
    // Method to remove charts
    removeChart(chartKey) {
        const chart = this.charts.get(chartKey);
        if (chart) {
            chart.destroy();
            this.charts.delete(chartKey);
            delete this.chartConfigs[chartKey];
        }
    }
    
    // Method to get chart statistics
    getChartStats() {
        const stats = {};
        this.charts.forEach((chart, key) => {
            stats[key] = {
                datasets: chart.data.datasets.length,
                dataPoints: chart.data.datasets.reduce((total, dataset) => total + dataset.data.length, 0),
                timeRange: this.timeRange
            };
        });
        return stats;
    }
    
    // Method to export chart data
    exportChartData(chartKey) {
        const chart = this.charts.get(chartKey);
        if (!chart) return null;
        
        const exportData = {
            chartKey,
            timeRange: this.timeRange,
            datasets: chart.data.datasets.map(dataset => ({
                label: dataset.label,
                data: dataset.data.map(point => ({
                    timestamp: point.x,
                    value: point.y
                }))
            }))
        };
        
        return exportData;
    }
}
