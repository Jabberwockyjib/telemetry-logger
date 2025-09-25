"""Binary packing utilities for telemetry data."""

import logging
import struct
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class TelemetryPacker:
    """Binary packer for telemetry data to create compact Meshtastic payloads."""
    
    # Packing format constants
    LAT_LON_SCALE = 1e7  # Scale factor for latitude/longitude (1e7 = 0.1m precision)
    ALTITUDE_SCALE = 1e2  # Scale factor for altitude (1e2 = 1cm precision)
    SPEED_SCALE = 1e2    # Scale factor for speed (1e2 = 0.01 m/s precision)
    TEMP_SCALE = 1e1     # Scale factor for temperature (1e1 = 0.1°C precision)
    PRESSURE_SCALE = 1e1 # Scale factor for pressure (1e1 = 0.1 kPa precision)
    
    # Data type constants for packing
    TYPE_GPS = 0x01
    TYPE_OBD = 0x02
    TYPE_STATUS = 0x03
    
    # GPS field constants
    GPS_LAT = 0x01
    GPS_LON = 0x02
    GPS_ALT = 0x03
    GPS_SPEED = 0x04
    GPS_HEADING = 0x05
    GPS_SATELLITES = 0x06
    GPS_HDOP = 0x07
    
    # OBD field constants
    OBD_SPEED = 0x10
    OBD_RPM = 0x11
    OBD_THROTTLE = 0x12
    OBD_ENGINE_LOAD = 0x13
    OBD_COOLANT_TEMP = 0x14
    OBD_FUEL_LEVEL = 0x15
    OBD_INTAKE_TEMP = 0x16
    OBD_MAF = 0x17
    OBD_TIMING_ADVANCE = 0x18
    OBD_FUEL_PRESSURE = 0x19
    
    # Status field constants
    STATUS_BATTERY = 0x20
    STATUS_SIGNAL_STRENGTH = 0x21
    STATUS_UPTIME = 0x22
    
    def __init__(self) -> None:
        """Initialize the telemetry packer."""
        self.field_mappings = self._create_field_mappings()
    
    def _create_field_mappings(self) -> Dict[str, Tuple[int, int, float]]:
        """Create field mappings for packing.
        
        Returns:
            Dict mapping field names to (type, field_id, scale_factor) tuples.
        """
        return {
            # GPS fields
            "latitude": (self.TYPE_GPS, self.GPS_LAT, self.LAT_LON_SCALE),
            "longitude": (self.TYPE_GPS, self.GPS_LON, self.LAT_LON_SCALE),
            "altitude": (self.TYPE_GPS, self.GPS_ALT, self.ALTITUDE_SCALE),
            "speed_kph": (self.TYPE_GPS, self.GPS_SPEED, self.SPEED_SCALE),
            "heading_deg": (self.TYPE_GPS, self.GPS_HEADING, 1.0),
            "satellites": (self.TYPE_GPS, self.GPS_SATELLITES, 1.0),
            "hdop": (self.TYPE_GPS, self.GPS_HDOP, 1e1),
            
            # OBD fields
            "SPEED": (self.TYPE_OBD, self.OBD_SPEED, self.SPEED_SCALE),
            "RPM": (self.TYPE_OBD, self.OBD_RPM, 1.0),
            "THROTTLE_POS": (self.TYPE_OBD, self.OBD_THROTTLE, 1.0),
            "ENGINE_LOAD": (self.TYPE_OBD, self.OBD_ENGINE_LOAD, 1.0),
            "COOLANT_TEMP": (self.TYPE_OBD, self.OBD_COOLANT_TEMP, self.TEMP_SCALE),
            "FUEL_LEVEL": (self.TYPE_OBD, self.OBD_FUEL_LEVEL, 1.0),
            "INTAKE_TEMP": (self.TYPE_OBD, self.OBD_INTAKE_TEMP, self.TEMP_SCALE),
            "MAF": (self.TYPE_OBD, self.OBD_MAF, 1e1),
            "TIMING_ADVANCE": (self.TYPE_OBD, self.OBD_TIMING_ADVANCE, 1e1),
            "FUEL_PRESSURE": (self.TYPE_OBD, self.OBD_FUEL_PRESSURE, self.PRESSURE_SCALE),
        }
    
    def pack_telemetry_data(self, data: Dict[str, Union[float, int]]) -> bytes:
        """Pack telemetry data into a compact binary payload.
        
        Args:
            data: Dictionary of telemetry data with field names as keys.
            
        Returns:
            Packed binary data as bytes.
        """
        packed_fields = []
        
        for field_name, value in data.items():
            if field_name not in self.field_mappings:
                continue
            
            if value is None:
                continue
            
            try:
                type_id, field_id, scale_factor = self.field_mappings[field_name]
                
                # Scale the value
                scaled_value = int(value * scale_factor)
                
                # Pack the field: type(1) + field_id(1) + value(4) = 6 bytes
                field_data = struct.pack('<BBi', type_id, field_id, scaled_value)
                packed_fields.append(field_data)
                
            except (ValueError, struct.error) as e:
                logger.warning(f"Failed to pack field {field_name}: {e}")
                continue
        
        if not packed_fields:
            return b''
        
        # Combine all fields
        payload = b''.join(packed_fields)
        
        # Add header: version(1) + field_count(1) + payload
        header = struct.pack('BB', 0x01, len(packed_fields))
        
        return header + payload
    
    def unpack_telemetry_data(self, data: bytes) -> Dict[str, float]:
        """Unpack binary telemetry data back to field values.
        
        Args:
            data: Packed binary data.
            
        Returns:
            Dictionary of unpacked telemetry data.
        """
        if len(data) < 2:
            return {}
        
        try:
            # Unpack header
            version, field_count = struct.unpack('BB', data[:2])
            
            if version != 0x01:
                logger.warning(f"Unknown packing version: {version}")
                return {}
            
            # Create reverse mapping for unpacking
            reverse_mappings = {}
            for field_name, (type_id, field_id, scale_factor) in self.field_mappings.items():
                reverse_mappings[(type_id, field_id)] = (field_name, scale_factor)
            
            unpacked_data = {}
            offset = 2
            
            for _ in range(field_count):
                if offset + 6 > len(data):
                    break
                
                # Unpack field: type(1) + field_id(1) + value(4)
                type_id, field_id, scaled_value = struct.unpack('<BBi', data[offset:offset+6])
                
                if (type_id, field_id) in reverse_mappings:
                    field_name, scale_factor = reverse_mappings[(type_id, field_id)]
                    value = scaled_value / scale_factor
                    unpacked_data[field_name] = value
                
                offset += 6
            
            return unpacked_data
            
        except struct.error as e:
            logger.error(f"Failed to unpack telemetry data: {e}")
            return {}
    
    def get_payload_size(self, data: Dict[str, Union[float, int]]) -> int:
        """Calculate the size of packed payload for given data.
        
        Args:
            data: Dictionary of telemetry data.
            
        Returns:
            Size in bytes of the packed payload.
        """
        field_count = sum(1 for field_name in data.keys() if field_name in self.field_mappings)
        return 2 + (field_count * 6)  # header(2) + fields(6 each)
    
    def get_supported_fields(self) -> List[str]:
        """Get list of supported field names for packing.
        
        Returns:
            List of supported field names.
        """
        return list(self.field_mappings.keys())
    
    def validate_data(self, data: Dict[str, Union[float, int]]) -> Tuple[bool, List[str]]:
        """Validate telemetry data for packing.
        
        Args:
            data: Dictionary of telemetry data to validate.
            
        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []
        
        for field_name, value in data.items():
            if field_name not in self.field_mappings:
                errors.append(f"Unsupported field: {field_name}")
                continue
            
            if value is None:
                continue
            
            if not isinstance(value, (int, float)):
                errors.append(f"Field {field_name} must be numeric, got {type(value)}")
                continue
            
            # Check for reasonable value ranges
            if field_name in ["latitude", "longitude"]:
                if not (-180 <= value <= 180):
                    errors.append(f"Field {field_name} out of range: {value}")
            elif field_name == "altitude":
                if not (-1000 <= value <= 50000):  # -1km to 50km
                    errors.append(f"Field {field_name} out of range: {value}")
            elif field_name in ["speed_kph", "SPEED"]:
                if not (0 <= value <= 500):  # 0-500 km/h
                    errors.append(f"Field {field_name} out of range: {value}")
            elif field_name == "RPM":
                if not (0 <= value <= 10000):  # 0-10k RPM
                    errors.append(f"Field {field_name} out of range: {value}")
            elif field_name in ["THROTTLE_POS", "ENGINE_LOAD", "FUEL_LEVEL"]:
                if not (0 <= value <= 100):  # 0-100%
                    errors.append(f"Field {field_name} out of range: {value}")
            elif field_name in ["COOLANT_TEMP", "INTAKE_TEMP"]:
                if not (-50 <= value <= 200):  # -50°C to 200°C
                    errors.append(f"Field {field_name} out of range: {value}")
        
        return len(errors) == 0, errors


# Global packer instance
telemetry_packer = TelemetryPacker()


def pack_telemetry_data(data: Dict[str, Union[float, int]]) -> bytes:
    """Convenience function to pack telemetry data.
    
    Args:
        data: Dictionary of telemetry data.
        
    Returns:
        Packed binary data.
    """
    return telemetry_packer.pack_telemetry_data(data)


def unpack_telemetry_data(data: bytes) -> Dict[str, float]:
    """Convenience function to unpack telemetry data.
    
    Args:
        data: Packed binary data.
        
    Returns:
        Dictionary of unpacked telemetry data.
    """
    return telemetry_packer.unpack_telemetry_data(data)


def get_payload_size(data: Dict[str, Union[float, int]]) -> int:
    """Convenience function to get payload size.
    
    Args:
        data: Dictionary of telemetry data.
        
    Returns:
        Size in bytes of the packed payload.
    """
    return telemetry_packer.get_payload_size(data)


def validate_telemetry_data(data: Dict[str, Union[float, int]]) -> Tuple[bool, List[str]]:
    """Convenience function to validate telemetry data.
    
    Args:
        data: Dictionary of telemetry data.
        
    Returns:
        Tuple of (is_valid, error_messages).
    """
    return telemetry_packer.validate_data(data)
