/**
 * Device Setup Wizard JavaScript
 * Handles the multi-step device configuration process
 */

class SetupWizard {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 4;
        this.selectedProfile = null;
        this.deviceConfigs = {
            gps: { enabled: false, config: {} },
            obd: { enabled: false, config: {} },
            meshtastic: { enabled: false, config: {} }
        };
        this.testResults = {};
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadProfiles();
        this.loadAvailablePorts();
        this.updateStepDisplay();
    }
    
    bindEvents() {
        // Step navigation
        document.getElementById('prev-btn').addEventListener('click', () => this.previousStep());
        document.getElementById('next-btn').addEventListener('click', () => this.nextStep());
        document.getElementById('complete-btn').addEventListener('click', () => this.completeSetup());
        
        // Profile action selection
        document.querySelectorAll('input[name="profile-action"]').forEach(radio => {
            radio.addEventListener('change', (e) => this.toggleProfileAction(e.target.value));
        });
        
        // Device configuration toggles
        document.getElementById('gps-enabled').addEventListener('change', (e) => this.toggleDeviceConfig('gps', e.target.checked));
        document.getElementById('obd-enabled').addEventListener('change', (e) => this.toggleDeviceConfig('obd', e.target.checked));
        document.getElementById('meshtastic-enabled').addEventListener('change', (e) => this.toggleDeviceConfig('meshtastic', e.target.checked));
        
        // Test button
        document.getElementById('start-test').addEventListener('click', () => this.startDeviceTest());
        
        // Step indicators
        document.querySelectorAll('.step').forEach(step => {
            step.addEventListener('click', (e) => {
                const stepNumber = parseInt(e.currentTarget.dataset.step);
                if (stepNumber <= this.currentStep || this.isStepCompleted(stepNumber)) {
                    this.goToStep(stepNumber);
                }
            });
        });
    }
    
    async loadProfiles() {
        try {
            const response = await fetch('/api/v1/setup/profiles');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const profiles = await response.json();
            this.renderProfiles(profiles);
        } catch (error) {
            console.error('Error loading profiles:', error);
            this.showError('Failed to load device profiles');
        }
    }
    
    renderProfiles(profiles) {
        const profileList = document.getElementById('profile-list');
        profileList.innerHTML = '';
        
        if (profiles.length === 0) {
            profileList.innerHTML = '<p>No profiles found. Create a new profile to get started.</p>';
            return;
        }
        
        profiles.forEach(profile => {
            const profileCard = document.createElement('div');
            profileCard.className = 'profile-card';
            profileCard.dataset.profileId = profile.id;
            
            profileCard.innerHTML = `
                <h4>
                    ${profile.name}
                    ${profile.is_default ? '<span class="default-badge">Default</span>' : ''}
                </h4>
                <p>${profile.description || 'No description'}</p>
                <div class="profile-config">
                    ${profile.gps_config ? '<span class="config-badge">GPS</span>' : ''}
                    ${profile.obd_config ? '<span class="config-badge">OBD</span>' : ''}
                    ${profile.meshtastic_config ? '<span class="config-badge">Meshtastic</span>' : ''}
                </div>
            `;
            
            profileCard.addEventListener('click', () => this.selectProfile(profile));
            profileList.appendChild(profileCard);
        });
    }
    
    selectProfile(profile) {
        // Remove previous selection
        document.querySelectorAll('.profile-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // Select new profile
        const profileCard = document.querySelector(`[data-profile-id="${profile.id}"]`);
        profileCard.classList.add('selected');
        
        this.selectedProfile = profile;
        this.loadProfileConfig(profile);
    }
    
    loadProfileConfig(profile) {
        // Load GPS config
        if (profile.gps_config) {
            document.getElementById('gps-enabled').checked = true;
            this.toggleDeviceConfig('gps', true);
            this.populateDeviceConfig('gps', profile.gps_config);
        }
        
        // Load OBD config
        if (profile.obd_config) {
            document.getElementById('obd-enabled').checked = true;
            this.toggleDeviceConfig('obd', true);
            this.populateDeviceConfig('obd', profile.obd_config);
        }
        
        // Load Meshtastic config
        if (profile.meshtastic_config) {
            document.getElementById('meshtastic-enabled').checked = true;
            this.toggleDeviceConfig('meshtastic', true);
            this.populateDeviceConfig('meshtastic', profile.meshtastic_config);
        }
    }
    
    populateDeviceConfig(deviceType, config) {
        const prefix = deviceType === 'obd' ? 'obd' : deviceType;
        
        if (config.port) {
            const portSelect = document.getElementById(`${prefix}-port`);
            portSelect.value = config.port;
        }
        
        if (config.baud_rate) {
            const baudSelect = document.getElementById(`${prefix}-baud`);
            baudSelect.value = config.baud_rate;
        }
        
        if (config.rate_hz) {
            const rateInput = document.getElementById(`${prefix}-rate`);
            if (rateInput) rateInput.value = config.rate_hz;
        }
        
        if (config.timeout) {
            const timeoutInput = document.getElementById(`${prefix}-timeout`);
            if (timeoutInput) timeoutInput.value = config.timeout;
        }
        
        if (config.max_reconnect) {
            const reconnectInput = document.getElementById(`${prefix}-reconnect`);
            if (reconnectInput) reconnectInput.value = config.max_reconnect;
        }
        
        if (config.max_payload_size) {
            const payloadInput = document.getElementById(`${prefix}-payload`);
            if (payloadInput) payloadInput.value = config.max_payload_size;
        }
    }
    
    toggleProfileAction(action) {
        const profileSelection = document.getElementById('profile-selection');
        const profileCreation = document.getElementById('profile-creation');
        
        if (action === 'select') {
            profileSelection.style.display = 'block';
            profileCreation.style.display = 'none';
        } else {
            profileSelection.style.display = 'none';
            profileCreation.style.display = 'block';
        }
    }
    
    toggleDeviceConfig(deviceType, enabled) {
        const configDiv = document.getElementById(`${deviceType}-config`);
        const statusIndicator = configDiv.querySelector('.status-indicator');
        
        if (enabled) {
            configDiv.classList.add('enabled');
            statusIndicator.className = 'status-indicator status-success';
            this.deviceConfigs[deviceType].enabled = true;
        } else {
            configDiv.classList.remove('enabled');
            statusIndicator.className = 'status-indicator status-info';
            this.deviceConfigs[deviceType].enabled = false;
        }
    }
    
    async loadAvailablePorts() {
        try {
            const response = await fetch('/api/v1/setup/ports');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            this.populatePortSelects(data.ports);
        } catch (error) {
            console.error('Error loading ports:', error);
            this.showError('Failed to load available ports');
        }
    }
    
    populatePortSelects(ports) {
        const portSelects = ['gps-port', 'obd-port', 'meshtastic-port'];
        
        portSelects.forEach(selectId => {
            const select = document.getElementById(selectId);
            const currentValue = select.value;
            
            // Clear existing options except the first one
            select.innerHTML = '<option value="">Select port...</option>';
            
            ports.forEach(port => {
                const option = document.createElement('option');
                option.value = port.device;
                option.textContent = `${port.device} - ${port.description}`;
                select.appendChild(option);
            });
            
            // Restore previous selection if it still exists
            if (currentValue) {
                select.value = currentValue;
            }
        });
    }
    
    nextStep() {
        if (this.validateCurrentStep()) {
            if (this.currentStep < this.totalSteps) {
                this.currentStep++;
                this.updateStepDisplay();
            }
        }
    }
    
    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStepDisplay();
        }
    }
    
    goToStep(stepNumber) {
        if (stepNumber >= 1 && stepNumber <= this.totalSteps) {
            this.currentStep = stepNumber;
            this.updateStepDisplay();
        }
    }
    
    validateCurrentStep() {
        switch (this.currentStep) {
            case 1:
                return this.validateProfileStep();
            case 2:
                return this.validateDeviceStep();
            case 3:
                return this.validateTestStep();
            default:
                return true;
        }
    }
    
    validateProfileStep() {
        const profileAction = document.querySelector('input[name="profile-action"]:checked').value;
        
        if (profileAction === 'select') {
            if (!this.selectedProfile) {
                this.showError('Please select a device profile');
                return false;
            }
        } else {
            const profileName = document.getElementById('profile-name').value.trim();
            if (!profileName) {
                this.showError('Please enter a profile name');
                return false;
            }
        }
        
        return true;
    }
    
    validateDeviceStep() {
        const enabledDevices = Object.keys(this.deviceConfigs).filter(
            device => this.deviceConfigs[device].enabled
        );
        
        if (enabledDevices.length === 0) {
            this.showError('Please enable at least one device');
            return false;
        }
        
        // Validate each enabled device
        for (const deviceType of enabledDevices) {
            const prefix = deviceType === 'obd' ? 'obd' : deviceType;
            const port = document.getElementById(`${prefix}-port`).value;
            const baud = document.getElementById(`${prefix}-baud`).value;
            
            if (!port || !baud) {
                this.showError(`Please configure ${deviceType.toUpperCase()} port and baud rate`);
                return false;
            }
        }
        
        return true;
    }
    
    validateTestStep() {
        // Tests are optional, so this step is always valid
        return true;
    }
    
    updateStepDisplay() {
        // Update step indicators
        document.querySelectorAll('.step').forEach((step, index) => {
            const stepNumber = index + 1;
            step.classList.remove('active', 'completed');
            
            if (stepNumber === this.currentStep) {
                step.classList.add('active');
            } else if (stepNumber < this.currentStep) {
                step.classList.add('completed');
            }
        });
        
        // Update step content
        document.querySelectorAll('.step-content').forEach((content, index) => {
            content.classList.remove('active');
            if (index + 1 === this.currentStep) {
                content.classList.add('active');
            }
        });
        
        // Update navigation buttons
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        const completeBtn = document.getElementById('complete-btn');
        
        prevBtn.style.display = this.currentStep > 1 ? 'block' : 'none';
        
        if (this.currentStep < this.totalSteps) {
            nextBtn.style.display = 'block';
            completeBtn.style.display = 'none';
        } else {
            nextBtn.style.display = 'none';
            completeBtn.style.display = 'block';
        }
        
        // Special handling for step 4
        if (this.currentStep === 4) {
            this.generateProfileSummary();
        }
    }
    
    isStepCompleted(stepNumber) {
        // For now, all steps are considered completable
        return stepNumber <= this.currentStep;
    }
    
    async startDeviceTest() {
        const testType = document.getElementById('test-type').value;
        const testBtn = document.getElementById('start-test');
        const loading = testBtn.querySelector('.loading');
        const testResults = document.getElementById('test-results');
        
        // Show loading state
        testBtn.disabled = true;
        loading.style.display = 'inline-block';
        testResults.style.display = 'none';
        
        try {
            // Create test setups for enabled devices
            const enabledDevices = Object.keys(this.deviceConfigs).filter(
                device => this.deviceConfigs[device].enabled
            );
            
            const testPromises = enabledDevices.map(deviceType => 
                this.testDevice(deviceType, testType)
            );
            
            const results = await Promise.all(testPromises);
            this.displayTestResults(results);
            
        } catch (error) {
            console.error('Error during device testing:', error);
            this.showError('Device testing failed');
        } finally {
            // Hide loading state
            testBtn.disabled = false;
            loading.style.display = 'none';
        }
    }
    
    async testDevice(deviceType, testType) {
        const prefix = deviceType === 'obd' ? 'obd' : deviceType;
        const port = document.getElementById(`${prefix}-port`).value;
        const baud = document.getElementById(`${prefix}-baud`).value;
        
        // Create device setup
        const setupData = {
            setup_type: deviceType,
            device_name: `${deviceType.toUpperCase()} Device`,
            port_path: port,
            baud_rate: parseInt(baud)
        };
        
        const setupResponse = await fetch('/api/v1/setup/setups', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(setupData)
        });
        
        if (!setupResponse.ok) throw new Error(`Failed to create setup: ${setupResponse.status}`);
        
        const setup = await setupResponse.json();
        
        // Start test
        const testResponse = await fetch('/api/v1/setup/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                setup_id: setup.id,
                test_type: testType
            })
        });
        
        if (!testResponse.ok) throw new Error(`Failed to start test: ${testResponse.status}`);
        
        const testResult = await testResponse.json();
        
        // Poll for test completion
        return await this.pollTestResult(setup.id, deviceType);
    }
    
    async pollTestResult(setupId, deviceType) {
        const maxAttempts = 30; // 30 seconds max
        let attempts = 0;
        
        while (attempts < maxAttempts) {
            await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
            
            try {
                const response = await fetch(`/api/v1/setup/setups/${setupId}`);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                
                const setup = await response.json();
                
                if (setup.status === 'success' || setup.status === 'failed') {
                    return {
                        deviceType,
                        status: setup.status,
                        results: setup.test_results,
                        error: setup.error_message
                    };
                }
                
                attempts++;
            } catch (error) {
                console.error('Error polling test result:', error);
                attempts++;
            }
        }
        
        return {
            deviceType,
            status: 'timeout',
            error: 'Test timed out'
        };
    }
    
    displayTestResults(results) {
        const testResults = document.getElementById('test-results');
        const testOutput = document.getElementById('test-output');
        
        testResults.style.display = 'block';
        testResults.className = 'test-results';
        
        let html = '';
        let hasErrors = false;
        let hasSuccess = false;
        
        results.forEach(result => {
            if (result.status === 'success') {
                hasSuccess = true;
                html += `
                    <div class="test-result success">
                        <h5>✅ ${result.deviceType.toUpperCase()} - Success</h5>
                        <pre>${JSON.stringify(result.results, null, 2)}</pre>
                    </div>
                `;
            } else if (result.status === 'failed') {
                hasErrors = true;
                html += `
                    <div class="test-result error">
                        <h5>❌ ${result.deviceType.toUpperCase()} - Failed</h5>
                        <p>${result.error}</p>
                    </div>
                `;
            } else {
                hasErrors = true;
                html += `
                    <div class="test-result error">
                        <h5>⏱️ ${result.deviceType.toUpperCase()} - Timeout</h5>
                        <p>Test timed out after 30 seconds</p>
                    </div>
                `;
            }
        });
        
        testOutput.innerHTML = html;
        
        // Update test results class
        if (hasErrors && hasSuccess) {
            testResults.classList.add('testing');
        } else if (hasErrors) {
            testResults.classList.add('error');
        } else {
            testResults.classList.add('success');
        }
    }
    
    generateProfileSummary() {
        const summaryDiv = document.getElementById('profile-summary');
        
        const profileAction = document.querySelector('input[name="profile-action"]:checked').value;
        let profileName;
        
        if (profileAction === 'select' && this.selectedProfile) {
            profileName = this.selectedProfile.name;
        } else {
            profileName = document.getElementById('profile-name').value;
        }
        
        const enabledDevices = Object.keys(this.deviceConfigs).filter(
            device => this.deviceConfigs[device].enabled
        );
        
        let html = `
            <div class="summary-item">
                <strong>Profile Name:</strong> ${profileName}
            </div>
            <div class="summary-item">
                <strong>Enabled Devices:</strong> ${enabledDevices.length}
            </div>
            <div class="summary-devices">
        `;
        
        enabledDevices.forEach(deviceType => {
            const prefix = deviceType === 'obd' ? 'obd' : deviceType;
            const port = document.getElementById(`${prefix}-port`).value;
            const baud = document.getElementById(`${prefix}-baud`).value;
            
            html += `
                <div class="device-summary">
                    <strong>${deviceType.toUpperCase()}:</strong> ${port} @ ${baud} baud
                </div>
            `;
        });
        
        html += '</div>';
        summaryDiv.innerHTML = html;
    }
    
    async completeSetup() {
        try {
            const profileAction = document.querySelector('input[name="profile-action"]:checked').value;
            let profileId;
            
            if (profileAction === 'create') {
                // Create new profile
                profileId = await this.createProfile();
            } else {
                // Use selected profile
                profileId = this.selectedProfile.id;
            }
            
            // Save device configurations
            await this.saveDeviceConfigs(profileId);
            
            this.showSuccess('Device setup completed successfully!');
            
            // Redirect to dashboard after a delay
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 2000);
            
        } catch (error) {
            console.error('Error completing setup:', error);
            this.showError('Failed to complete setup');
        }
    }
    
    async createProfile() {
        const profileData = {
            name: document.getElementById('profile-name').value,
            description: document.getElementById('profile-description').value,
            is_default: document.getElementById('profile-default').checked
        };
        
        // Add device configurations
        const enabledDevices = Object.keys(this.deviceConfigs).filter(
            device => this.deviceConfigs[device].enabled
        );
        
        enabledDevices.forEach(deviceType => {
            const prefix = deviceType === 'obd' ? 'obd' : deviceType;
            const config = {
                port: document.getElementById(`${prefix}-port`).value,
                baud_rate: parseInt(document.getElementById(`${prefix}-baud`).value)
            };
            
            // Add optional settings
            const rateInput = document.getElementById(`${prefix}-rate`);
            if (rateInput) config.rate_hz = parseFloat(rateInput.value);
            
            const timeoutInput = document.getElementById(`${prefix}-timeout`);
            if (timeoutInput) config.timeout = parseFloat(timeoutInput.value);
            
            const reconnectInput = document.getElementById(`${prefix}-reconnect`);
            if (reconnectInput) config.max_reconnect = parseInt(reconnectInput.value);
            
            const payloadInput = document.getElementById(`${prefix}-payload`);
            if (payloadInput) config.max_payload_size = parseInt(payloadInput.value);
            
            profileData[`${deviceType}_config`] = config;
        });
        
        const response = await fetch('/api/v1/setup/profiles', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profileData)
        });
        
        if (!response.ok) throw new Error(`Failed to create profile: ${response.status}`);
        
        const profile = await response.json();
        return profile.id;
    }
    
    async saveDeviceConfigs(profileId) {
        const enabledDevices = Object.keys(this.deviceConfigs).filter(
            device => this.deviceConfigs[device].enabled
        );
        
        const setupPromises = enabledDevices.map(deviceType => {
            const prefix = deviceType === 'obd' ? 'obd' : deviceType;
            const setupData = {
                setup_type: deviceType,
                device_name: `${deviceType.toUpperCase()} Device`,
                profile_id: profileId,
                port_path: document.getElementById(`${prefix}-port`).value,
                baud_rate: parseInt(document.getElementById(`${prefix}-baud`).value)
            };
            
            return fetch('/api/v1/setup/setups', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(setupData)
            });
        });
        
        await Promise.all(setupPromises);
    }
    
    showError(message) {
        // Create or update error message
        let errorDiv = document.getElementById('error-message');
        if (!errorDiv) {
            errorDiv = document.createElement('div');
            errorDiv.id = 'error-message';
            errorDiv.className = 'error-message';
            document.querySelector('.wizard-content').insertBefore(errorDiv, document.querySelector('.step-content'));
        }
        
        errorDiv.innerHTML = `
            <div class="alert alert-error">
                <strong>Error:</strong> ${message}
            </div>
        `;
        errorDiv.style.display = 'block';
        
        // Hide after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
    }
    
    showSuccess(message) {
        // Create success message
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.innerHTML = `
            <div class="alert alert-success">
                <strong>Success:</strong> ${message}
            </div>
        `;
        
        document.querySelector('.wizard-content').insertBefore(successDiv, document.querySelector('.step-content'));
        
        // Hide after 3 seconds
        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 3000);
    }
}

// Initialize the setup wizard when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new SetupWizard();
});
