#!/bin/bash

# cancel.sh - Cancel action for all environments
# Usage: ./cancel.sh {game_code}
# 
# This script executes cancel action for the specified game_code
# across all environments (CIT, UAT, QAT, STG, PRD, GLC, DEV) in parallel.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Print usage
usage() {
    echo "Usage: $0 {game_code} [env]"
    echo ""
    echo "This script executes cancel action for the specified game_code"
    echo "across all environments (CIT, UAT, QAT, STG, PRD, GLC, DEV) in parallel."
    echo ""
    echo "Note: The env parameter is ignored - cancel will be executed for all environments."
    echo ""
    echo "Example:"
    echo "  $0 Studio-Roulette-Test"
    echo "  $0 Studio-Roulette-Test CIT"
    echo "  $0 SBO-001"
    echo "  $0 ARO-001 UAT"
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
        GLC)
            echo "crystal-table.iki-glc.cc"
            ;;
        DEV)
            echo "crystal-table.iki-dev.cc"
            ;;
        *)
            echo -e "${RED}Error: Unknown environment: $env${NC}" >&2
            return 1
            ;;
    esac
}

# Get access token for a specific environment
get_access_token() {
    local game_code=$1
    local env=$2
    local env_url=$(get_env_url "$env")
    
    if [ $? -ne 0 ]; then
        return 1
    fi
    
    local sessions_url="https://${env_url}/v2/service/sessions"
    
    local response=$(curl -s -X POST "$sessions_url" \
        -H "accept: application/json" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -d "{\"gameCode\": \"$game_code\", \"role\": \"sdp\"}" \
        --insecure)
    
    local token=$(echo "$response" | jq -r '.data.token // empty')
    
    if [ -z "$token" ] || [ "$token" = "null" ]; then
        return 1
    fi
    
    echo "$token"
}

# Execute cancel for a single environment
execute_cancel_for_env() {
    local game_code=$1
    local env=$2
    local env_url=$(get_env_url "$env")
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}[$env] Error: Invalid environment${NC}" >&2
        return 1
    fi
    
    local url="https://${env_url}/v2/service/tables/${game_code}/cancel"
    
    # Get access token
    local token=$(get_access_token "$game_code" "$env")
    if [ -z "$token" ]; then
        echo -e "${RED}[$env] Error: Failed to get access token${NC}" >&2
        return 1
    fi
    
    # Execute cancel
    local response=$(curl -s -X POST "$url" \
        -H "accept: application/json" \
        -H "Bearer: $token" \
        -H "x-signature: los-local-signature" \
        -H "Content-Type: application/json" \
        -H "Cookie: accessToken=$token" \
        -H "Connection: close" \
        -d '{}' \
        --insecure)
    
    # Check if there's an error in the response
    local error=$(echo "$response" | jq -r '.error.message // empty')
    if [ -n "$error" ] && [ "$error" != "null" ]; then
        echo -e "${RED}[$env] Error: $error${NC}" >&2
        echo "$response" | jq . >&2
        return 1
    fi
    
    # Success
    echo -e "${GREEN}[$env] Cancel executed successfully${NC}" >&2
    echo "$response" | jq . >&2
    return 0
}

# Main function
main() {
    # Check dependencies
    check_dependencies
    
    # Check arguments
    if [ $# -lt 1 ]; then
        usage
    fi
    
    local game_code=$1
    # Note: env parameter ($2) is ignored - always execute for all environments
    
    # All environments
    local environments=("CIT" "UAT" "QAT" "STG" "PRD" "GLC" "DEV")
    
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}Canceling $game_code across all environments${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    
    # Array to store PIDs
    declare -a pids=()
    declare -a envs=()
    
    # Execute cancel for each environment in parallel
    for env in "${environments[@]}"; do
        (
            execute_cancel_for_env "$game_code" "$env"
        ) &
        pids+=($!)
        envs+=("$env")
    done
    
    # Wait for all background jobs to complete
    local success_count=0
    local fail_count=0
    
    for i in "${!pids[@]}"; do
        local pid=${pids[$i]}
        local env=${envs[$i]}
        
        if wait $pid; then
            ((success_count++))
        else
            ((fail_count++))
        fi
    done
    
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}Summary${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo -e "${GREEN}Successful: $success_count${NC}"
    if [ $fail_count -gt 0 ]; then
        echo -e "${RED}Failed: $fail_count${NC}"
    fi
    echo -e "${CYAN}Total: ${#environments[@]}${NC}"
    echo ""
    
    # Return non-zero exit code if any failed
    if [ $fail_count -gt 0 ]; then
        exit 1
    fi
}

# Run main function
main "$@"

