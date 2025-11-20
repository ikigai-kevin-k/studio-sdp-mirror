# WebSocket API Reference

Complete WebSocket API documentation.

## update_game_status()

Update game status via WebSocket.

```python
from studio_api.ws_update_v2 import update_game_status

await update_game_status(table_id="SBO-001")
```

## send_exception_event()

Send exception event.

```python
from studio_api.ws_update_v2 import send_exception_event

await send_exception_event("NO SHAKE", "SBO-001")
```

## Related Documentation

- [WebSocket API Guide](../guides/websocket-api.md)
- [Studio API README](../../studio_api/README.md)

