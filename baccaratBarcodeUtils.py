import asyncio
import time


def convert_barcodes_to_result(barcodes):
    """
    Convert scanned barcodes to game result format
    This function can be customized based on your barcode format
    and game requirements
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


async def on_barcode_scanned(
    barcode,
    barcode_count,
    game_started,
    scanned_barcodes,
    waiting_for_bet_period,
    scan_start_time,
    barcode_controller,
    current_round_id,
    broadcast_barcode_func,
    check_dealing_order,
    mock_data_non_outs,
    mock_data_outs,
    check_outs_rule,
    deal_post_v2,
    finish_post_v2,
    CIT_BASE_URL,
    CIT_TOKEN,
    start_new_game_func,
):
    """Handle barcode scanning events"""
    current_time = time.time()

    # Check if we're currently waiting for bet period to end
    if waiting_for_bet_period:
        print(f"[IGNORED] Barcode scanned during bet period wait: {barcode}")
        return barcode_count, scanned_barcodes

    # Check if game is not started
    if not game_started:
        print(f"[IGNORED] Barcode scanned when game not started: {barcode}")
        return barcode_count, scanned_barcodes

    # Check if scanning has started for this round (time-based validation)
    if scan_start_time and current_time < scan_start_time:
        print(f"[IGNORED] Barcode scanned before round started: {barcode}")
        return barcode_count, scanned_barcodes

    # Check if this barcode was scanned during pause period
    if barcode_controller and barcode_controller.pause_timestamp:
        if (
            current_time < barcode_controller.pause_timestamp + 1.0
        ):  # Allow 1 second buffer
            print(f"[IGNORED] Barcode scanned during pause period: {barcode}")
            return barcode_count, scanned_barcodes

    # Check if this barcode is the same as the last one (duplicate detection)
    if scanned_barcodes and scanned_barcodes[-1] == barcode:
        print(f"[DUPLICATE] Ignoring duplicate barcode: {barcode}")
        return barcode_count, scanned_barcodes

    print(f"[RESULT] Barcode scanned: {barcode}")
    await broadcast_barcode_func(barcode)

    # Store scanned barcode
    scanned_barcodes.append(barcode)

    # Increment barcode count
    barcode_count += 1
    print(f"Barcode count: {barcode_count}/6")
    print(f"Scanned barcodes: {scanned_barcodes}")

    # --- Add dealing order check and outs check ---
    # Check dealing order only when 4 cards are scanned
    if barcode_count == 4:
        # Use mock_data_non_outs to simulate idp
        if not check_dealing_order(mock_data_non_outs, outs=False):
            print("[ERROR] Dealing order incorrect for first 4 cards!")
            # Add error handling/prompt
            return barcode_count, scanned_barcodes
        print("[CHECK] First 4 cards dealing order correct.")
        # Determine if 5th/6th card should be dealt
        # Use mock_data_outs to simulate 6 cards
        # Assume first 4 cards are: player1, banker1, player2, banker2
        # Use first 4 barcodes as player/banker hands
        player_cards = [mock_data_non_outs[0], mock_data_non_outs[2]]
        banker_cards = [mock_data_non_outs[1], mock_data_non_outs[3]]
        # Use check_outs_rule to determine if 5th/6th card should be dealt
        player_draw = check_outs_rule.player_draw_rule(player_cards)
        player_third_card = None
        if player_draw:
            # Simulate player's third card
            player_third_card = (
                check_outs_rule.CARD_VALUES.get(mock_data_outs[4][0], None)
                if len(mock_data_outs[4]) > 0
                else None
            )
            player_cards.append(mock_data_outs[4])
        banker_draw = check_outs_rule.banker_draw_rule(
            banker_cards, player_cards, player_third_card
        )
        need_outs = player_draw or banker_draw
        print(f"[CHECK] Need outs? {need_outs}")
        # If no outs needed and extra barcode scanned, report error
        if not need_outs and barcode_count > 4:
            print("[ERROR] No outs needed, but extra barcode scanned!")
            return barcode_count, scanned_barcodes
        # If outs needed, wait for 6th barcode for outs check
        if need_outs:
            print("[INFO] Waiting for 6th barcode for outs check...")
            return barcode_count, scanned_barcodes
        # If no outs needed, send deal result
        print("[INFO] No outs needed, sending deal result.")
        # Here you can call the deal result sending process
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
                    await start_new_game_func()
                    print("New game round started. Please scan barcodes.")
                    return 0, []  # Reset barcode count and scanned barcodes
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
                    return 0, []  # Reset barcode count and scanned barcodes
        return barcode_count, scanned_barcodes
    # If outs needed, wait for 6th barcode for dealing order check
    if barcode_count == 6:
        # Use mock_data_outs to simulate idp
        if not check_dealing_order(mock_data_outs, outs=True):
            print("[ERROR] Dealing order incorrect for 6 cards!")
            return barcode_count, scanned_barcodes
        print("[CHECK] 6 cards dealing order correct.")
        print("[INFO] Outs check passed, sending deal result.")
        # Here you can call the deal result sending process
        # Convert scanned barcodes to game result
        result = convert_barcodes_to_result(scanned_barcodes)[
            :3
        ]  # workaround for now
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
                    await start_new_game_func()
                    print("New game round started. Please scan barcodes.")
                    return 0, []  # Reset barcode count and scanned barcodes
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
                    return 0, []  # Reset barcode count and scanned barcodes
        return barcode_count, scanned_barcodes

    return barcode_count, scanned_barcodes
