#!/usr/bin/env python3
"""
Environment Detection Module
Detects the current host environment by checking hostname against valid table codes.
"""

import socket
from typing import Optional, Tuple
from log_redirector import log_console, get_timestamp


# Valid table codes that can be detected from hostname
VALID_TABLE_CODES = [
    "ARO-001-1",
    "ARO-001-2",
    "ARO-002-1",
    "ARO-002-2",
    "ASB-001-1",
]


def get_hostname() -> str:
    """
    Get the current hostname.
    
    Returns:
        str: The hostname of the current machine
    """
    try:
        return socket.gethostname()
    except Exception as e:
        log_console(f"Error getting hostname: {e}", "ENV_DETECT >>>")
        return ""


def detect_table_code(hostname: Optional[str] = None) -> Optional[str]:
    """
    Detect table code from hostname.
    
    Args:
        hostname: Optional hostname string. If None, will get from system.
    
    Returns:
        Optional[str]: Detected table code if found, None otherwise
    """
    if hostname is None:
        hostname = get_hostname()
    
    if not hostname:
        return None
    
    # Check if any valid table code is contained in the hostname
    for table_code in VALID_TABLE_CODES:
        if table_code in hostname:
            return table_code
    
    return None


def detect_environment() -> Tuple[Optional[str], Optional[str], bool]:
    """
    Detect the current environment by checking hostname.
    
    Returns:
        Tuple[Optional[str], Optional[str], bool]: 
            - Detected table code (e.g., "ARO-001-2")
            - Hostname
            - Whether detection was successful
    """
    hostname = get_hostname()
    table_code = detect_table_code(hostname)
    
    if table_code:
        log_console(
            f"Environment detected: {table_code} (hostname: {hostname})",
            "ENV_DETECT >>>"
        )
        return table_code, hostname, True
    else:
        log_console(
            f"Environment detection failed: hostname '{hostname}' does not "
            f"contain any valid table code. Valid codes: {VALID_TABLE_CODES}",
            "ENV_DETECT >>>"
        )
        return None, hostname, False


def get_table_id_from_table_code(table_code: str) -> Optional[str]:
    """
    Extract table_id from table_code.
    
    Examples:
        ARO-001-1 -> ARO-001
        ARO-001-2 -> ARO-001
        ARO-002-1 -> ARO-002
        ASB-001-1 -> SBO-001 (special case for SicBo)
    
    Args:
        table_code: Table code string (e.g., "ARO-001-1")
    
    Returns:
        Optional[str]: Table ID (e.g., "ARO-001") or None if invalid
    """
    if not table_code:
        return None
    
    # Special case for SicBo: ASB-001-1 -> SBO-001
    if table_code.startswith("ASB-001"):
        return "SBO-001"
    
    # For roulette tables: ARO-001-1 -> ARO-001, ARO-001-2 -> ARO-001
    if table_code.startswith("ARO-"):
        # Extract table_id by removing the last part (device number)
        parts = table_code.split("-")
        if len(parts) >= 3:
            return f"{parts[0]}-{parts[1]}"
    
    return None


def get_device_id_from_table_code(table_code: str) -> Optional[str]:
    """
    Get device_id from table_code (same as table_code for dealer PCs).
    
    Args:
        table_code: Table code string (e.g., "ARO-001-1")
    
    Returns:
        Optional[str]: Device ID (same as table_code) or None if invalid
    """
    if not table_code:
        return None
    
    # Validate that it's a valid table code
    if table_code in VALID_TABLE_CODES:
        return table_code
    
    return None


def get_device_alias(device_id: str) -> str:
    """
    Get device alias based on device_id suffix.
    
    Rules:
    - If device_id ends with "-1" (e.g., ARO-001-1), returns "main"
    - If device_id ends with "-2" (e.g., ARO-001-2), returns "backup"
    - Otherwise, returns "main" as default
    
    Args:
        device_id: Device ID string (e.g., "ARO-001-1" or "ARO-001-2")
    
    Returns:
        str: Device alias ("main" or "backup")
    """
    if not device_id:
        return "main"
    
    if device_id.endswith("-1"):
        return "main"
    elif device_id.endswith("-2"):
        return "backup"
    else:
        # Default to "main" for unknown patterns
        return "main"


if __name__ == "__main__":
    # Test the environment detection
    print("=" * 60)
    print("Environment Detection Test")
    print("=" * 60)
    
    table_code, hostname, success = detect_environment()
    
    if success:
        print(f"✅ Detection successful!")
        print(f"   Table Code: {table_code}")
        print(f"   Hostname: {hostname}")
        
        table_id = get_table_id_from_table_code(table_code)
        device_id = get_device_id_from_table_code(table_code)
        device_alias = get_device_alias(device_id) if device_id else "main"
        
        print(f"   Table ID: {table_id}")
        print(f"   Device ID: {device_id}")
        print(f"   Device Alias: {device_alias}")
    else:
        print(f"❌ Detection failed!")
        print(f"   Hostname: {hostname}")
        print(f"   Valid table codes: {VALID_TABLE_CODES}")

