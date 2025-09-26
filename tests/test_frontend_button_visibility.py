"""
Tests for frontend button visibility and styling.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


class TestButtonVisibility:
    """Test button visibility and styling across frontend pages."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_dashboard_buttons_have_proper_classes(self, client):
        """Test that dashboard buttons have the expected CSS classes."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check telemetry control buttons
        assert 'class="btn btn-success"' in content  # Start Telemetry
        assert 'class="btn btn-danger"' in content   # Stop Telemetry
        assert 'class="btn btn-primary"' in content  # Connect
        assert 'class="btn btn-secondary"' in content # Disconnect

    def test_setup_page_buttons_have_proper_classes(self, client):
        """Test that setup page buttons have the expected CSS classes."""
        response = client.get("/setup.html")
        assert response.status_code == 200
        content = response.text
        
        # Check setup wizard buttons
        assert 'class="btn btn-primary"' in content   # Scan devices, Next, Start Test
        assert 'class="btn btn-secondary"' in content # Previous
        assert 'class="btn btn-success"' in content   # Complete Setup

    def test_setup_page_button_styles_have_high_contrast(self, client):
        """Test that setup page buttons have high contrast colors."""
        response = client.get("/setup.html")
        assert response.status_code == 200
        content = response.text
        
        # Check that setup page has high-contrast button colors
        assert 'background: #2c5aa0;' in content  # Primary button - dark blue
        assert 'background: #6c757d;' in content  # Secondary button - dark gray
        assert 'background: #28a745;' in content  # Success button - dark green
        assert 'color: white;' in content         # White text for contrast
        
        # Check hover states have even darker colors
        assert 'background: #1e3f73;' in content  # Primary hover - darker blue
        assert 'background: #545b62;' in content  # Secondary hover - darker gray
        assert 'background: #1e7e34;' in content  # Success hover - darker green

    def test_setup_page_buttons_have_enhanced_styling(self, client):
        """Test that setup page buttons have enhanced styling for visibility."""
        response = client.get("/setup.html")
        assert response.status_code == 200
        content = response.text
        
        # Check enhanced button styling
        assert 'padding: 14px 28px;' in content    # Larger padding
        assert 'border: 2px solid transparent;' in content  # Border for definition
        assert 'box-shadow: 0 3px 6px rgba(0, 0, 0, 0.15);' in content  # Shadow for depth
        assert 'min-width: 140px;' in content      # Minimum width
        assert 'font-size: 15px;' in content       # Larger font size
        assert 'font-weight: 600;' in content      # Bold font weight

    def test_css_variables_defined(self, client):
        """Test that CSS variables are defined in the stylesheet."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check that CSS variables are defined
        assert ":root {" in content
        assert "--primary-color:" in content
        assert "--secondary-color:" in content
        assert "--success-color:" in content
        assert "--error-color:" in content
        assert "--warning-color:" in content

    def test_button_styles_have_proper_contrast(self, client):
        """Test that button styles include proper contrast colors."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check button base styles
        assert ".btn {" in content
        assert "padding: 12px 24px;" in content
        assert "font-weight: 600;" in content
        assert "border: 2px solid transparent;" in content
        
        # Check button variants
        assert ".btn-primary {" in content
        assert "background: var(--primary-color);" in content
        assert "color: white;" in content
        
        assert ".btn-success {" in content
        assert "background: var(--success-color);" in content
        
        assert ".btn-danger {" in content
        assert "background: var(--error-color);" in content
        
        assert ".btn-secondary {" in content
        assert "background: var(--secondary-color);" in content

    def test_button_hover_states_defined(self, client):
        """Test that button hover states are properly defined."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check hover states
        assert ".btn-primary:hover:not(:disabled)" in content
        assert ".btn-success:hover:not(:disabled)" in content
        assert ".btn-danger:hover:not(:disabled)" in content
        assert ".btn-secondary:hover:not(:disabled)" in content
        
        # Check hover effects include transform and box-shadow
        assert "transform: translateY(-2px);" in content
        assert "box-shadow: 0 4px 8px" in content

    def test_button_disabled_states_defined(self, client):
        """Test that button disabled states are properly defined."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check disabled state
        assert ".btn:disabled {" in content
        assert "opacity: 0.5;" in content
        assert "cursor: not-allowed;" in content
        
        # Check disabled hover prevention
        assert ".btn:disabled:hover {" in content
        assert "transform: none;" in content

    def test_button_focus_accessibility(self, client):
        """Test that buttons have proper focus styles for accessibility."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check focus styles
        assert ".btn:focus {" in content
        assert "outline: 3px solid rgba(52, 152, 219, 0.3);" in content
        assert "outline-offset: 2px;" in content

    def test_loading_spinner_styles(self, client):
        """Test that loading spinner styles are defined for buttons."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check loading state
        assert ".btn.loading {" in content
        assert "color: transparent !important;" in content
        assert "pointer-events: none;" in content
        
        # Check loading spinner
        assert ".btn.loading::after {" in content
        assert "animation: spin 1s linear infinite;" in content

    def test_toast_notification_styles(self, client):
        """Test that toast notification styles are defined."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check toast styles
        assert ".toast {" in content
        assert "position: fixed;" in content
        assert "z-index: 1000;" in content
        
        # Check toast variants
        assert ".toast.success {" in content
        assert ".toast.error {" in content
        assert ".toast.info {" in content
        assert ".toast.warning {" in content

    def test_device_scan_styles(self, client):
        """Test that device scanning styles are defined."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check device scan styles
        assert ".device-scan {" in content
        assert ".scan-status {" in content
        assert ".scan-status.scanning {" in content
        assert ".scan-status.success {" in content
        assert ".scan-status.error {" in content

    def test_css_color_contrast_values(self, client):
        """Test that CSS color values provide good contrast."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check that we have high-contrast color values
        # Primary blue: #3498db (good contrast with white text)
        assert "--primary-color: #3498db;" in content
        assert "--primary-dark-color: #2980b9;" in content
        
        # Success green: #27ae60 (good contrast with white text)
        assert "--success-color: #27ae60;" in content
        assert "--success-dark-color: #229954;" in content
        
        # Error red: #e74c3c (good contrast with white text)
        assert "--error-color: #e74c3c;" in content
        assert "--error-dark-color: #c0392b;" in content
        
        # Secondary gray: #95a5a6 (good contrast with white text)
        assert "--secondary-color: #95a5a6;" in content
        assert "--secondary-dark-color: #7f8c8d;" in content

    def test_responsive_button_styles(self, client):
        """Test that button styles work on mobile devices."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check that buttons have minimum width and proper padding
        assert "min-width: 120px;" in content
        assert "padding: 12px 24px;" in content
        assert "line-height: 1.4;" in content
        
        # Check responsive breakpoints exist
        assert "@media (max-width: 768px)" in content
        assert "@media (max-width: 480px)" in content
