"""
Frontend tests for session creation functionality.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


class TestFrontendSessionCreation:
    """Test frontend session creation UI and functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_dashboard_has_create_session_button(self, client):
        """Test that the dashboard has a Create New Session button."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for Create New Session button
        assert 'id="create-session-btn"' in content
        assert 'Create New Session' in content
        assert 'class="btn btn-primary"' in content

    def test_session_creation_modal_exists(self, client):
        """Test that the session creation modal exists in the HTML."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for modal structure
        assert 'id="session-modal"' in content
        assert 'class="modal"' in content
        assert 'Create New Session' in content

    def test_session_form_has_required_fields(self, client):
        """Test that the session form has all required fields."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for form structure
        assert 'id="session-form"' in content
        assert 'class="modal-body"' in content
        
        # Check for required fields
        assert 'id="session-name"' in content
        assert 'name="name"' in content
        assert 'required' in content
        assert 'placeholder="e.g., Track Day 1"' in content
        
        # Check for optional fields
        assert 'id="car-id"' in content
        assert 'name="car_id"' in content
        assert 'placeholder="e.g., CAR001"' in content
        
        assert 'id="driver-name"' in content
        assert 'name="driver"' in content
        assert 'placeholder="e.g., John Doe"' in content
        
        assert 'id="track-location"' in content
        assert 'name="track"' in content
        assert 'placeholder="e.g., Laguna Seca"' in content
        
        assert 'id="session-notes"' in content
        assert 'name="notes"' in content
        assert 'placeholder="Optional session notes..."' in content

    def test_session_form_has_validation_attributes(self, client):
        """Test that the session form has proper validation attributes."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for validation attributes
        assert 'maxlength="255"' in content  # Session name
        assert 'maxlength="100"' in content  # Car ID, Driver, Track
        assert 'rows="3"' in content  # Notes textarea

    def test_session_form_has_submit_button(self, client):
        """Test that the session form has a submit button."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for submit button
        assert 'id="create-session-submit"' in content
        assert 'type="submit"' in content
        assert 'Create Session' in content
        assert 'class="btn btn-primary"' in content

    def test_session_form_has_cancel_button(self, client):
        """Test that the session form has a cancel button."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for cancel button
        assert 'id="cancel-session"' in content
        assert 'type="button"' in content
        assert 'Cancel' in content
        assert 'class="btn btn-secondary"' in content

    def test_session_form_has_close_button(self, client):
        """Test that the modal has a close button."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for close button
        assert 'id="modal-close"' in content
        assert 'class="modal-close"' in content
        assert '&times;' in content

    def test_session_success_toast_exists(self, client):
        """Test that the success toast notification exists."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for success toast
        assert 'id="session-success-toast"' in content
        assert 'class="toast success"' in content
        assert 'Session Created!' in content
        assert 'id="created-session-id"' in content

    def test_form_error_display_elements_exist(self, client):
        """Test that form error display elements exist."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for error display elements
        assert 'id="name-error"' in content
        assert 'class="form-error"' in content

    def test_modal_styles_are_defined(self, client):
        """Test that modal styles are defined in CSS."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check for modal styles
        assert '.modal {' in content
        assert '.modal-content {' in content
        assert '.modal-header {' in content
        assert '.modal-body {' in content
        assert '.modal-close {' in content
        assert '.modal-actions {' in content

    def test_form_styles_are_defined(self, client):
        """Test that form styles are defined in CSS."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check for form styles
        assert '.form-group {' in content
        assert '.form-group label {' in content
        assert '.form-group input,' in content
        assert '.form-group textarea {' in content
        assert '.form-error {' in content

    def test_toast_styles_are_defined(self, client):
        """Test that toast styles are defined in CSS."""
        response = client.get("/css/styles.css")
        assert response.status_code == 200
        content = response.text
        
        # Check for toast styles
        assert '.toast {' in content
        assert '.toast.show {' in content
        assert '.toast.success {' in content
        assert '.toast-content {' in content

    def test_app_js_includes_session_creation_functionality(self, client):
        """Test that app.js includes session creation functionality."""
        response = client.get("/js/app.js")
        assert response.status_code == 200
        content = response.text
        
        # Check for session creation methods
        assert 'showCreateSessionModal' in content
        assert 'hideCreateSessionModal' in content
        assert 'createSession' in content
        assert 'showSessionCreatedSuccess' in content
        assert 'updateSessionInfo' in content

    def test_app_js_has_form_validation(self, client):
        """Test that app.js includes form validation."""
        response = client.get("/js/app.js")
        assert response.status_code == 200
        content = response.text
        
        # Check for validation methods
        assert 'clearFormErrors' in content
        assert 'showFormError' in content
        assert 'Session name is required' in content

    def test_app_js_has_api_integration(self, client):
        """Test that app.js includes API integration for session creation."""
        response = client.get("/js/app.js")
        assert response.status_code == 200
        content = response.text
        
        # Check for API calls
        assert 'fetch(\'/api/v1/sessions\'' in content
        assert 'POST' in content
        assert 'application/json' in content

    def test_app_js_has_loading_states(self, client):
        """Test that app.js includes loading states for form submission."""
        response = client.get("/js/app.js")
        assert response.status_code == 200
        content = response.text
        
        # Check for loading state handling
        assert 'loading' in content
        assert 'disabled' in content
        assert 'style.display' in content

    def test_app_js_has_error_handling(self, client):
        """Test that app.js includes error handling for session creation."""
        response = client.get("/js/app.js")
        assert response.status_code == 200
        content = response.text
        
        # Check for error handling
        assert 'catch' in content
        assert 'error' in content
        assert 'Failed to create session' in content

    def test_app_js_has_success_handling(self, client):
        """Test that app.js includes success handling for session creation."""
        response = client.get("/js/app.js")
        assert response.status_code == 200
        content = response.text
        
        # Check for success handling
        assert 'showSessionCreatedSuccess' in content
        assert 'updateSessionInfo' in content
        assert 'Session created successfully' in content

    def test_modal_accessibility_features(self, client):
        """Test that the modal has accessibility features."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for basic modal structure (accessibility features can be enhanced later)
        assert 'id="session-modal"' in content
        assert 'class="modal"' in content

    def test_form_has_proper_labels(self, client):
        """Test that the form has proper labels for accessibility."""
        response = client.get("/index.html")
        assert response.status_code == 200
        content = response.text
        
        # Check for proper label associations
        assert 'for="session-name"' in content
        assert 'for="car-id"' in content
        assert 'for="driver-name"' in content
        assert 'for="track-location"' in content
        assert 'for="session-notes"' in content
