#!/bin/bash
# Simple test script for Mock SBO 001 Daemon Container
# This script tests if the daemon starts automatically on container boot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="kevin-sdp-daemon"
COMPOSE_FILE="docker-compose.simple.yml"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_test_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  TEST: $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    mkdir -p logs run
    print_success "Directories created successfully"
}

# Function to wait for daemon to be ready
wait_for_daemon() {
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for daemon to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec "$CONTAINER_NAME" pgrep -f "mock_SBO_001_1.py" >/dev/null 2>&1; then
            print_success "Daemon is now running after $attempt attempts"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts: Daemon not ready yet, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Daemon failed to start within expected time"
    return 1
}

# Test 1: Initial container startup
test_initial_startup() {
    print_test_header "Initial Container Startup Test"
    
    print_status "Starting container for the first time..."
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    print_status "Waiting for container to be ready..."
    sleep 10
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        print_success "Container is running"
    else
        print_error "Container failed to start"
        return 1
    fi
    
    # Wait for daemon to be ready
    if wait_for_daemon; then
        print_success "Daemon started automatically on container boot"
        
        # Show daemon process
        print_status "Daemon process:"
        docker exec "$CONTAINER_NAME" ps aux | grep mock_SBO_001_1.py || true
        
        return 0
    else
        print_error "Daemon failed to start automatically"
        return 1
    fi
}

# Test 2: Container restart test
test_container_restart() {
    print_test_header "Container Restart Test"
    
    print_status "Restarting container..."
    docker compose -f "$COMPOSE_FILE" restart
    
    print_status "Waiting for container to be ready after restart..."
    sleep 10
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        print_success "Container restarted successfully"
    else
        print_error "Container failed to restart"
        return 1
    fi
    
    # Wait for daemon to be ready
    if wait_for_daemon; then
        print_success "Daemon started automatically after container restart"
        
        # Show daemon process
        print_status "Daemon process after restart:"
        docker exec "$CONTAINER_NAME" ps aux | grep mock_SBO_001_1.py || true
        
        return 0
    else
        print_error "Daemon failed to start automatically after restart"
        return 1
    fi
}

# Test 3: Log verification
test_log_verification() {
    print_test_header "Log Verification Test"
    
    print_status "Checking daemon logs..."
    
    # Check container logs
    print_status "Container logs:"
    docker compose -f "$COMPOSE_FILE" logs --tail=20 || true
    
    # Check if log file exists
    if docker exec "$CONTAINER_NAME" test -f /var/log/mock_sbo_001.log; then
        print_success "Daemon log file exists"
        print_status "Recent daemon log entries:"
        docker exec "$CONTAINER_NAME" tail -10 /var/log/mock_sbo_001.log || true
    else
        print_warning "Daemon log file not found"
    fi
    
    return 0
}

# Main test execution
main() {
    print_status "Starting Mock SBO 001 Daemon Simple Boot Autostart Tests"
    print_status "Container name: $CONTAINER_NAME"
    print_status "Using simplified approach without systemd"
    
    # Check prerequisites
    check_docker
    create_directories
    
    # Run tests
    local test_results=()
    
    print_status "Running tests..."
    
    # Test 1: Initial startup
    if test_initial_startup; then
        test_results+=("Initial Startup: PASS")
    else
        test_results+=("Initial Startup: FAIL")
    fi
    
    # Test 2: Container restart
    if test_container_restart; then
        test_results+=("Container Restart: PASS")
    else
        test_results+=("Container Restart: FAIL")
    fi
    
    # Test 3: Log verification
    if test_log_verification; then
        test_results+=("Log Verification: PASS")
    else
        test_results+=("Log Verification: FAIL")
    fi
    
    # Display test results
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  TEST RESULTS SUMMARY${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    for result in "${test_results[@]}"; do
        if [[ $result == *"PASS"* ]]; then
            print_success "$result"
        else
            print_error "$result"
        fi
    done
    
    # Count results
    local total_tests=${#test_results[@]}
    local passed_tests=$(echo "${test_results[@]}" | grep -o "PASS" | wc -l)
    local failed_tests=$((total_tests - passed_tests))
    
    echo -e "\n${BLUE}Summary:${NC}"
    echo -e "Total tests: $total_tests"
    echo -e "Passed: $passed_tests"
    echo -e "Failed: $failed_tests"
    
    if [ $failed_tests -eq 0 ]; then
        print_success "All tests passed! The daemon starts automatically on boot."
    else
        print_warning "Some tests failed. Check the output above for details."
    fi
    
    echo -e "\n${BLUE}To clean up:${NC}"
    echo -e "Run: docker compose -f $COMPOSE_FILE down"
}

# Run main function
main "$@"
