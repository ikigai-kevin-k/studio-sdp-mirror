# State Machine Guide

This guide explains the state machine architecture.

## Overview

The system uses a hierarchical state machine to manage system and game states.

## Main Program States

- **INITIALIZING**: System initialization
- **RUNNING**: Normal operation
- **ERROR**: Error handling
- **STOPPING**: Graceful shutdown
- **STOPPED**: System stopped

## State Transitions

```
INITIALIZING → RUNNING
RUNNING → ERROR → RUNNING
RUNNING → STOPPING → STOPPED
ERROR → STOPPING → STOPPED
```

## Implementation

The state machine is implemented in `gameStateController.py`:

```python
from gameStateController import GameStateController

controller = GameStateController()
await controller.initialize()
```

## Related Documentation

- [Architecture Guide](architecture.md)
- [Game Controllers Guide](game-controllers.md)

