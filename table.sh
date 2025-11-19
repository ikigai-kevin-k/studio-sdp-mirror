#!/bin/bash

# table.sh - Table API execution script
# Usage: ./table.sh {game_code} {env} {action} [additional_args...]
# 
# game_code: ARO-001/ARO-002/SBO-001/Studio-Roulette-Test
# env: CIT/UAT/QAT/STG/PRD
# action: start/betStop/deal/finish/broadcast/pause/resume/cancel/sessions
#
# Additional args for specific actions:
#   - deal: roundId result (e.g., "round-123" "[1,2,3]")
#   - pause: reason (e.g., "Test pause")
#   - broadcast: broadcast_type [audience] [afterSeconds] (e.g., "dice.reshake" "players" 20)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print usage
usage() {
    echo "Usage: $0 {game_code} {env} {action} [additional_args...]"
    echo ""
    echo "Arguments:"
    echo "  game_code: ARO-001, ARO-002, SBO-001, Studio-Roulette-Test"
    echo "  env:       CIT, UAT, QAT, STG, PRD"
    echo "  action:    start, betStop, deal, finish, broadcast, pause, resume, cancel, sessions, getRoundId"
    echo ""
    echo "Additional arguments for specific actions:"
    echo "  deal:      [roundId] result"
    echo "            If roundId is omitted, it will be automatically fetched using getRoundId"
    echo "            SicBo example: ./table.sh SBO-001 CIT deal \"[1,2,3]\""
    echo "            SicBo with roundId: ./table.sh SBO-001 CIT deal \"round-123\" \"[1,2,3]\""
    echo "            Roulette example: ./table.sh Studio-Roulette-Test CIT deal \"0\""
    echo "            Roulette with roundId: ./table.sh Studio-Roulette-Test CIT deal \"round-123\" \"0\""
    echo ""
    echo "  pause:     reason"
    echo "            Example: ./table.sh Studio-Roulette-Test CIT pause \"Test pause\""
    echo ""
    echo "  broadcast: broadcast_type [audience] [afterSeconds]"
    echo "            Example: ./table.sh SBO-001 CIT broadcast \"dice.reshake\" \"players\" 20"
    echo ""
    exit 1
}

# Check if jq is installed
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        echo -e "${RED}Error: jq is not installed. Please install jq first.${NC}"
        echo "  Ubuntu/Debian: sudo apt-get install jq"
        echo "  macOS: brew install jq"
        exit 1
    fi
}

# Get environment URL
get_env_url() {
    local env=$1
    case "$env" in
        CIT)
            echo "crystal-table.iki-cit.cc"
            ;;
        UAT)
            echo "crystal-table.iki-uat.cc"
            ;;
        QAT)
            echo "crystal-table.iki-qat.cc"
            ;;
        STG)
            echo "crystal-table.iki-stg.cc"
            ;;
        PRD)
            echo "crystal-table.ikg-game.cc"
            ;;
        *)
            echo -e "${RED}Error: Unknown environment: $env${NC}" >&2
            echo "Supported environments: CIT, UAT, QAT, STG, PRD"
            exit 1
            ;;
    esac
}

# Get access token
get_access_token() {
    local game_code=$1
    local env=$2
    local env_url=$(get_env_url "$env")
    local sessions_url="https://${env_url}/v2/service/sessions"
    
    echo -e "${YELLOW}Getting access token for $game_code in $env environment...${NC}" >&2
    
    local response=$(curl -s -X POST "$sessions_url" \
        -H "accept: application/json" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -d "{\"gameCode\": \"$game_code\", \"role\": \"sdp\"}" \
        --insecure)
    
    local token=$(echo "$response" | jq -r '.data.token // empty')
    
    if [ -z "$token" ] || [ "$token" = "null" ]; then
        echo -e "${RED}Error: Failed to get access token${NC}" >&2
        echo "Response: $response" >&2
        exit 1
    fi
    
    echo "$token"
}

# Execute sessions action (just get token)
execute_sessions() {
    local game_code=$1
    local env=$2
    local token=$(get_access_token "$game_code" "$env")
    echo "$token"
}

# Execute start action
execute_start() {
    local game_code=$1
    local env=$2
    local token=$3
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}/start"
    
    echo -e "${YELLOW}Executing start for $game_code in $env...${NC}" >&2
    
    curl -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: Bearer $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d '{}' \
        --insecure | jq .
}

# Execute betStop action
execute_bet_stop() {
    local game_code=$1
    local env=$2
    local token=$3
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}/bet-stop"
    
    echo -e "${YELLOW}Executing betStop for $game_code in $env...${NC}" >&2
    
    curl -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d '{}' \
        --insecure | jq .
}

# Determine game type based on game_code
get_game_type() {
    local game_code=$1
    case "$game_code" in
        SBO-001)
            echo "sicbo"
            ;;
        ARO-001|ARO-002|ARO-003|ARO-004|ARO-005|ARO-006|ARO-007|Studio-Roulette-Test)
            echo "roulette"
            ;;
        *)
            # Check if game_code contains "Roulette" (case insensitive)
            if echo "$game_code" | grep -qi "roulette"; then
                echo "roulette"
            else
                # Default to sicbo for unknown game codes
                echo "sicbo"
            fi
            ;;
    esac
}

# Get current round ID (internal function, can be called silently)
_get_round_id_internal() {
    local game_code=$1
    local env=$2
    local token=$3
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}"
    
    local response=$(curl -s -X GET "$url" \
        -H "accept: application/json" \
        -H "Bearer: Bearer $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        --insecure)
    
    # Extract roundId
    echo "$response" | jq -r '.data.table.tableRound.roundId // empty'
}

# Get current round ID (public function with full output)
execute_get_round_id() {
    local game_code=$1
    local env=$2
    local token=$3
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}"
    
    echo -e "${YELLOW}Getting current round ID for $game_code in $env...${NC}" >&2
    
    local response=$(curl -s -X GET "$url" \
        -H "accept: application/json" \
        -H "Bearer: Bearer $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        --insecure)
    
    # Pretty print the response
    echo "$response" | jq .
    
    # Extract roundId
    local round_id=$(echo "$response" | jq -r '.data.table.tableRound.roundId // empty')
    local status=$(echo "$response" | jq -r '.data.table.tableRound.status // empty')
    local bet_period=$(echo "$response" | jq -r '.data.table.betPeriod // empty')
    
    if [ -z "$round_id" ] || [ "$round_id" = "null" ]; then
        echo -e "${RED}Error: Failed to get roundId from response${NC}" >&2
        return 1
    fi
    
    echo -e "${GREEN}Round ID: $round_id${NC}" >&2
    echo -e "${GREEN}Status: $status${NC}" >&2
    echo -e "${GREEN}Bet Period: $bet_period${NC}" >&2
    
    # Return round_id for use in other functions (on stdout, last line)
    echo "$round_id"
}

# Execute deal action
execute_deal() {
    local game_code=$1
    local env=$2
    local token=$3
    local round_id=$4
    local result=$5
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}/deal"
    local timecode=$(date +%s)000
    local game_type=$(get_game_type "$game_code")
    
    # If result is provided but round_id is empty, try to auto-fetch round_id
    if [ -z "$round_id" ] && [ -n "$result" ]; then
        echo -e "${YELLOW}Round ID not provided, fetching current round ID...${NC}" >&2
        round_id=$(_get_round_id_internal "$game_code" "$env" "$token")
        if [ -z "$round_id" ] || [ "$round_id" = "null" ]; then
            echo -e "${RED}Error: Failed to get roundId automatically. Please provide roundId manually.${NC}" >&2
            exit 1
        fi
        echo -e "${GREEN}Using round ID: $round_id${NC}" >&2
    fi
    
    if [ -z "$result" ]; then
        echo -e "${RED}Error: deal action requires result${NC}" >&2
        echo "Usage: $0 $game_code $env deal [roundId] <result>"
        if [ "$game_type" = "sicbo" ]; then
            echo "Example (SicBo, auto roundId): $0 SBO-001 CIT deal \"[1,2,3]\""
            echo "Example (SicBo, with roundId): $0 SBO-001 CIT deal \"round-123\" \"[1,2,3]\""
        else
            echo "Example (Roulette, auto roundId): $0 Studio-Roulette-Test CIT deal \"0\""
            echo "Example (Roulette, with roundId): $0 Studio-Roulette-Test CIT deal \"round-123\" \"0\""
        fi
        exit 1
    fi
    
    echo -e "${YELLOW}Executing deal for $game_code ($game_type) in $env...${NC}" >&2
    echo -e "${YELLOW}Round ID: $round_id, Result: $result${NC}" >&2
    
    # Build payload based on game type
    local payload
    if [ "$game_type" = "sicbo" ]; then
        # SicBo format: {"roundId": "...", "sicBo": [1,2,3]}
        payload="{\"roundId\": \"$round_id\", \"sicBo\": $result}"
    else
        # Roulette format: {"roundId": "...", "roulette": "0"}
        # Ensure result is a string for roulette
        payload="{\"roundId\": \"$round_id\", \"roulette\": \"$result\"}"
    fi
    
    curl -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "timecode: $timecode" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d "$payload" \
        --insecure | jq .
}

# Execute finish action
execute_finish() {
    local game_code=$1
    local env=$2
    local token=$3
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}/finish"
    
    echo -e "${YELLOW}Executing finish for $game_code in $env...${NC}" >&2
    
    curl -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d '{}' \
        --insecure | jq .
}

# Execute pause action
execute_pause() {
    local game_code=$1
    local env=$2
    local token=$3
    local reason=$4
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}/pause"
    
    if [ -z "$reason" ]; then
        reason="Pause request"
    fi
    
    echo -e "${YELLOW}Executing pause for $game_code in $env...${NC}" >&2
    echo -e "${YELLOW}Reason: $reason${NC}" >&2
    
    curl -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d "{\"reason\": \"$reason\"}" \
        --insecure | jq .
}

# Execute resume action
execute_resume() {
    local game_code=$1
    local env=$2
    local token=$3
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}/resume"
    
    echo -e "${YELLOW}Executing resume for $game_code in $env...${NC}" >&2
    
    curl -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d '{}' \
        --insecure | jq .
}

# Execute cancel action
execute_cancel() {
    local game_code=$1
    local env=$2
    local token=$3
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}/cancel"
    
    echo -e "${YELLOW}Executing cancel for $game_code in $env...${NC}" >&2
    
    curl -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d '{}' \
        --insecure | jq .
}

# Get broadcast metadata based on broadcast_type
get_broadcast_metadata() {
    local broadcast_type=$1
    case "$broadcast_type" in
        dice.reshake|dice.reroll|sicbo.reshake)
            echo '{"msgId": "SICBO_INVALID_AFTER_RESHAKE", "content": "Sicbo invalid result after reshake", "metadata": {"title": "SICBO RESHAKE", "description": "Invalid result detected, reshaking dice", "code": "SBE.1", "suggestion": "Dice will be reshaken shortly", "signalType": "warning"}}'
            ;;
        sicbo.invalid_result)
            echo '{"msgId": "SICBO_INVALID_RESULT", "content": "Sicbo invalid result error", "metadata": {"title": "SICBO INVALID RESULT", "description": "Invalid result detected", "code": "SBE.2", "suggestion": "Please check the result", "signalType": "warning"}}'
            ;;
        dice.no_shake|sicbo.no_shake)
            echo '{"msgId": "SICBO_NO_SHAKE", "content": "Sicbo no shake error", "metadata": {"title": "SICBO NO SHAKE", "description": "Dice shaker did not shake", "code": "SBE.3", "suggestion": "Check the shaker mechanism", "signalType": "warning"}}'
            ;;
        *)
            echo '{"msgId": "SICBO_INVALID_AFTER_RESHAKE", "content": "Broadcast notification: '"$broadcast_type"'", "metadata": {"title": "BROADCAST NOTIFICATION", "description": "Broadcast message: '"$broadcast_type"'", "code": "BRD.1", "suggestion": "Please check the game status", "signalType": "warning"}}'
            ;;
    esac
}

# Execute broadcast action
execute_broadcast() {
    local game_code=$1
    local env=$2
    local token=$3
    local broadcast_type=$4
    local audience=${5:-"players"}
    local after_seconds=${6:-20}
    local env_url=$(get_env_url "$env")
    local url="https://${env_url}/v2/service/tables/${game_code}/broadcast"
    
    if [ -z "$broadcast_type" ]; then
        echo -e "${RED}Error: broadcast action requires broadcast_type${NC}" >&2
        echo "Usage: $0 $game_code $env broadcast <broadcast_type> [audience] [afterSeconds]"
        echo "Example: $0 SBO-001 CIT broadcast \"dice.reshake\" \"players\" 20"
        exit 1
    fi
    
    echo -e "${YELLOW}Executing broadcast for $game_code in $env...${NC}" >&2
    echo -e "${YELLOW}Broadcast Type: $broadcast_type, Audience: $audience, After Seconds: $after_seconds${NC}" >&2
    
    # Get base metadata
    local base_metadata=$(get_broadcast_metadata "$broadcast_type")
    
    # Add audience and afterSeconds to metadata
    local payload=$(echo "$base_metadata" | jq --arg audience "$audience" --argjson afterSeconds "$after_seconds" \
        '.metadata.audience = $audience | .metadata.afterSeconds = $afterSeconds')
    
    curl -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d "$payload" \
        --insecure | jq .
}

# Main function
main() {
    # Check dependencies
    check_dependencies
    
    # Check arguments
    if [ $# -lt 3 ]; then
        usage
    fi
    
    local game_code=$1
    local env=$2
    local action=$3
    shift 3
    local additional_args=("$@")
    
    # Validate environment
    case "$env" in
        CIT|UAT|QAT|STG|PRD)
            ;;
        *)
            echo -e "${RED}Error: Invalid environment: $env${NC}" >&2
            echo "Supported environments: CIT, UAT, QAT, STG, PRD"
            exit 1
            ;;
    esac
    
    # Validate action
    case "$action" in
        start|betStop|deal|finish|broadcast|pause|resume|cancel|sessions|getRoundId)
            ;;
        *)
            echo -e "${RED}Error: Invalid action: $action${NC}" >&2
            echo "Supported actions: start, betStop, deal, finish, broadcast, pause, resume, cancel, sessions, getRoundId"
            exit 1
            ;;
    esac
    
    # Get access token (except for sessions action which just returns token)
    local token
    if [ "$action" = "sessions" ]; then
        token=$(execute_sessions "$game_code" "$env")
        echo -e "${GREEN}Access Token:${NC}"
        echo "$token"
        exit 0
    else
        token=$(get_access_token "$game_code" "$env")
        echo -e "${GREEN}Access Token obtained successfully${NC}" >&2
    fi
    
    # Execute action
    case "$action" in
        start)
            execute_start "$game_code" "$env" "$token"
            ;;
        betStop)
            execute_bet_stop "$game_code" "$env" "$token"
            ;;
        deal)
            # Handle deal arguments: if 1 arg -> result only (auto-fetch roundId)
            #                        if 2 args -> roundId and result
            if [ ${#additional_args[@]} -eq 1 ]; then
                # Only result provided, roundId will be auto-fetched
                execute_deal "$game_code" "$env" "$token" "" "${additional_args[0]}"
            elif [ ${#additional_args[@]} -eq 2 ]; then
                # Both roundId and result provided
                execute_deal "$game_code" "$env" "$token" "${additional_args[0]}" "${additional_args[1]}"
            else
                echo -e "${RED}Error: deal action requires at least result argument${NC}" >&2
                echo "Usage: $0 $game_code $env deal [roundId] <result>"
                exit 1
            fi
            ;;
        finish)
            execute_finish "$game_code" "$env" "$token"
            ;;
        pause)
            execute_pause "$game_code" "$env" "$token" "${additional_args[0]}"
            ;;
        resume)
            execute_resume "$game_code" "$env" "$token"
            ;;
        cancel)
            execute_cancel "$game_code" "$env" "$token"
            ;;
        broadcast)
            execute_broadcast "$game_code" "$env" "$token" "${additional_args[0]}" "${additional_args[1]}" "${additional_args[2]}"
            ;;
        getRoundId)
            execute_get_round_id "$game_code" "$env" "$token"
            ;;
    esac
}

# Run main function
main "$@"

