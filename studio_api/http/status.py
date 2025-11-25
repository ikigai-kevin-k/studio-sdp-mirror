"""
Studio API Service Status Module
Provides functions to query service status from Studio API
"""

import requests
import json
from typing import Optional, Dict, Any
from log_redirector import log_api, get_timestamp

# Studio API base URL - Development mode
# Note: This uses port 8084 for service status endpoint
STUDIO_API_BASE_URL = "http://100.64.0.160:8084"


def get_service_status(table_id: str) -> Optional[Dict[str, Any]]:
    """
    Studio API service status endpoint
    GET /v1/service/status?tableId={table_id}
    
    Get service status for a specific table from the Studio API
    
    Args:
        table_id (str): Table ID to query (e.g., "Studio-Roulette-Test", "ARO-002")
        
    Returns:
        Optional[Dict[str, Any]]: Response data if successful, None otherwise
        Response format:
        {
            "error": null,
            "data": {
                "tableId": "Studio-Roulette-Test",
                "uptime": 0,
                "timestamp": 1763685656628,
                "maintenance": true,
                "sdp": "down_pause",
                "idp": "standby",
                "broker": "down",
                "zCam": "down",
                "roulette": "down",
                "shaker": "down",
                "barcodeScanner": "down",
                "nfcScanner": "down"
            }
        }
    """
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "x-signature": "rgs-local-signature",
    }
    
    # Build query parameters
    params = {"tableId": table_id}
    
    try:
        # Make GET request to service status endpoint
        response = requests.get(
            f"{STUDIO_API_BASE_URL}/v1/service/status",
            headers=headers,
            params=params,
            verify=False,
            timeout=5,  # 5 second timeout
        )
        
        # Check if the response status code indicates success
        if response.status_code != 200:
            log_api(
                f"Service status API error: {response.status_code} - {response.text}",
                "HTTP API >>>"
            )
            print(f"[{get_timestamp()}] ⚠️ Service status API returned status code {response.status_code}: {response.text}")
            return None
        
        # Parse the response JSON
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            log_api(
                "Error: Unable to decode JSON response from service status API",
                "HTTP API >>>"
            )
            return None
        
        # Check if there's an error in the response
        # Even if there's an error, try to return data if it exists
        # (e.g., "hasn't changed" error but data still contains current status)
        if response_data.get("error") is not None:
            error_info = response_data.get("error", {})
            error_msg = error_info.get("message", "") if isinstance(error_info, dict) else str(error_info)
            log_api(
                f"Service status API returned error: {response_data.get('error')}",
                "HTTP API >>>"
            )
            print(f"[{get_timestamp()}] ⚠️ Service status API returned error: {error_info}")
            # If data exists despite error, still return it (e.g., "hasn't changed" case)
            data = response_data.get("data")
            if data is not None:
                log_api(
                    f"Service status API returned error but data exists, returning data anyway",
                    "HTTP API >>>"
                )
                print(f"[{get_timestamp()}] Service status API returned error but data exists, returning data: {data}")
                return data
            print(f"[{get_timestamp()}] Service status API returned error and data is None")
            return None
        
        # Return the data portion of the response
        return response_data.get("data")
        
    except requests.exceptions.Timeout:
        log_api(
            f"Service status API request timeout for table_id: {table_id}",
            "HTTP API >>>"
        )
        return None
    except requests.exceptions.ConnectionError as e:
        log_api(
            f"Service status API connection error for table_id {table_id}: {e}",
            "HTTP API >>>"
        )
        return None
    except Exception as e:
        log_api(
            f"Unexpected error calling service status API for table_id {table_id}: {e}",
            "HTTP API >>>"
        )
        return None


def get_sdp_status(table_id: str) -> Optional[str]:
    """
    Get SDP status from service status API
    
    Args:
        table_id (str): Table ID to query
        
    Returns:
        Optional[str]: SDP status string (e.g., "down_pause", "down_cancel", 
                      "up_cancel", "up_resume", "down", "up") or None if error
    """
    status_data = get_service_status(table_id)
    if status_data is None:
        return None
    
    return status_data.get("sdp")


def set_sdp_status_via_http(
    table_id: str, sdp_status: str = "down"
) -> bool:
    """
    Set SDP status via HTTP API PATCH endpoint.
    This is the preferred method as it doesn't require WebSocket connection.
    If the table doesn't exist, it will automatically create it first via POST.
    
    Args:
        table_id (str): Table ID to update (e.g., "ARO-002")
        sdp_status (str): SDP status to set. 
                        Current supported: "down", "up"
                        Future support (placeholder): "down_pause", "down_cancel", 
                        "up_cancel", "up_resume"
                        Default: "down" (for CIT environment compatibility)
        
    Returns:
        bool: True if update successful, False otherwise
    """
    # Set up HTTP headers
    headers = {
        "accept": "application/json",
        "x-signature": "rgs-local-signature",
        "Content-Type": "application/json",
    }
    
    try:
        # First, check if table exists by trying to GET status
        get_response = requests.get(
            f"{STUDIO_API_BASE_URL}/v1/service/status",
            headers=headers,
            params={"tableId": table_id},
            verify=False,
            timeout=5,
        )
        
        # If table doesn't exist (400 error with "not found"), create it first
        if get_response.status_code == 400:
            try:
                error_data = get_response.json()
                if error_data.get("error", {}).get("code") == 22002 and "not found" in error_data.get("error", {}).get("message", "").lower():
                    log_api(
                        f"Table {table_id} not found, creating it first...",
                        "HTTP API >>>"
                    )
                    # Create table status via POST
                    post_data = {"tableId": table_id}
                    post_response = requests.post(
                        f"{STUDIO_API_BASE_URL}/v1/service/status",
                        headers=headers,
                        json=post_data,
                        verify=False,
                        timeout=10,
                    )
                    if post_response.status_code != 200:
                        log_api(
                            f"Failed to create table status: {post_response.status_code} - {post_response.text}",
                            "HTTP API >>>"
                        )
                        return False
                    log_api(
                        f"Table {table_id} created successfully",
                        "HTTP API >>>"
                    )
            except Exception as e:
                log_api(
                    f"Error checking/creating table status: {e}",
                    "HTTP API >>>"
                )
                # Continue to try PATCH anyway
        
        # Build request body according to UpdateTableStatusRequest format
        data = {
            "tableId": table_id,
            "sdp": sdp_status
        }
        
        # Make PATCH request to service status endpoint
        response = requests.patch(
            f"{STUDIO_API_BASE_URL}/v1/service/status",
            headers=headers,
            json=data,
            verify=False,
            timeout=10,  # 10 second timeout
        )
        
        # Check if the response status code indicates success
        if response.status_code != 200:
            # Check if error is "hasn't changed" - this means status is already set
            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", "").lower()
                if "hasn't changed" in error_msg or "hasn't been changed" in error_msg:
                    # Status is already the target value, verify via GET
                    log_api(
                        f"PATCH returned 'hasn't changed', verifying current status...",
                        "HTTP API >>>"
                    )
                    verify_response = requests.get(
                        f"{STUDIO_API_BASE_URL}/v1/service/status",
                        headers=headers,
                        params={"tableId": table_id},
                        verify=False,
                        timeout=5,
                    )
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json().get("data", {})
                        if verify_data.get("sdp") == sdp_status:
                            log_api(
                                f"SDP status is already {sdp_status} (no change needed)",
                                "HTTP API >>>"
                            )
                            return True
            except Exception:
                pass
            
            log_api(
                f"Service status PATCH API error: {response.status_code} - {response.text}",
                "HTTP API >>>"
            )
            return False
        
        # Parse the response JSON
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            log_api(
                "Error: Unable to decode JSON response from service status PATCH API",
                "HTTP API >>>"
            )
            return False
        
        # Check if there's an error in the response
        if response_data.get("error") is not None:
            log_api(
                f"Service status PATCH API returned error: {response_data.get('error')}",
                "HTTP API >>>"
            )
            return False
        
        # Verify the update was successful
        updated_data = response_data.get("data", {})
        if updated_data.get("sdp") == sdp_status:
            log_api(
                f"SDP status successfully updated to {sdp_status} for {table_id}",
                "HTTP API >>>"
            )
            return True
        else:
            log_api(
                f"SDP status update may have failed (expected: {sdp_status}, got: {updated_data.get('sdp')})",
                "HTTP API >>>"
            )
            return False
        
    except requests.exceptions.Timeout:
        log_api(
            f"Service status PATCH API request timeout for table_id: {table_id}",
            "HTTP API >>>"
        )
        return False
    except requests.exceptions.ConnectionError as e:
        log_api(
            f"Service status PATCH API connection error for table_id {table_id}: {e}",
            "HTTP API >>>"
        )
        return False
    except Exception as e:
        log_api(
            f"Unexpected error calling service status PATCH API for table_id {table_id}: {e}",
            "HTTP API >>>"
        )
        return False


def set_sdp_status_via_websocket(
    table_id: str, sdp_status: str = "down"
) -> bool:
    """
    Set SDP status via WebSocket connection to Studio API.
    Note: Prefer using set_sdp_status_via_http() as it's more reliable.
    This function is kept as a fallback option.
    
    Args:
        table_id (str): Table ID to update (e.g., "ARO-002")
        sdp_status (str): SDP status to set. 
                        Current supported: "down", "up"
                        Future support (placeholder): "down_pause", "down_cancel", 
                        "up_cancel", "up_resume"
                        Default: "down" (for CIT environment compatibility)
        
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        import asyncio
        import sys
        import os
        
        # Add studio_api to path to import ws_client
        studio_api_path = os.path.join(
            os.path.dirname(__file__), ".."
        )
        if studio_api_path not in sys.path:
            sys.path.insert(0, studio_api_path)
        
        from studio_api.ws_client import SmartStudioWebSocketClient
        
        # Load configuration from ws.json
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "conf", "ws.json"
        )
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            SERVER_URL = config.get("server_url", "wss://studio-api.iki-cit.cc/v1/ws")
            base_device_name = config.get("device_name", f"{table_id}-1")
            TOKEN = config.get("token", "0000")
        except Exception as e:
            log_api(
                f"Failed to load ws.json config: {e}, using defaults",
                "HTTP API >>>"
            )
            SERVER_URL = "wss://studio-api.iki-cit.cc/v1/ws"
            base_device_name = f"{table_id}-1"
            TOKEN = "0000"
        
        # Use a unique device_id to avoid duplicate login error
        # Append "-script" suffix to differentiate from main process
        import time
        DEVICE_NAME = f"{base_device_name}-script-{int(time.time())}"
        
        async def _set_sdp_status():
            """Internal async function to set SDP status"""
            client = SmartStudioWebSocketClient(
                SERVER_URL, table_id, DEVICE_NAME, TOKEN, fast_connect=True
            )
            
            update_sent = False
            try:
                # Connect to the table
                if not await client.connect():
                    log_api(
                        f"Failed to connect to {table_id}",
                        "HTTP API >>>"
                    )
                    return False
                
                # Send the SDP status update
                # Note: send_multiple_updates may throw exception after sending message
                # (e.g., duplicate login error), but message might still be sent
                sdp_status_update = {"sdp": sdp_status}
                try:
                    await client.send_multiple_updates(sdp_status_update)
                    update_sent = True
                    log_api(
                        f"SDP status update sent: {sdp_status} for {table_id}",
                        "HTTP API >>>"
                    )
                except Exception as send_error:
                    # Message might have been sent before error occurred
                    # Mark as sent if we got past the send operation
                    update_sent = True
                    log_api(
                        f"SDP status update may have been sent (error during send: {send_error})",
                        "HTTP API >>>"
                    )
                
                # Wait a moment for the update to be processed
                await asyncio.sleep(1.0)  # Increased wait time for status propagation
                
                # Check if update was accepted (if we didn't get an error)
                try:
                    preferences = client.get_server_preferences()
                    sdp_accepted = "sdp" in preferences.get("accepted_fields", [])
                    
                    if sdp_accepted:
                        log_api(
                            f"SDP status update to {sdp_status} for {table_id} was accepted",
                            "HTTP API >>>"
                        )
                        return True
                except Exception:
                    # If we can't check preferences, proceed to HTTP verification
                    pass
                    
            except Exception as e:
                log_api(
                    f"Error during WebSocket operation (may be duplicate login): {e}",
                    "HTTP API >>>"
                )
                # If we attempted to send, mark as sent for verification
                if not update_sent:
                    # Check if error occurred after connection (likely means send was attempted)
                    update_sent = True
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass
            
            # Even if we got an error (like duplicate login), the update might have been sent
            # Verify by checking the actual SDP status via HTTP API
            if update_sent:
                log_api(
                    f"Update was sent but response unclear, verifying via HTTP API...",
                    "HTTP API >>>"
                )
                # Wait a bit more for status to propagate
                await asyncio.sleep(2.0)
                
                # Verify status was actually set by checking via HTTP API
                for attempt in range(3):  # Try up to 3 times
                    actual_status = get_sdp_status(table_id)
                    if actual_status == sdp_status:
                        log_api(
                            f"SDP status verified: {actual_status} (update was successful despite connection error)",
                            "HTTP API >>>"
                        )
                        return True
                    elif actual_status:
                        log_api(
                            f"SDP status check {attempt + 1}/3: current={actual_status}, target={sdp_status}",
                            "HTTP API >>>"
                        )
                        if attempt < 2:  # Wait before retry (except on last attempt)
                            await asyncio.sleep(1.0)
                    else:
                        log_api(
                            f"SDP status check {attempt + 1}/3: could not retrieve status",
                            "HTTP API >>>"
                        )
                        if attempt < 2:
                            await asyncio.sleep(1.0)
                
                # Final check
                actual_status = get_sdp_status(table_id)
                if actual_status == sdp_status:
                    log_api(
                        f"SDP status verified after retries: {actual_status}",
                        "HTTP API >>>"
                    )
                    return True
                else:
                    log_api(
                        f"SDP status update to {sdp_status} for {table_id} failed (current: {actual_status})",
                        "HTTP API >>>"
                    )
                    return False
            else:
                log_api(
                    f"Update was not sent, cannot verify status",
                    "HTTP API >>>"
                )
                return False
        
        # Run the async function
        return asyncio.run(_set_sdp_status())
        
    except Exception as e:
        log_api(
            f"Unexpected error in set_sdp_status_via_websocket: {e}",
            "HTTP API >>>"
        )
        return False


if __name__ == "__main__":
    # Example usage
    print("=== Testing Studio API Service Status Endpoint ===\n")
    
    # Test with example table ID
    test_table_id = "Studio-Roulette-Test"
    print(f"Getting service status for table: {test_table_id}")
    print("-" * 50)
    
    status_data = get_service_status(test_table_id)
    if status_data:
        print(f"✅ Service status retrieved successfully:")
        print(json.dumps(status_data, indent=2))
        
        sdp_status = get_sdp_status(test_table_id)
        if sdp_status:
            print(f"\n✅ SDP Status: {sdp_status}")
    else:
        print("❌ Failed to retrieve service status")
    
    print("\n=== Test completed ===")

