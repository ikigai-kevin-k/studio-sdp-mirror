import asyncio
import logging
import websockets
from deviceController import BarcodeController, GameConfig
from controller import GameType

logging.basicConfig(level=logging.INFO)

connected_clients = set()

async def ws_handler(websocket):
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

async def broadcast_barcode(barcode):
    if connected_clients:
        await asyncio.gather(*(ws.send(barcode) for ws in connected_clients))

async def on_barcode_scanned(barcode):
    print(f"[RESULT] Barcode scanned: {barcode}")
    await broadcast_barcode(barcode)

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
    print("Barcode self-test started. Please scan barcodes (Ctrl+C to exit).")
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