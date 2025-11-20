# Table API Reference

Complete Live Backend Service API integration documentation for game round management.

## Overview

The Table API (also known as Live Backend Service API) provides endpoints for managing game rounds across different game types and environments. It supports:

- **Sicbo** (SBO-*) - Dice game management
- **Speed Roulette** (ARO-*) - Speed roulette game management
- **VIP Roulette** (ARO-*) - VIP roulette game management
- **Baccarat** (BAC-*) - Baccarat game management

## Authentication

All Table API requests require authentication via access token obtained from the session endpoint:

```python
from table_api.get_access_token import get_access_token

token = get_access_token(
    url="https://crystal-table.iki-cit.cc/v2/service/sessions",
    game_code="SBO-001",
    role="sdp"
)
```

## Game Round Management

### Start Round

Initiate a new game round.

```python
from table_api.sb.api_v2_sb import start_post_v2

round_id, bet_period = await start_post_v2(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token
)
```

**Endpoint**: `POST {base_url}/start`

**Response**:
```json
{
    "data": {
        "table": {
            "tableRound": {
                "roundId": "round-12345"
            },
            "betPeriod": "betting"
        }
    }
}
```

### Deal Result

Submit game results for the current round.

```python
from table_api.sb.api_v2_sb import deal_post_v2

# Sicbo result
result = {"dice1": 1, "dice2": 2, "dice3": 3}
success = await deal_post_v2(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token,
    round_id=round_id,
    result=result
)
```

**Endpoint**: `POST {base_url}/deal`

**Request Body** (Sicbo):
```json
{
    "roundId": "round-12345",
    "sicBo": {
        "dice1": 1,
        "dice2": 2,
        "dice3": 3
    }
}
```

**Request Body** (Roulette):
```json
{
    "roundId": "round-12345",
    "roulette": {
        "winningNumber": 7
    }
}
```

### Finish Round

Complete the current game round.

```python
from table_api.sb.api_v2_sb import finish_post_v2

success = await finish_post_v2(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token
)
```

**Endpoint**: `POST {base_url}/finish`

### Get Round Information

Query current round status and information.

```python
from table_api.sb.api_v2_sb import get_roundID_v2

round_id, status, bet_period = await get_roundID_v2(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token
)
```

**Endpoint**: `GET {base_url}`

**Response**:
```json
{
    "data": {
        "table": {
            "tableRound": {
                "roundId": "round-12345",
                "status": "start"
            },
            "betPeriod": "betting"
        }
    }
}
```

## Table Operations

### Pause Round

Temporarily pause the current game round.

```python
from table_api.sb.api_v2_sb import pause_post_v2

success = await pause_post_v2(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token
)
```

**Endpoint**: `POST {base_url}/pause`

### Resume Round

Resume a paused game round.

```python
from table_api.sb.api_v2_sb import resume_post_v2

success = await resume_post_v2(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token
)
```

**Endpoint**: `POST {base_url}/resume`

### Cancel Round

Cancel the current game round.

```python
from table_api.sb.api_v2_sb import cancel_post_v2

success = await cancel_post_v2(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token
)
```

**Endpoint**: `POST {base_url}/cancel`

### Set Table Visibility

Control table visibility for players.

```python
from table_api.sb.api_v2_sb import visibility_post

# Enable visibility
await visibility_post(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token,
    enable=True
)

# Disable visibility
await visibility_post(
    url="https://crystal-table.iki-cit.cc/v2/service/tables/SBO-001",
    token=access_token,
    enable=False
)
```

**Endpoint**: `POST {base_url}/visibility`

**Request Body**:
```json
{
    "visibility": "visible"  // or "disabled"
}
```

## State Machine

The Table API uses a state machine to manage game round state transitions:

### Normal Flow

```
START → DEAL → BET_STOPPED → FINISHED → START
```

### Exception Flow

```
Any State → BROADCAST → PAUSE → CANCEL → START
```

### State Transitions

- `START` → `DEAL`, `BROADCAST`
- `DEAL` → `BET_STOPPED`, `BROADCAST`
- `BET_STOPPED` → `FINISHED`, `BROADCAST`
- `FINISHED` → `START`, `BROADCAST`
- `BROADCAST` → `PAUSE`, `DEAL`, `BET_STOPPED`, `FINISHED`, `START`
- `PAUSE` → `CANCEL`
- `CANCEL` → `START`

## Environment Support

The Table API supports multiple environments:

- **CIT** - Development environment
- **UAT** - User acceptance testing
- **PRD** - Production environment
- **STG** - Staging environment
- **QAT** - Quality assurance testing
- **GLC** - Global environment

Each environment has its own base URL and configuration.

## Error Handling

All API methods include error handling and return appropriate status codes:

- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Internal Server Error

## Related Documentation

- [State Machine Guide](../../state_machine/README.md)
- [Table API State Machine](../../state_machine/table_api_state_machine.py)
- [Table API Documentation](../../TABLEAPI_DOC/)
