#!/usr/bin/env python3
"""CLI tool to send test frames via Meshtastic service."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.utils.packing import telemetry_packer, pack_telemetry_data, unpack_telemetry_data
from app.services.meshtastic_service import meshtastic_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_packing():
    """Test the packing functionality."""
    print("Testing telemetry packing...")
    
    # Test data
    test_data = {
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
    
    print(f"Original data: {len(test_data)} fields")
    for key, value in test_data.items():
        print(f"  {key}: {value}")
    
    # Pack the data
    packed = pack_telemetry_data(test_data)
    print(f"\nPacked size: {len(packed)} bytes")
    print(f"Packed hex: {packed.hex()}")
    
    # Unpack the data
    unpacked = unpack_telemetry_data(packed)
    print(f"\nUnpacked data: {len(unpacked)} fields")
    for key, value in unpacked.items():
        print(f"  {key}: {value}")
    
    # Verify data integrity
    for key in test_data:
        if key in unpacked:
            original = test_data[key]
            unpacked_val = unpacked[key]
            diff = abs(original - unpacked_val)
            if diff > 0.001:  # Allow small floating point differences
                print(f"WARNING: {key} differs: {original} vs {unpacked_val} (diff: {diff})")
    
    print("\nPacking test completed successfully!")


async def test_meshtastic_service():
    """Test the Meshtastic service."""
    print("\nTesting Meshtastic service...")
    
    # Start the service
    session_id = 1
    await meshtastic_service.start(session_id)
    
    # Add some test data
    test_gps_data = {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "altitude": 10.5,
        "speed_kph": 65.0,
        "heading_deg": 45.0,
    }
    
    test_obd_data = {
        "SPEED": {"value": 65.0, "unit": "kph", "quality": "good"},
        "RPM": {"value": 2500, "unit": "rpm", "quality": "good"},
        "THROTTLE_POS": {"value": 45.0, "unit": "%", "quality": "good"},
        "ENGINE_LOAD": {"value": 75.0, "unit": "%", "quality": "good"},
        "COOLANT_TEMP": {"value": 85.0, "unit": "°C", "quality": "good"},
    }
    
    # Update the service with test data
    meshtastic_service.update_telemetry_data("gps", test_gps_data)
    meshtastic_service.update_telemetry_data("obd", test_obd_data)
    
    print("Added test data to Meshtastic service")
    
    # Wait for a few frames to be published
    print("Waiting for frames to be published...")
    await asyncio.sleep(5)
    
    # Get service status
    status = meshtastic_service.get_status()
    print(f"\nService status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # Get last known values
    last_values = meshtastic_service.get_last_known_values()
    print(f"\nLast known values: {len(last_values)} fields")
    for key, value in last_values.items():
        print(f"  {key}: {value}")
    
    # Stop the service
    await meshtastic_service.stop()
    print("\nMeshtastic service test completed!")


async def send_test_frame(data_file: str = None):
    """Send a test frame with custom data."""
    print("\nSending test frame...")
    
    # Load test data
    if data_file:
        with open(data_file, 'r') as f:
            test_data = json.load(f)
    else:
        # Default test data
        test_data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 10.5,
            "speed_kph": 65.0,
            "SPEED": 65.0,
            "RPM": 2500,
            "THROTTLE_POS": 45.0,
        }
    
    print(f"Test data: {test_data}")
    
    # Pack the data
    packed = pack_telemetry_data(test_data)
    print(f"Packed payload: {len(packed)} bytes")
    print(f"Payload hex: {packed.hex()}")
    
    # Start Meshtastic service
    session_id = 1
    await meshtastic_service.start(session_id)
    
    # Update with test data
    meshtastic_service.update_telemetry_data("test", test_data)
    
    # Wait for frame to be published
    await asyncio.sleep(2)
    
    # Stop service
    await meshtastic_service.stop()
    
    print("Test frame sent successfully!")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Test Meshtastic service and packing")
    parser.add_argument("--test", choices=["packing", "service", "frame"], 
                       default="packing", help="Test to run")
    parser.add_argument("--data-file", help="JSON file with test data for frame test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.test == "packing":
            asyncio.run(test_packing())
        elif args.test == "service":
            asyncio.run(test_meshtastic_service())
        elif args.test == "frame":
            asyncio.run(send_test_frame(args.data_file))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
