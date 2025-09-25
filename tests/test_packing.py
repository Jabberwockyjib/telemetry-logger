"""Tests for telemetry data packing utilities."""

import pytest
import struct

from backend.app.utils.packing import (
    TelemetryPacker,
    telemetry_packer,
    pack_telemetry_data,
    unpack_telemetry_data,
    get_payload_size,
    validate_telemetry_data,
)


class TestTelemetryPacker:
    """Test TelemetryPacker class."""
    
    def test_packer_initialization(self) -> None:
        """Test packer initialization."""
        packer = TelemetryPacker()
        
        assert packer.LAT_LON_SCALE == 1e7
        assert packer.ALTITUDE_SCALE == 1e2
        assert packer.SPEED_SCALE == 1e2
        assert packer.TEMP_SCALE == 1e1
        assert packer.PRESSURE_SCALE == 1e1
        
        assert len(packer.field_mappings) > 0
        assert "latitude" in packer.field_mappings
        assert "longitude" in packer.field_mappings
        assert "SPEED" in packer.field_mappings
        assert "RPM" in packer.field_mappings
    
    def test_field_mappings(self) -> None:
        """Test field mappings structure."""
        packer = TelemetryPacker()
        
        for field_name, (type_id, field_id, scale_factor) in packer.field_mappings.items():
            assert isinstance(type_id, int)
            assert isinstance(field_id, int)
            assert isinstance(scale_factor, float)
            assert scale_factor > 0
    
    def test_get_supported_fields(self) -> None:
        """Test getting supported fields."""
        packer = TelemetryPacker()
        fields = packer.get_supported_fields()
        
        assert isinstance(fields, list)
        assert len(fields) > 0
        assert "latitude" in fields
        assert "longitude" in fields
        assert "SPEED" in fields
        assert "RPM" in fields


class TestPacking:
    """Test packing and unpacking functionality."""
    
    def test_pack_single_field(self) -> None:
        """Test packing a single field."""
        data = {"latitude": 37.7749}
        packed = pack_telemetry_data(data)
        
        # Should have header (2 bytes) + field (6 bytes) = 8 bytes
        assert len(packed) == 8
        
        # Unpack header
        version, field_count = struct.unpack('BB', packed[:2])
        assert version == 0x01
        assert field_count == 1
        
        # Unpack field
        type_id, field_id, value = struct.unpack('<BBi', packed[2:8])
        assert type_id == 0x01  # TYPE_GPS
        assert field_id == 0x01  # GPS_LAT
        assert value == int(37.7749 * 1e7)  # Scaled value
    
    def test_pack_multiple_fields(self) -> None:
        """Test packing multiple fields."""
        data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "SPEED": 65.0,
            "RPM": 2500,
        }
        packed = pack_telemetry_data(data)
        
        # Should have header (2 bytes) + 4 fields (6 bytes each) = 26 bytes
        assert len(packed) == 26
        
        # Unpack header
        version, field_count = struct.unpack('BB', packed[:2])
        assert version == 0x01
        assert field_count == 4
    
    def test_pack_and_unpack_roundtrip(self) -> None:
        """Test packing and unpacking roundtrip."""
        original_data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 10.5,
            "speed_kph": 65.0,
            "heading_deg": 45.0,
            "satellites": 8,
            "hdop": 1.2,
            "SPEED": 65.0,
            "RPM": 2500,
            "THROTTLE_POS": 45.0,
            "ENGINE_LOAD": 75.0,
            "COOLANT_TEMP": 85.0,
            "FUEL_LEVEL": 60.0,
        }
        
        # Pack the data
        packed = pack_telemetry_data(original_data)
        assert len(packed) > 0
        
        # Unpack the data
        unpacked = unpack_telemetry_data(packed)
        
        # Verify all fields are present
        assert len(unpacked) == len(original_data)
        
        # Verify values are close (allowing for floating point precision)
        for key, original_value in original_data.items():
            assert key in unpacked
            unpacked_value = unpacked[key]
            diff = abs(original_value - unpacked_value)
            assert diff < 0.001, f"Field {key} differs: {original_value} vs {unpacked_value}"
    
    def test_pack_unsupported_field(self) -> None:
        """Test packing with unsupported field."""
        data = {
            "latitude": 37.7749,
            "unsupported_field": 123.45,
        }
        packed = pack_telemetry_data(data)
        
        # Should only pack the supported field
        version, field_count = struct.unpack('BB', packed[:2])
        assert field_count == 1
    
    def test_pack_none_values(self) -> None:
        """Test packing with None values."""
        data = {
            "latitude": 37.7749,
            "longitude": None,
            "SPEED": 65.0,
        }
        packed = pack_telemetry_data(data)
        
        # Should only pack non-None values
        version, field_count = struct.unpack('BB', packed[:2])
        assert field_count == 2
    
    def test_unpack_empty_data(self) -> None:
        """Test unpacking empty data."""
        unpacked = unpack_telemetry_data(b'')
        assert unpacked == {}
    
    def test_unpack_invalid_data(self) -> None:
        """Test unpacking invalid data."""
        # Too short
        unpacked = unpack_telemetry_data(b'\x01')
        assert unpacked == {}
        
        # Invalid version
        unpacked = unpack_telemetry_data(b'\x02\x01\x01\x01\x00\x00\x00\x00')
        assert unpacked == {}
    
    def test_unpack_partial_data(self) -> None:
        """Test unpacking partial data."""
        # Valid header but incomplete field
        data = b'\x01\x01\x01\x01\x00\x00'  # Missing last 2 bytes
        unpacked = unpack_telemetry_data(data)
        assert unpacked == {}


class TestValidation:
    """Test data validation functionality."""
    
    def test_validate_valid_data(self) -> None:
        """Test validation of valid data."""
        data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 10.5,
            "SPEED": 65.0,
            "RPM": 2500,
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_unsupported_field(self) -> None:
        """Test validation with unsupported field."""
        data = {
            "latitude": 37.7749,
            "unsupported_field": 123.45,
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Unsupported field: unsupported_field" in errors
    
    def test_validate_non_numeric_value(self) -> None:
        """Test validation with non-numeric value."""
        data = {
            "latitude": "invalid",
            "SPEED": 65.0,
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Field latitude must be numeric, got" in errors[0]
    
    def test_validate_out_of_range_latitude(self) -> None:
        """Test validation with out-of-range latitude."""
        data = {
            "latitude": 200.0,  # Invalid latitude
            "longitude": -122.4194,
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Field latitude out of range:" in errors[0]
    
    def test_validate_out_of_range_longitude(self) -> None:
        """Test validation with out-of-range longitude."""
        data = {
            "latitude": 37.7749,
            "longitude": -200.0,  # Invalid longitude
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Field longitude out of range:" in errors[0]
    
    def test_validate_out_of_range_altitude(self) -> None:
        """Test validation with out-of-range altitude."""
        data = {
            "altitude": 100000.0,  # Too high
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Field altitude out of range:" in errors[0]
    
    def test_validate_out_of_range_speed(self) -> None:
        """Test validation with out-of-range speed."""
        data = {
            "speed_kph": 1000.0,  # Too fast
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Field speed_kph out of range:" in errors[0]
    
    def test_validate_out_of_range_rpm(self) -> None:
        """Test validation with out-of-range RPM."""
        data = {
            "RPM": 20000.0,  # Too high
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Field RPM out of range:" in errors[0]
    
    def test_validate_out_of_range_percentage(self) -> None:
        """Test validation with out-of-range percentage values."""
        data = {
            "THROTTLE_POS": 150.0,  # Too high
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Field THROTTLE_POS out of range:" in errors[0]
    
    def test_validate_out_of_range_temperature(self) -> None:
        """Test validation with out-of-range temperature."""
        data = {
            "COOLANT_TEMP": 300.0,  # Too hot
        }
        
        is_valid, errors = validate_telemetry_data(data)
        assert is_valid is False
        assert "Field COOLANT_TEMP out of range:" in errors[0]


class TestPayloadSize:
    """Test payload size calculations."""
    
    def test_get_payload_size(self) -> None:
        """Test payload size calculation."""
        data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "SPEED": 65.0,
        }
        
        size = get_payload_size(data)
        expected_size = 2 + (3 * 6)  # header(2) + 3 fields(6 each)
        assert size == expected_size
    
    def test_get_payload_size_with_unsupported_fields(self) -> None:
        """Test payload size calculation with unsupported fields."""
        data = {
            "latitude": 37.7749,
            "unsupported_field": 123.45,
            "SPEED": 65.0,
        }
        
        size = get_payload_size(data)
        expected_size = 2 + (2 * 6)  # header(2) + 2 supported fields(6 each)
        assert size == expected_size


class TestScaling:
    """Test scaling factors and precision."""
    
    def test_latitude_scaling(self) -> None:
        """Test latitude scaling precision."""
        # Test with high precision
        original = 37.7749123
        packed = pack_telemetry_data({"latitude": original})
        unpacked = unpack_telemetry_data(packed)
        
        # Should maintain precision to 0.1m (1e7 scale)
        assert abs(unpacked["latitude"] - original) < 1e-7
    
    def test_longitude_scaling(self) -> None:
        """Test longitude scaling precision."""
        original = -122.4194567
        packed = pack_telemetry_data({"longitude": original})
        unpacked = unpack_telemetry_data(packed)
        
        # Should maintain precision to 0.1m (1e7 scale)
        assert abs(unpacked["longitude"] - original) < 1e-7
    
    def test_altitude_scaling(self) -> None:
        """Test altitude scaling precision."""
        original = 10.567
        packed = pack_telemetry_data({"altitude": original})
        unpacked = unpack_telemetry_data(packed)
        
        # Should maintain precision to 1cm (1e2 scale)
        assert abs(unpacked["altitude"] - original) < 1e-2
    
    def test_speed_scaling(self) -> None:
        """Test speed scaling precision."""
        original = 65.123
        packed = pack_telemetry_data({"speed_kph": original})
        unpacked = unpack_telemetry_data(packed)
        
        # Should maintain precision to 0.01 m/s (1e2 scale)
        assert abs(unpacked["speed_kph"] - original) < 1e-2
    
    def test_temperature_scaling(self) -> None:
        """Test temperature scaling precision."""
        original = 85.67
        packed = pack_telemetry_data({"COOLANT_TEMP": original})
        unpacked = unpack_telemetry_data(packed)
        
        # Should maintain precision to 0.1°C (1e1 scale)
        assert abs(unpacked["COOLANT_TEMP"] - original) < 1e-1


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_pack_zero_values(self) -> None:
        """Test packing zero values."""
        data = {
            "latitude": 0.0,
            "longitude": 0.0,
            "SPEED": 0.0,
            "RPM": 0,
        }
        
        packed = pack_telemetry_data(data)
        unpacked = unpack_telemetry_data(packed)
        
        assert unpacked["latitude"] == 0.0
        assert unpacked["longitude"] == 0.0
        assert unpacked["SPEED"] == 0.0
        assert unpacked["RPM"] == 0.0
    
    def test_pack_negative_values(self) -> None:
        """Test packing negative values."""
        data = {
            "longitude": -122.4194,
            "altitude": -10.5,
            "COOLANT_TEMP": -40.0,
        }
        
        packed = pack_telemetry_data(data)
        unpacked = unpack_telemetry_data(packed)
        
        assert unpacked["longitude"] == -122.4194
        assert unpacked["altitude"] == -10.5
        assert unpacked["COOLANT_TEMP"] == -40.0
    
    def test_pack_large_values(self) -> None:
        """Test packing large values."""
        data = {
            "RPM": 9999,
            "FUEL_PRESSURE": 999.9,
        }
        
        packed = pack_telemetry_data(data)
        unpacked = unpack_telemetry_data(packed)
        
        assert unpacked["RPM"] == 9999.0
        assert abs(unpacked["FUEL_PRESSURE"] - 999.9) < 1e-1
    
    def test_pack_empty_data(self) -> None:
        """Test packing empty data."""
        data = {}
        packed = pack_telemetry_data(data)
        assert packed == b''
    
    def test_pack_none_data(self) -> None:
        """Test packing data with all None values."""
        data = {
            "latitude": None,
            "longitude": None,
            "SPEED": None,
        }
        packed = pack_telemetry_data(data)
        assert packed == b''
