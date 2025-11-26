import asyncio

# Global variable to store connected clients
connected_clients = set()


async def ws_handler(websocket):
    """Handle WebSocket connections"""
    connected_clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)


async def broadcast_barcode(barcode):
    """Broadcast barcode to all connected WebSocket clients"""
    if connected_clients:
        await asyncio.gather(*(ws.send(barcode) for ws in connected_clients))


def get_connected_clients():
    """Get the set of connected clients"""
    return connected_clients


def get_client_count():
    """Get the number of connected clients"""
    return len(connected_clients)
