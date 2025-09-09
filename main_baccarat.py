import asyncio
import logging
import websockets
import time
import sys
import json
import argparse
from deviceController import BarcodeController, GameConfig
from controller import GameType

sys.path.append("./studio-sdp-roulette")
from dealing_order_check import (
    check_dealing_order,
    mock_data_non_outs,
    mock_data_outs,
)
import check_outs_rule

# Import BCR API functions
from table_api.bcr.api_v2_bcr import start_post_v2, deal_post_v2, finish_post_v2

# Import WebSocket utilities
from baccaratWsUtils import ws_handler, broadcast_barcode

# Import barcode utilities
from baccaratBarcodeUtils import (
    convert_barcodes_to_result,
    on_barcode_scanned as barcode_handler,
)

# TODO:
# Add the dealing order check
# Add the outs check
# How to implement:
# When 4 barcode results are scanned, check these 4 card positions by the idp (image data processor)
# Check if the dealing position order is correct by the dealing_order_check.py
# Check whether need to deal the 5th and/or 6th card by the check_outs_rule.py
# If no need but 5th or 6th barcode is scanned, report error
# If no need and 5th or 6th barcode is not scanned, send deal result
# If need to deal the 5th and/or 6th card, check the 5th or 6th card position by the idp (image data processor)
# If the 5th or 6th card position is correct, send deal result
# If the 5th or 6th card position is incorrect, report error
# Because the idp (image data processor) has not implement yet, so we will use the mock data to test the dealing_order_check.py and check_outs_rule.py
# Now every round we use the correct mock data so that we can send deal result


logging.basicConfig(level=logging.INFO)


def load_table_config():
    """Load table configuration from JSON file"""
    config_path = "conf/table-config-baccarat-v2.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            if config_data and len(config_data) > 0:
                table_config = config_data[0]  # Get first table config
                return (
                    f"{table_config['post_url']}{table_config['game_code']}",
                    table_config["table_token"],
                )
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not load config from {config_path}: {e}")
        print("Using default configuration")

    # Fallback to default values
    return (
        "https://crystal-table.iki-cit.cc/v2/service/tables/BCR-001",
        "E5LN4END9Q",
    )


# CIT API configuration
CIT_BASE_URL, CIT_TOKEN = load_table_config()

# Game state variables
barcode_count = 0
scanned_barcodes = []  # Store scanned barcodes for result generation
barcode_controller = None  # Global reference to barcode controller
scan_start_time = None  # Track when scanning should start for current round

# IDP mode variables
idp_mode = False
idp_controller = None

current_round_id = None
game_started = False
game_start_time = None  # Track when game started
current_bet_period = None  # Store current bet period
waiting_for_bet_period = (
    False  # Flag to prevent additional scans during bet period wait
)


async def start_new_game():
    """Start a new game round"""
    global current_round_id, game_started, game_start_time, current_bet_period, barcode_count, scanned_barcodes, waiting_for_bet_period

    print("Starting new game round...")

    # Add a small delay before starting new game to ensure previous round is fully closed
    await asyncio.sleep(1)

    if idp_only_mode:
        # In IDP-only mode, skip CIT API calls
        current_round_id = f"DEV-{int(time.time())}"
        game_started = True
        game_start_time = time.time()
        current_bet_period = 30  # Default bet period for development
        barcode_count = 0
        scanned_barcodes = []
        waiting_for_bet_period = False
        scan_start_time = time.time() + 0.5

        print("IDP-only mode: Starting card detection (no CIT API)...")
        await detect_cards_with_idp()

        print(f"Game started with Round ID: {current_round_id}")
        print(f"Bet period: {current_bet_period} seconds (default)")
        return True
    else:
        # Normal mode: call CIT API
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

            if idp_mode:
                # In IDP mode, wait for bet period to end before starting card detection
                print(
                    f"IDP mode: Waiting for bet period ({bet_period} seconds) to end..."
                )
                await asyncio.sleep(bet_period)
                print("Bet period ended, starting card detection...")
                await detect_cards_with_idp()
            else:
                # Resume barcode scanning for new game
                if barcode_controller:
                    barcode_controller.resume_scanning()
                    print("Barcode scanning resumed for new game")

            print(f"Game started with Round ID: {round_id}")
            print(f"Bet period: {bet_period} seconds")
            if not idp_mode:
                print(f"Scanning will start at: {scan_start_time}")
            return True
        else:
            print("Failed to start game. Please try again.")
            return False


async def detect_cards_with_idp():
    """Detect cards using IDP in IDP mode"""
    global barcode_count, scanned_barcodes

    if not idp_controller:
        print("IDP controller not initialized")
        return

    attempt_count = 0
    max_wait_time = 60  # Maximum wait time in seconds (1 minute)
    start_time = time.time()

    while True:
        attempt_count += 1
        current_wait_time = time.time() - start_time

        # Check if we've exceeded maximum wait time
        if current_wait_time > max_wait_time:
            print(f"Maximum wait time ({max_wait_time} seconds) exceeded.")
            print("IDP detection could not complete successfully.")
            print("Consider checking camera setup and card positioning.")
            break

        try:
            print(
                f"Detecting cards with IDP (attempt {attempt_count}, elapsed: {current_wait_time:.1f}s)..."
            )
            success, result = await idp_controller.detect(current_round_id)

            if success and result:
                # Check if we have at least 4 non-empty strings (minimum cards needed)
                non_empty_cards = [
                    card for card in result if card and card.strip()
                ]
                print(f"IDP detection result: {result}")
                print(f"Non-empty cards found: {len(non_empty_cards)}")

                if len(non_empty_cards) >= 4:
                    # Convert IDP result to barcode format for compatibility
                    scanned_barcodes = [
                        str(i) for i in range(len(result)) if result[i]
                    ]
                    barcode_count = len(scanned_barcodes)

                    print(
                        f"🎉 IDP detection successful after {attempt_count} attempts!"
                    )
                    print(f"Final result: {result}")
                    print(f"Converted to barcodes: {scanned_barcodes}")
                    print(f"Barcode count: {barcode_count}")

                    # Process the result using existing logic
                    await process_idp_result(result)
                    return  # Success, exit retry loop
                else:
                    print(
                        f"IDP detection incomplete: need at least 4 cards, got {len(non_empty_cards)}"
                    )

                    if len(non_empty_cards) > 0:
                        print(
                            f"Progress: {len(non_empty_cards)} cards detected so far..."
                        )

                    # Fixed wait time: 1 second between attempts
                    wait_time = 1
                    print(f"Waiting {wait_time} second before next attempt...")
                    await asyncio.sleep(wait_time)

            else:
                print("IDP detection failed or returned empty result")

                # Fixed wait time: 1 second between attempts
                wait_time = 1
                print(f"Waiting {wait_time} second before retry...")
                await asyncio.sleep(wait_time)

        except Exception as e:
            print(f"Error during IDP detection (attempt {attempt_count}): {e}")

            # Fixed wait time: 1 second between attempts
            wait_time = 1
            print(f"Waiting {wait_time} second before retry...")
            await asyncio.sleep(wait_time)

    # If we reach here, maximum wait time was exceeded
    print("IDP detection could not complete successfully within time limit.")
    print("Consider checking camera setup and card positioning.")


async def process_idp_result(idp_result):
    """Process IDP detection result"""

    # Simulate barcode scanning events for compatibility
    if barcode_count >= 4:
        # Check dealing order for first 4 cards
        if not check_dealing_order(mock_data_non_outs, outs=False):
            print("[ERROR] Dealing order incorrect for first 4 cards!")
            return
        print("[CHECK] First 4 cards dealing order correct.")

        # Determine if 5th/6th card should be dealt
        # Filter out empty strings before passing to check_outs_rule
        player_cards = [
            card
            for card in [idp_result[0], idp_result[2]]
            if card and card.strip()
        ]
        banker_cards = [
            card
            for card in [idp_result[1], idp_result[3]]
            if card and card.strip()
        ]

        # Only proceed if we have valid cards
        if len(player_cards) >= 2 and len(banker_cards) >= 2:
            player_draw = check_outs_rule.player_draw_rule(player_cards)
            player_third_card = None
            if (
                player_draw
                and len(idp_result) > 4
                and idp_result[4]
                and idp_result[4].strip()
            ):
                player_third_card = idp_result[4]
                player_cards.append(idp_result[4])

            banker_draw = check_outs_rule.banker_draw_rule(
                banker_cards, player_cards, player_third_card
            )
        else:
            print(
                f"[WARNING] Insufficient valid cards for outs check: player={len(player_cards)}, banker={len(banker_cards)}"
            )
            player_draw = False
            banker_draw = False
        need_outs = player_draw or banker_draw

        if not need_outs:
            print("[INFO] No outs needed, sending deal result.")
            await send_deal_result()
        elif barcode_count >= 6:
            print("[INFO] Outs check passed, sending deal result.")
            await send_deal_result()
        else:
            print("[INFO] Waiting for more cards...")

    elif barcode_count >= 6:
        # Check dealing order for 6 cards
        if not check_dealing_order(mock_data_outs, outs=True):
            print("[ERROR] Dealing order incorrect for 6 cards!")
            return
        print("[CHECK] 6 cards dealing order correct.")
        await send_deal_result()


async def send_deal_result():
    """Send deal result and finish game"""
    global game_started, barcode_count, scanned_barcodes, waiting_for_bet_period

    # Convert scanned barcodes to game result
    result = convert_barcodes_to_result(scanned_barcodes)
    print(f"Converted result: {result}")

    if idp_only_mode:
        # In IDP-only mode, skip CIT API calls
        print("IDP-only mode: Skipping CIT API calls")
        print("Game finished successfully (development mode)")

        # Start next game round
        await start_new_game()
        print("New game round started.")
        return
    else:
        # Normal mode: call CIT API
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
                    print("New game round started.")
                    return
                else:
                    print("Failed to finish game.")
                    break
            else:
                retry_count += 1
                if retry_count < max_retries:
                    print(
                        f"Failed to send deal result. Retrying in 2 seconds... "
                        f"(Attempt {retry_count}/{max_retries})"
                    )
                    await asyncio.sleep(2)
                else:
                    print("Failed to send deal result after all retries.")
                    # Reset game state to allow manual restart
                    game_started = False
                    barcode_count = 0
                    scanned_barcodes = []
                    waiting_for_bet_period = False
                    return


async def on_barcode_scanned(barcode):
    """Wrapper function to call the barcode handler from baccaratBarcodeUtils"""
    global barcode_count, scanned_barcodes

    # Call the utility function with all necessary parameters
    new_barcode_count, new_scanned_barcodes = await barcode_handler(
        barcode,
        barcode_count,
        game_started,
        scanned_barcodes,
        waiting_for_bet_period,
        scan_start_time,
        barcode_controller,
        current_round_id,
        broadcast_barcode,
        check_dealing_order,
        mock_data_non_outs,
        mock_data_outs,
        check_outs_rule,
        deal_post_v2,
        finish_post_v2,
        CIT_BASE_URL,
        CIT_TOKEN,
        start_new_game,
    )

    # Update global variables
    barcode_count = new_barcode_count
    scanned_barcodes = new_scanned_barcodes


async def main():
    global barcode_controller, idp_mode, idp_controller, idp_only_mode

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Baccarat Game Controller")
    parser.add_argument(
        "--idp-dev",
        action="store_true",
        help="Enable IDP development mode (no barcode scanning)",
    )
    parser.add_argument(
        "--idp-only-dev",
        action="store_true",
        help="Enable IDP-only development mode (no CIT API calls)",
    )
    args = parser.parse_args()

    idp_mode = args.idp_dev
    idp_only_mode = args.idp_only_dev

    # Validate mode combinations
    if idp_only_mode and not idp_mode:
        print("❌ Error: --idp-only-dev requires --idp-dev mode")
        sys.exit(1)

    if idp_only_mode:
        print("🚀 Starting in IDP-only development mode")
        print("📷 Card detection will be handled by IDP controller")
        print("🔌 Barcode scanning is disabled")
        print("🚫 CIT API calls are disabled (development only)")
    elif idp_mode:
        print("🚀 Starting in IDP development mode")
        print("📷 Card detection will be handled by IDP controller")
        print("🔌 Barcode scanning is disabled")
    else:
        print("📱 Starting in normal barcode scanning mode")
        print("📷 Card detection will be handled by barcode scanning")

    # 1. Prepare GameConfig (adjust as needed)
    config = GameConfig(
        room_id="test",
        broker_host="",
        broker_port=1883,
        game_type=GameType.BACCARAT,
    )

    if idp_mode:
        # Initialize IDP controller
        try:
            from deviceController import BaccaratIDPController

            idp_controller = BaccaratIDPController(config)
            await idp_controller.initialize()
            print("✅ IDP controller initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize IDP controller: {e}")
            print("Falling back to barcode mode")
            idp_mode = False
    else:
        # Initialize BarcodeController
        barcode_controller = BarcodeController(config)
        # Set HID device path
        device_path = "/dev/hidraw4"  # Adjust according to your system

    # 4. Start WebSocket server
    ws_server = await websockets.serve(ws_handler, "localhost", 8765)
    print("WebSocket server started at ws://localhost:8765")

    # 5. Start the first game round immediately
    print("Starting initial game round...")
    if not await start_new_game():
        print("Failed to start initial game. Exiting.")
        return

    if not idp_mode:
        # 6. Start barcode scanning
        await barcode_controller.initialize(
            device_path, callback=on_barcode_scanned
        )
        print(
            "Barcode self-test started. Please scan barcodes (Ctrl+C to exit)."
        )
        print(
            "Game flow: Game started -> Scan 3 barcodes -> Wait for bet period -> "
            "Deal result -> Finish game -> Start new game"
        )
        print(
            "Note: Program automatically waits for bet period to end before "
            "sending deal result"
        )
    else:
        if idp_only_mode:
            print("IDP-only mode: Waiting for card detection...")
            print(
                "Game flow: Game started -> IDP detects cards -> Deal result -> "
                "Finish game -> Start new game (no CIT API)"
            )
        else:
            print("IDP mode: Waiting for card detection...")
            print(
                "Game flow: Game started -> IDP detects cards -> Deal result -> "
                "Finish game -> Start new game"
            )

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Test interrupted by user.")
    finally:
        if idp_mode and idp_controller:
            await idp_controller.cleanup()
            print("IDP test finished.")
        elif barcode_controller:
            await barcode_controller.cleanup()
            print("Barcode self-test finished.")


if __name__ == "__main__":
    asyncio.run(main())
