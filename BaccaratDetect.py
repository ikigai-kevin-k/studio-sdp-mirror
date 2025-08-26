#!/usr/bin/env python3
"""
Test script for BaccaratIDPController
Tests the baccarat image detection functionality
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the current directory to Python path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from deviceController import BaccaratIDPController
from controller import GameConfig, GameType


async def baccarat_detect():
    """Test the baccarat detection functionality"""

    # Configure logging to only show errors
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create game configuration
    config = GameConfig(
        room_id="BAC-001",
        broker_host="192.168.20.10",
        broker_port=1883,
        game_type=GameType.BACCARAT,
    )

    # Create BaccaratIDPController instance
    controller = BaccaratIDPController(config)

    try:
        # Initialize the controller
        await controller.initialize()

        # Generate a test round ID
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        round_id = f"BAC-001-{timestamp}"

        # Test detection
        success, result = await controller.detect(round_id)

        if success:
            if result and result != [""] * 6:
                # Parse the result
                if len(result) == 6:
                    player_cards = result[:2]  # First 2 cards for player
                    banker_cards = result[2:4]  # Next 2 cards for banker
                    additional_cards = result[4:]  # Additional cards if needed

                    # Basic validation
                    valid_cards = [card for card in result if card]

                else:
                    valid_cards = 0
            else:
                valid_cards = 0
        else:
            valid_cards = 0

        # Wait a bit before cleanup
        await asyncio.sleep(2)

    except Exception as e:
        return False, ["ERROR"]

    finally:
        # Cleanup
        await controller.cleanup()

    return success, result


async def multiple_detections():
    """Test multiple detection attempts"""

    # Configure logging to only show errors
    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    config = GameConfig(
        room_id="BAC-001",
        broker_host="192.168.20.10",
        broker_port=1883,
        game_type=GameType.BACCARAT,
    )

    controller = BaccaratIDPController(config)

    try:
        await controller.initialize()

        results = []
        for i in range(3):
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            round_id = f"BAC-001-{timestamp}-{i+1}"

            success, result = await controller.detect(round_id)

            if success and result and result != [""] * 6:
                results.append((f"Test {i+1}", result, "Success"))
            else:
                if result == [""] * 6:
                    results.append(
                        (
                            f"Test {i+1}",
                            result,
                            "Timeout but normal processing, return default value",
                        )
                    )
                else:
                    results.append((f"Test {i+1}", result, "Failed"))

            # Wait between tests
            if i < 2:  # Don't wait after the last test
                await asyncio.sleep(3)

    except Exception as e:
        return False

    finally:
        await controller.cleanup()

    return results


async def main():
    """Main test function"""
    print("Baccarat IDP Controller Test")
    print("=" * 40)

    # Test 1: Single detection
    print("\nSingle detection test...")
    success1, result1 = await baccarat_detect()

    if success1 and result1 and result1 != [""] * 6:
        print(f"Single detection: {result1} - Success")
    else:
        print(f"Single detection: {result1} - Failed")

    # Test 2: Multiple detections
    print("\nMultiple detections test...")
    results = await multiple_detections()

    if results:
        for test_name, result, status in results:
            print(f"{test_name}: {result} - {status}")

    # Summary
    print("\n" + "=" * 40)
    if success1 and results:
        print("🎉 All tests completed!")
        return 0
    else:
        print("⚠ Some tests failed!")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with unexpected error: {e}")
        sys.exit(1)
