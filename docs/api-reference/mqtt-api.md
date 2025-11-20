# MQTT API Reference

Complete MQTT API documentation.

## CompleteMQTTSystem

The unified MQTT system for all game types.

### Initialization

```python
from mqtt.complete_system import CompleteMQTTSystem, GameType, Environment

system = CompleteMQTTSystem(
    game_type=GameType.SICBO,
    environment=Environment.DEVELOPMENT
)
await system.initialize()
```

### Methods

#### detect()

Send detection command and wait for result.

```python
success, result = await system.detect(
    round_id="round_001",
    input_stream="input_stream",
    output_stream="output_stream"
)
```

#### cleanup()

Cleanup resources.

```python
await system.cleanup()
```

## Related Documentation

- [MQTT System Guide](../guides/mqtt-system.md)
- [MQTT Migration Guide](../../MQTT_MIGRATION_GUIDE.md)

