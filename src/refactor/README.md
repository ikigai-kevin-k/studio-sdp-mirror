# SDP Game System Refactoring

This document describes the hierarchical state machine structure of the SDP game system.

## Main Program State Machine

```mermaid
stateDiagram-v2
    [*] --> INITIALIZING
    INITIALIZING --> RUNNING: start_running[is_initialized]
    INITIALIZING --> ERROR: handle_error
    RUNNING --> ERROR: handle_error
    RUNNING --> STOPPING: start_stopping
    ERROR --> STOPPING: start_stopping
    STOPPING --> STOPPED: complete_stop
    STOPPED --> [*]
    
    note right of INITIALIZING
        Load config
        Setup logging
        Create controller
    end note
    
    note right of RUNNING
        Game controller running
        Processing game rounds
    end note
    
    note right of ERROR
        Error handling
        Retry mechanism
    end note
```

## Game Controllers State Machines

### Roulette Controller (using RS232)
```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> WAITING_START: start_game
    WAITING_START --> SPINNING: start_spin
    SPINNING --> RESULT_READY: set_result[is_valid_result]
    RESULT_READY --> IDLE: reset
    
    state ERROR
    IDLE --> ERROR: handle_error
    WAITING_START --> ERROR: handle_error
    SPINNING --> ERROR: handle_error
    RESULT_READY --> ERROR: handle_error
    ERROR --> IDLE: reset
    
    note right of SPINNING
        RS232 communication
        Wheel control
    end note
```

### SicBo Controller (using IDP and MQTT)
```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> WAITING_START: start_game
    WAITING_START --> SHAKING: start_shake
    SHAKING --> DETECTING: start_detect
    DETECTING --> RESULT_READY: set_result[is_valid_result]
    RESULT_READY --> IDLE: reset
    
    state ERROR
    IDLE --> ERROR: handle_error
    WAITING_START --> ERROR: handle_error
    SHAKING --> ERROR: handle_error
    DETECTING --> ERROR: handle_error
    RESULT_READY --> ERROR: handle_error
    ERROR --> IDLE: reset
    
    note right of SHAKING
        MQTT control shaker
    end note
    
    note right of DETECTING
        IDP detect dice
    end note
```

### Blackjack Controller (using HID)
```mermaid
stateDiagram-v2
    [*] --> TABLE_CLOSED
    TABLE_CLOSED --> START_GAME: open_table
    START_GAME --> DEAL_CARDS: start_dealing
    DEAL_CARDS --> PLAYER_TURN: start_player_turn[is_initial_deal_complete]
    PLAYER_TURN --> DEALER_TURN: start_dealer_turn[is_player_turn_complete]
    DEALER_TURN --> GAME_RESULT: end_game
    GAME_RESULT --> TABLE_CLOSED: close_table
    
    state ERROR
    TABLE_CLOSED --> ERROR: handle_error
    START_GAME --> ERROR: handle_error
    DEAL_CARDS --> ERROR: handle_error
    PLAYER_TURN --> ERROR: handle_error
    DEALER_TURN --> ERROR: handle_error
    GAME_RESULT --> ERROR: handle_error
    ERROR --> TABLE_CLOSED: reset
    
    note right of DEAL_CARDS
        HID barcode scanner
        Card detection
    end note
```

## Hierarchical Structure

```mermaid
graph TD
    Main[Main State Machine] --> Roulette[Roulette Controller]
    Main --> SicBo[SicBo Controller]
    Main --> Blackjack[Blackjack Controller]
    
    Roulette --> RS232[RS232 Communication]
    SicBo --> MQTT[MQTT Protocol]
    SicBo --> IDP[IDP Detection]
    Blackjack --> HID[HID Scanner]
    
    style Main fill:#f9f,stroke:#333,stroke-width:4px
    style Roulette fill:#bbf,stroke:#333
    style SicBo fill:#bbf,stroke:#333
    style Blackjack fill:#bbf,stroke:#333
    style RS232 fill:#dfd,stroke:#333
    style MQTT fill:#dfd,stroke:#333
    style IDP fill:#dfd,stroke:#333
    style HID fill:#dfd,stroke:#333
```

## State Machine Descriptions

### Main State Machine
- Controls overall program flow
- Manages game type selection and initialization
- Handles high-level error cases
- Coordinates resource cleanup

### Game Controllers
Each game controller manages its specific game logic and device communication:

#### Roulette Controller
- Manages roulette wheel via RS232
- Controls game rounds and result detection
- Handles wheel speed and positioning

#### SicBo Controller
- Controls dice shaker via MQTT
- Uses IDP for dice detection
- Manages shake patterns and result validation

#### Blackjack Controller
- Uses HID barcode scanner for card detection
- Manages game rounds and player turns
- Handles card validation and game rules

## Communication Protocols
- **RS232**: Serial communication for roulette wheel control
- **MQTT**: Message queue for dice shaker control
- **IDP**: Image detection for dice results
- **HID**: Human Interface Device for card scanning
