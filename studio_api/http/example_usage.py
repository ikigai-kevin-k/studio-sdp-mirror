#!/usr/bin/env python3
"""
Example usage of the Studio API Device Registration endpoints

This script demonstrates how to use the device registration API functions
for registering and managing devices in the Studio system.
"""

import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from register import (
    device_post_v1,
    device_patch_v1,
    device_get_v1,
    device_delete_v1
)


def main():
    """Main function to demonstrate device API usage"""
    
    print("=== Studio API Device Registration Example ===\n")
    
    # Example device and table IDs
    device_id = "EXAMPLE-DEVICE-001"
    table_id = "EXAMPLE-TABLE-001"
    
    try:
        # Step 1: Register a new device
        print(f"Step 1: Registering device '{device_id}'")
        print("-" * 50)
        success = device_post_v1(device_id)
        if success:
            print("✅ Device registration successful!\n")
        else:
            print("❌ Device registration failed!\n")
            return
        
        # Step 2: Assign device to a table
        print(f"Step 2: Assigning device '{device_id}' to table '{table_id}'")
        print("-" * 50)
        success = device_patch_v1(device_id, table_id)
        if success:
            print("✅ Device table assignment successful!\n")
        else:
            print("❌ Device table assignment failed!\n")
            return
        
        # Step 3: Get device information
        print(f"Step 3: Getting information for device '{device_id}'")
        print("-" * 50)
        success = device_get_v1(device_id)
        if success:
            print("✅ Device information retrieved successfully!\n")
        else:
            print("❌ Failed to retrieve device information!\n")
        
        # Step 4: Clean up - delete the test device
        print(f"Step 4: Cleaning up - deleting test device '{device_id}'")
        print("-" * 50)
        success = device_delete_v1(device_id)
        if success:
            print("✅ Device deletion successful!\n")
        else:
            print("❌ Device deletion failed!\n")
        
        print("=== Example completed ===")
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")


if __name__ == "__main__":
    main()
