import asyncio
import logging
import websockets
import time
import requests
import json
from deviceController import BarcodeController, GameConfig
from controller import GameType

logging.basicConfig(level=logging.INFO)

connected_clients = set()

# CIT API configuration
CIT_BASE_URL = "https://crystal-table.iki-cit.cc/v2/service/tables/BCR-001"
CIT_TOKEN = "E5LN4END9Q"
ACCESS_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uSWQiOiI2N2MyYjk5Mi1lOGEyLTQ4NWQtODA5Ni05ZTIxY2VjMjBmMTciLCJnYW1lQ29kZSI6WyJCQ1ItMDAxIl0sInJvbGUiOiJzZHAiLCJjcmVhdGVkQXQiOjE3NTMzMjY2NDYyOTIsImlhdCI6MTc1MzMyNjY0Nn0.TwSFQybSKOqOwsBrHBRZYST3CGxwEUpJJA9a8-h_jXw'

# Game state variables
barcode_count = 0
current_round_id = None
game_started = False
scanned_barcodes = []  # Store scanned barcodes for result generation
game_start_time = None  # Track when game started
current_bet_period = None  # Store current bet period

async def ws_handler(websocket):
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

async def broadcast_barcode(barcode):
    if connected_clients:
        await asyncio.gather(*(ws.send(barcode) for ws in connected_clients))

def convert_barcodes_to_result(barcodes):
    """
    Convert scanned barcodes to game result format
    This function can be customized based on your barcode format and game requirements
    """
    try:
        # Method 1: If barcodes are numeric values, use them directly
        if len(barcodes) >= 3:
            # Convert string barcodes to integers, with validation
            result = []
            for barcode in barcodes[:3]:  # Take first 3 barcodes
                try:
                    value = int(barcode)
                    # Ensure value is within valid range (1-6 for dice)
                    if 1 <= value <= 6:
                        result.append(value)
                    else:
                        # If out of range, use modulo to get valid value
                        result.append((value % 6) + 1)
                except ValueError:
                    # If barcode is not numeric, use hash-based value
                    hash_value = hash(barcode) % 6 + 1
                    result.append(hash_value)
            
            # Ensure we have exactly 3 values
            while len(result) < 3:
                result.append(1)  # Default value
            
            return result[:3]  # Return exactly 3 values
        else:
            # If not enough barcodes, use default values
            return [1, 2, 3]
    except Exception as e:
        print(f"Error converting barcodes to result: {e}")
        return [1, 2, 3]  # Fallback to default result

def start_post_v2(url, token):
    """Start a new game round on CIT server"""
    headers = {
        'accept': 'application/json',
        'Bearer': f'Bearer {token}',
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={ACCESS_TOKEN}',
        'Connection': 'close'
    }
    
    data = {}
    response = requests.post(f'{url}/start', headers=headers, json=data, verify=False)
    
    if response.status_code != 200:
        print(f"Error starting game: {response.status_code} - {response.text}")
        return None, None
    
    try:
        response_data = response.json()
        round_id = response_data.get('data', {}).get('table', {}).get('tableRound', {}).get('roundId')
        bet_period = response_data.get('data', {}).get('table', {}).get('betPeriod')
        
        if not round_id:
            print("Error: roundId not found in response.")
            return None, None
            
        print(f"Game started successfully. Round ID: {round_id}, Bet Period: {bet_period}")
        return round_id, bet_period
        
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return None, None

def deal_post_v2(url, token, round_id, result):
    """Send deal result to CIT server"""
    timecode = str(int(time.time() * 1000))
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'timecode': timecode,
        'Cookie': f'accessToken={ACCESS_TOKEN}',
        'Connection': 'close'
    }
    
    data = {
        "roundId": f'{round_id}',
        "sicBo": result
    }
    
    response = requests.post(f'{url}/deal', headers=headers, json=data, verify=False)
    
    if response.status_code != 200:
        print(f"Error sending deal result: {response.status_code} - {response.text}")
        return False
    
    print(f"Deal result sent successfully: {result}")
    return True

def finish_post_v2(url, token):
    """Finish the current game round"""
    headers = {
        'accept': 'application/json',
        'Bearer': token,
        'x-signature': 'los-local-signature',
        'Content-Type': 'application/json',
        'Cookie': f'accessToken={ACCESS_TOKEN}',
        'Connection': 'close'
    }
    
    data = {}
    response = requests.post(f'{url}/finish', headers=headers, json=data, verify=False)
    
    if response.status_code != 200:
        print(f"Error finishing game: {response.status_code} - {response.text}")
        return False
    
    print("Game finished successfully.")
    return True

async def on_barcode_scanned(barcode):
    global barcode_count, current_round_id, game_started, scanned_barcodes, game_start_time, current_bet_period
    
    print(f"[RESULT] Barcode scanned: {barcode}")
    await broadcast_barcode(barcode)
    
    # Start game if not started yet
    if not game_started:
        print("Starting new game round...")
        round_id, bet_period = start_post_v2(CIT_BASE_URL, CIT_TOKEN)
        if round_id:
            current_round_id = round_id
            game_started = True
            scanned_barcodes = []  # Reset barcode list for new game
            game_start_time = time.time()  # Record start time
            current_bet_period = bet_period  # Store bet period
            print(f"Game started with Round ID: {round_id}")
            print(f"Bet period: {bet_period} seconds")
        else:
            print("Failed to start game. Please try again.")
            return
    
    # Store scanned barcode
    scanned_barcodes.append(barcode)
    
    # Increment barcode count
    barcode_count += 1
    print(f"Barcode count: {barcode_count}/3")
    print(f"Scanned barcodes: {scanned_barcodes}")
    
    # When 3 barcodes are scanned, wait for bet period to end then send deal result
    if barcode_count >= 3:
        print("3 barcodes scanned. Waiting for bet period to end...")
        
        # Calculate remaining time to wait
        elapsed_time = time.time() - game_start_time
        remaining_time = max(0, current_bet_period - elapsed_time + 1)  # Add 1 second buffer
        
        if remaining_time > 0:
            print(f"Waiting {remaining_time:.1f} seconds for bet period to end...")
            await asyncio.sleep(remaining_time)
        
        print("Bet period ended. Sending deal result...")
        
        # Convert scanned barcodes to game result
        result = convert_barcodes_to_result(scanned_barcodes)
        print(f"Converted result: {result}")
        
        if deal_post_v2(CIT_BASE_URL, CIT_TOKEN, current_round_id, result):
            print("Deal result sent successfully.")
            
            # Wait a moment then finish the game
            await asyncio.sleep(2)
            
            if finish_post_v2(CIT_BASE_URL, CIT_TOKEN):
                print("Game finished successfully.")
                
                # Reset for next round
                barcode_count = 0
                current_round_id = None
                game_started = False
                scanned_barcodes = []
                game_start_time = None
                current_bet_period = None
                print("Ready for next game round. Please scan barcodes to start new game.")
            else:
                print("Failed to finish game.")
        else:
            print("Failed to send deal result.")

async def main():
    # 1. Prepare GameConfig (adjust as needed)
    config = GameConfig(room_id="test", broker_host="", broker_port=1883, game_type=GameType.BACCARAT)
    # 2. Initialize BarcodeController
    barcode_controller = BarcodeController(config)
    # 3. Set HID device path
    device_path = "/dev/hidraw4"  # Adjust according to your system

    # 4. Start WebSocket server
    ws_server = await websockets.serve(ws_handler, "localhost", 8765)
    print("WebSocket server started at ws://localhost:8765")

    # 5. Start barcode scanning
    await barcode_controller.initialize(device_path, callback=on_barcode_scanned)
    print("Barcode self-test started. Please scan barcodes to start game (Ctrl+C to exit).")
    print("Game flow: Scan 3 barcodes -> Wait for bet period -> Deal result -> Finish game -> Ready for next round")
    print("Note: Program automatically waits for bet period to end before sending deal result")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Test interrupted by user.")
    finally:
        await barcode_controller.cleanup()
        print("Barcode self-test finished.")

if __name__ == "__main__":
    asyncio.run(main())