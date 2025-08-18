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
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzZXNzaW9uSWQiOiI2N2MyYjk5Mi1lOGEyLTQ4NWQtODA5Ni05ZTIxY2VjMjBmMTciLCJnYW1lQ29kZSI6WyJCQ1ItMDAxIl0sInJvbGUiOiJzZHAiLCJjcmVhdGVkQXQiOjE3NTMzMjY2NDYyOTIsImlhdCI6MTc1MzMyNjY0Nn0.TwSFQybSKOqOwsBrHBRZYST3CGxwEUpJJA9a8-h_jXw"

# Game state variables
barcode_count = 0
current_round_id = None
game_started = False
scanned_barcodes = []  # Store scanned barcodes for result generation
game_start_time = None  # Track when game started
current_bet_period = None  # Store current bet period
waiting_for_bet_period = (
    False  # Flag to prevent additional scans during bet period wait
)
barcode_controller = None  # Global reference to barcode controller
scan_start_time = None  # Track when scanning should start for current round


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
        "accept": "application/json",
        "Bearer": f"Bearer {token}",
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={ACCESS_TOKEN}",
        "Connection": "close",
    }

    data = {}
    response = requests.post(
        f"{url}/start", headers=headers, json=data, verify=False
    )

    if response.status_code != 200:
        print(f"Error starting game: {response.status_code} - {response.text}")
        return None, None

    try:
        response_data = response.json()
        round_id = (
            response_data.get("data", {})
            .get("table", {})
            .get("tableRound", {})
            .get("roundId")
        )
        bet_period = (
            response_data.get("data", {}).get("table", {}).get("betPeriod")
        )

        if not round_id:
            print("Error: roundId not found in response.")
            return None, None

        print(
            f"Game started successfully. Round ID: {round_id}, Bet Period: {bet_period}"
        )
        return round_id, bet_period

    except json.JSONDecodeError:
        print("Error: Unable to decode JSON response.")
        return None, None


def deal_post_v2(url, token, round_id, result):
    """Send deal result to CIT server"""
    timecode = str(int(time.time() * 1000))
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "timecode": timecode,
        "Cookie": f"accessToken={ACCESS_TOKEN}",
        "Connection": "close",
    }

    data = {"roundId": f"{round_id}", "sicBo": result}

    response = requests.post(
        f"{url}/deal", headers=headers, json=data, verify=False
    )

    if response.status_code != 200:
        print(
            f"Error sending deal result: {response.status_code} - {response.text}"
        )
        return False

    print(f"Deal result sent successfully: {result}")
    return True


def finish_post_v2(url, token):
    """Finish the current game round"""
    headers = {
        "accept": "application/json",
        "Bearer": token,
        "x-signature": "los-local-signature",
        "Content-Type": "application/json",
        "Cookie": f"accessToken={ACCESS_TOKEN}",
        "Connection": "close",
    }

    data = {}
    response = requests.post(
        f"{url}/finish", headers=headers, json=data, verify=False
    )

    if response.status_code != 200:
        print(
            f"Error finishing game: {response.status_code} - {response.text}"
        )
        return False

    print("Game finished successfully.")
    return True


async def start_new_game():
    """Start a new game round"""
    global current_round_id, game_started, game_start_time, current_bet_period, barcode_count, scanned_barcodes, waiting_for_bet_period

    print("Starting new game round...")

    # Add a small delay before starting new game to ensure previous round is fully closed
    await asyncio.sleep(1)

    round_id, bet_period = start_post_v2(CIT_BASE_URL, CIT_TOKEN)
    if round_id:
        current_round_id = round_id
        game_started = True
        game_start_time = time.time()  # Record start time
        current_bet_period = bet_period  # Store bet period
        barcode_count = 0  # Reset barcode count
        scanned_barcodes = []  # Reset barcode list
        waiting_for_bet_period = False  # Reset waiting flag
        scan_start_time = (
            time.time() + 0.5
        )  # Set scan start time to 0.5 seconds from now

        # Resume barcode scanning for new game
        if barcode_controller:
            barcode_controller.resume_scanning()
            print("Barcode scanning resumed for new game")

        print(f"Game started with Round ID: {round_id}")
        print(f"Bet period: {bet_period} seconds")
        print(f"Scanning will start at: {scan_start_time}")
        return True
    else:
        print("Failed to start game. Please try again.")
        return False


async def on_barcode_scanned(barcode):
    global barcode_count, scanned_barcodes, waiting_for_bet_period, game_started

    current_time = time.time()

    # Check if we're currently waiting for bet period to end
    if waiting_for_bet_period:
        print(f"[IGNORED] Barcode scanned during bet period wait: {barcode}")
        return

    # Check if game is not started
    if not game_started:
        print(f"[IGNORED] Barcode scanned when game not started: {barcode}")
        return

    # Check if scanning has started for this round (time-based validation)
    if scan_start_time and current_time < scan_start_time:
        print(f"[IGNORED] Barcode scanned before round started: {barcode}")
        return

    # Check if this barcode was scanned during pause period
    if barcode_controller and barcode_controller.pause_timestamp:
        if (
            current_time < barcode_controller.pause_timestamp + 1.0
        ):  # Allow 1 second buffer
            print(f"[IGNORED] Barcode scanned during pause period: {barcode}")
            return

    # Check if this barcode is the same as the last one (duplicate detection)
    if scanned_barcodes and scanned_barcodes[-1] == barcode:
        print(f"[DUPLICATE] Ignoring duplicate barcode: {barcode}")
        return

    print(f"[RESULT] Barcode scanned: {barcode}")
    await broadcast_barcode(barcode)

    # Store scanned barcode
    scanned_barcodes.append(barcode)

    # Increment barcode count
    barcode_count += 1
    print(f"Barcode count: {barcode_count}/3")
    print(f"Scanned barcodes: {scanned_barcodes}")

    # When 3 barcodes are scanned, wait for bet period to end then send deal result
    if barcode_count >= 3:
        print("3 barcodes scanned. Waiting for bet period to end...")
        waiting_for_bet_period = True  # Set flag to ignore additional scans

        # Pause barcode scanning to prevent additional scans
        if barcode_controller:
            barcode_controller.pause_scanning()
            print("Barcode scanning paused")

        # Calculate remaining time to wait
        elapsed_time = time.time() - game_start_time
        remaining_time = max(
            0, current_bet_period - elapsed_time + 2
        )  # Add 2 seconds buffer for safety

        if remaining_time > 0:
            print(
                f"Waiting {remaining_time:.1f} seconds for bet period to end..."
            )
            await asyncio.sleep(remaining_time)
        else:
            # If we've already passed the bet period, wait a bit more to ensure server is ready
            print(
                "Bet period already passed, waiting additional 1 second for server sync..."
            )
            await asyncio.sleep(1)

        print("Bet period ended. Sending deal result...")

        # Convert scanned barcodes to game result
        result = convert_barcodes_to_result(scanned_barcodes)
        print(f"Converted result: {result}")

        # Retry mechanism for sending deal result
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            if deal_post_v2(CIT_BASE_URL, CIT_TOKEN, current_round_id, result):
                print("Deal result sent successfully.")

                # Wait a moment then finish the game
                await asyncio.sleep(2)

                if finish_post_v2(CIT_BASE_URL, CIT_TOKEN):
                    print("Game finished successfully.")

                    # Start next game round
                    await start_new_game()
                    print("New game round started. Please scan barcodes.")
                    return  # Exit the retry loop on success
                else:
                    print("Failed to finish game.")
                    break
            else:
                retry_count += 1
                if retry_count < max_retries:
                    print(
                        f"Failed to send deal result. Retrying in 2 seconds... (Attempt {retry_count}/{max_retries})"
                    )
                    await asyncio.sleep(2)
                else:
                    print("Failed to send deal result after all retries.")
                    # Reset game state to allow manual restart
                    game_started = False
                    barcode_count = 0
                    scanned_barcodes = []
                    waiting_for_bet_period = False
                    # Resume barcode scanning
                    if barcode_controller:
                        barcode_controller.resume_scanning()
                        print("Barcode scanning resumed")


async def main():
    global barcode_controller

    # 1. Prepare GameConfig (adjust as needed)
    config = GameConfig(
        room_id="test",
        broker_host="",
        broker_port=1883,
        game_type=GameType.BACCARAT,
    )
    # 2. Initialize BarcodeController
    barcode_controller = BarcodeController(config)
    # 3. Set HID device path
    device_path = "/dev/hidraw4"  # Adjust according to your system

    # 4. Start WebSocket server
    ws_server = await websockets.serve(ws_handler, "localhost", 8765)
    print("WebSocket server started at ws://localhost:8765")

    # 5. Start the first game round immediately
    print("Starting initial game round...")
    if not await start_new_game():
        print("Failed to start initial game. Exiting.")
        return

    # 6. Start barcode scanning
    await barcode_controller.initialize(
        device_path, callback=on_barcode_scanned
    )
    print("Barcode self-test started. Please scan barcodes (Ctrl+C to exit).")
    print(
        "Game flow: Game started -> Scan 3 barcodes -> Wait for bet period -> Deal result -> Finish game -> Start new game"
    )
    print(
        "Note: Program automatically waits for bet period to end before sending deal result"
    )

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
