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

### Roulette Controller (RS232 + LOS Integration)
```mermaid
stateDiagram-v2
    [*] --> IDLE
    
    state "Game Flow" as GF {
        IDLE --> WAITING_START: start_game
        WAITING_START --> SPINNING: start_spin
        SPINNING --> RESULT_READY: set_result[is_valid_result]
        RESULT_READY --> IDLE: reset
    }
    
    state "Signal Processing" as SP {
        state "X2 Processing" as X2 {
            [*] --> X2_WAITING
            X2_WAITING --> X2_RECEIVED: receive_x2
            X2_RECEIVED --> X2_CONFIRMED: receive_x2[count >= 2]
            X2_CONFIRMED --> [*]: start_los_round
        }
        
        state "X5 Processing" as X5 {
            [*] --> X5_WAITING
            X5_WAITING --> X5_RECEIVED: receive_x5
            X5_RECEIVED --> X5_CONFIRMED: receive_x5[count >= 5]
            X5_CONFIRMED --> [*]: submit_result
        }
    }
    
    state "LOS Integration" as LOS {
        state "LOS States" as LS {
            INIT --> BETTING: start_post
            BETTING --> BET_STOPPED: bet_period_expired
            BET_STOPPED --> DEALING: deal_post
            DEALING --> FINISHED: finish_post
        }
    }
    
    X2_CONFIRMED --> WAITING_START: trigger_start
    X5_CONFIRMED --> RESULT_READY: set_wheel_result
    
    state ERROR
    IDLE --> ERROR: handle_error
    WAITING_START --> ERROR: handle_error
    SPINNING --> ERROR: handle_error
    RESULT_READY --> ERROR: handle_error
    ERROR --> IDLE: reset
```

### SicBo Controller (MQTT + IDP + LOS Integration)
```mermaid
stateDiagram-v2
    [*] --> IDLE
    
    state "Game Flow" as GF {
        IDLE --> WAITING_START: start_game
        WAITING_START --> SHAKING: start_shake
        SHAKING --> DETECTING: start_detect
        DETECTING --> RESULT_READY: set_result[is_valid_result]
        RESULT_READY --> IDLE: reset
    }
    
    state "LOS Integration" as LOS {
        state "LOS States" as LS {
            INIT --> BETTING: start_post
            BETTING --> BET_STOPPED: bet_period_expired
            BET_STOPPED --> DEALING: deal_post[dice_detected]
            DEALING --> FINISHED: finish_post
        }
    }
    
    WAITING_START --> BETTING: trigger_los_start
    DETECTING --> DEALING: submit_dice_result
    
    state ERROR
    IDLE --> ERROR: handle_error
    WAITING_START --> ERROR: handle_error
    SHAKING --> ERROR: handle_error
    DETECTING --> ERROR: handle_error
    RESULT_READY --> ERROR: handle_error
    ERROR --> IDLE: reset
```

### Blackjack Controller (HID + LOS Integration)
```mermaid
stateDiagram-v2
    [*] --> TABLE_CLOSED
    
    state "Game Flow" as GF {
        TABLE_CLOSED --> START_GAME: open_table
        START_GAME --> DEAL_CARDS: start_dealing
        DEAL_CARDS --> PLAYER_TURN: start_player_turn[is_initial_deal_complete]
        PLAYER_TURN --> DEALER_TURN: start_dealer_turn[is_player_turn_complete]
        DEALER_TURN --> GAME_RESULT: end_game
        GAME_RESULT --> TABLE_CLOSED: close_table
    }
    
    state "LOS Integration" as LOS {
        state "LOS States" as LS {
            INIT --> BETTING: start_post
            BETTING --> BET_STOPPED: bet_period_expired
            BET_STOPPED --> DEALING: deal_post[all_cards_scanned]
            DEALING --> FINISHED: finish_post
        }
    }
    
    START_GAME --> BETTING: trigger_los_start
    GAME_RESULT --> DEALING: submit_game_result
    
    state ERROR
    TABLE_CLOSED --> ERROR: handle_error
    START_GAME --> ERROR: handle_error
    DEAL_CARDS --> ERROR: handle_error
    PLAYER_TURN --> ERROR: handle_error
    DEALER_TURN --> ERROR: handle_error
    GAME_RESULT --> ERROR: handle_error
    ERROR --> TABLE_CLOSED: reset
```

## LOS API State Machine

```mermaid
stateDiagram-v2
    [*] --> IDLE
    IDLE --> BETTING: start_post
    BETTING --> BET_STOPPED: bet_period_expired
    BET_STOPPED --> DEALING: deal_post
    DEALING --> FINISHED: finish_post
    
    state PAUSED {
        [*] --> PAUSED_STATE
        PAUSED_STATE --> [*]: resume_post
    }
    
    BETTING --> PAUSED: pause_post
    BET_STOPPED --> PAUSED: pause_post
    DEALING --> PAUSED: pause_post
    PAUSED --> PREVIOUS_STATE: resume_post
    
    state VISIBILITY {
        VISIBLE --> INVISIBLE: visibility_post[enable=false]
        INVISIBLE --> VISIBLE: visibility_post[enable=true]
    }
    
    state ERROR {
        [*] --> CANCELLED
        CANCELLED --> [*]: cancel_post
    }
    
    BETTING --> ERROR: handle_error
    BET_STOPPED --> ERROR: handle_error
    DEALING --> ERROR: handle_error
    
    note right of BETTING
        Countdown bet_period
        Check table status
    end note
    
    note right of DEALING
        Send game results
        Update SDP config
    end note
```

## Updated Hierarchical Structure

```mermaid
graph TD
    Main[Main State Machine] --> Roulette[Roulette Controller]
    Main --> SicBo[SicBo Controller]
    Main --> Blackjack[Blackjack Controller]
    
    Roulette --> RS232[RS232 Communication]
    Roulette --> LOS_R[LOS API]
    SicBo --> MQTT[MQTT Protocol]
    SicBo --> IDP[IDP Detection]
    SicBo --> LOS_S[LOS API]
    Blackjack --> HID[HID Scanner]
    Blackjack --> LOS_B[LOS API]
    
    style Main fill:#f9f,stroke:#333,stroke-width:4px
    style Roulette fill:#bbf,stroke:#333
    style SicBo fill:#bbf,stroke:#333
    style Blackjack fill:#bbf,stroke:#333
    style RS232 fill:#dfd,stroke:#333
    style MQTT fill:#dfd,stroke:#333
    style IDP fill:#dfd,stroke:#333
    style HID fill:#dfd,stroke:#333
    style LOS_R fill:#fdd,stroke:#333
    style LOS_S fill:#fdd,stroke:#333
    style LOS_B fill:#fdd,stroke:#333
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

## LOS API State Descriptions

### Game Flow States
- **IDLE**: Initial state waiting for game start
- **BETTING**: Active betting period with countdown
- **BET_STOPPED**: Betting period ended, ready for dealing
- **DEALING**: Processing game results
- **FINISHED**: Round completed

### Control States
- **PAUSED**: Game temporarily suspended
  - Can be triggered from any active state
  - Requires reason for pause
  - Resume returns to previous state

### Visibility States
- **VISIBLE**: Table visible to players
- **INVISIBLE**: Table hidden from players

### Error Handling
- **CANCELLED**: Round cancelled due to error
- Supports round cancellation and recovery

## LOS API Functions
- **start_post**: Initiate new game round
- **deal_post**: Submit game results
- **finish_post**: Complete current round
- **pause_post**: Temporarily suspend game
- **resume_post**: Resume suspended game
- **visibility_post**: Control table visibility
- **cancel_post**: Cancel current round
- **get_roundID**: Check current round status
- **sdp_config_post**: Update game configuration

## Integration Points
Each game controller (Roulette, SicBo, Blackjack) integrates with LOS API for:
- Round management
- Result submission
- State control
- Configuration updates
- Error handling

## State Descriptions

### Roulette Signal States
- **X2 Processing**
  - X2_WAITING: Waiting for X2 signal
  - X2_RECEIVED: First X2 signal received
  - X2_CONFIRMED: Multiple X2 signals confirmed (triggers game start)
- **X5 Processing**
  - X5_WAITING: Waiting for X5 signal
  - X5_RECEIVED: First X5 signal received
  - X5_CONFIRMED: Multiple X5 signals confirmed (triggers result submission)

### LOS Integration States for Each Game
- **INIT**: Initial state before round starts
- **BETTING**: Active betting period
- **BET_STOPPED**: Betting period ended
- **DEALING**: Submitting game results
- **FINISHED**: Round completed

### Integration Points with LOS
1. **Roulette**:
   - X2 signals trigger LOS round start
   - X5 signals trigger result submission
   - Wheel position validation before result submission

2. **SicBo**:
   - Shake command triggers LOS round start
   - IDP detection triggers result submission
   - Dice validation before result submission

3. **Blackjack**:
   - Table opening triggers LOS round start
   - Card scanning during dealing phase
   - Final hand results trigger round completion
