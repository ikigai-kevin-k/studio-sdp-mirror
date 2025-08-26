#!/bin/bash
# Test script to verify boot autostart functionality
# This script tests if the mock_SBO_001_1.py daemon service starts automatically on container boot

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CONTAINER_NAME="kevin-sdp-daemon"
SERVICE_NAME="mock-sbo-001.service"
COMPOSE_FILE="docker-compose.yml"

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

# Function to wait for service to be ready
wait_for_service() {
    local max_attempts=30
    local attempt=1
    
    print_status "Waiting for service to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker exec "$CONTAINER_NAME" systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
            print_success "Service is now active after $attempt attempts"
            return 0
        fi
        
        print_status "Attempt $attempt/$max_attempts: Service not ready yet, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_error "Service failed to start within expected time"
    return 1
}

# Test 1: Initial container startup
test_initial_startup() {
    print_test_header "Initial Container Startup Test"
    
    print_status "Starting container for the first time..."
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    print_status "Waiting for container to be ready..."
    sleep 15
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        print_success "Container is running"
    else
        print_error "Container failed to start"
        return 1
    fi
    
    # Wait for service to be ready
    if wait_for_service; then
        print_success "Service started automatically on container boot"
        
        # Show service status
        print_status "Service status:"
        docker exec "$CONTAINER_NAME" systemctl status "$SERVICE_NAME" --no-pager -l || true
        
        # Show service logs
        print_status "Recent service logs:"
        docker exec "$CONTAINER_NAME" journalctl -u "$SERVICE_NAME" --no-pager -n 10 || true
        
        return 0
    else
        print_error "Service failed to start automatically"
        return 1
    fi
}

# Test 2: Container restart test
test_container_restart() {
    print_test_header "Container Restart Test"
    
    print_status "Restarting container..."
    docker compose -f "$COMPOSE_FILE" restart
    
    print_status "Waiting for container to be ready after restart..."
    sleep 15
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        print_success "Container restarted successfully"
    else
        print_error "Container failed to restart"
        return 1
    fi
    
    # Wait for service to be ready
    if wait_for_service; then
        print_success "Service started automatically after container restart"
        
        # Show service status
        print_status "Service status after restart:"
        docker exec "$CONTAINER_NAME" systemctl status "$SERVICE_NAME" --no-pager -l || true
        
        return 0
    else
        print_error "Service failed to start automatically after restart"
        return 1
    fi
}

# Test 3: Service restart test
test_service_restart() {
    print_test_header "Service Restart Test"
    
    print_status "Restarting the daemon service..."
    docker exec "$CONTAINER_NAME" systemctl restart "$SERVICE_NAME"
    
    print_status "Waiting for service to be ready after service restart..."
    sleep 5
    
    if docker exec "$CONTAINER_NAME" systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service restarted successfully"
        
        # Show service status
        print_status "Service status after service restart:"
        docker exec "$CONTAINER_NAME" systemctl status "$SERVICE_NAME" --no-pager -l || true
        
        return 0
    else
        print_error "Service failed to restart"
        return 1
    fi
}

# Test 4: Boot sequence verification
test_boot_sequence() {
    print_test_header "Boot Sequence Verification"
    
    print_status "Checking systemd boot sequence..."
    
    # Check if service is enabled
    if docker exec "$CONTAINER_NAME" systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        print_success "Service is enabled for boot"
    else
        print_error "Service is not enabled for boot"
        return 1
    fi
    
    # Check service dependencies
    print_status "Checking service dependencies..."
    docker exec "$CONTAINER_NAME" systemctl list-dependencies "$SERVICE_NAME" --no-pager || true
    
    # Check service configuration
    print_status "Checking service configuration..."
    docker exec "$CONTAINER_NAME" systemctl cat "$SERVICE_NAME" --no-pager || true
    
    return 0
}

# Test 5: Log verification
test_log_verification() {
    print_test_header "Log Verification Test"
    
    print_status "Checking daemon logs..."
    
    # Check container logs
    print_status "Container logs:"
    docker compose -f "$COMPOSE_FILE" logs --tail=20 || true
    
    # Check service logs
    print_status "Service logs:"
    docker exec "$CONTAINER_NAME" journalctl -u "$SERVICE_NAME" --no-pager --tail=20 || true
    
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
    print_status "Starting Mock SBO 001 Daemon Boot Autostart Tests"
    print_status "Container name: $CONTAINER_NAME"
    print_status "Service name: $SERVICE_NAME"
    
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
    
    # Test 3: Service restart
    if test_service_restart; then
        test_results+=("Service Restart: PASS")
    else
        test_results+=("Service Restart: FAIL")
    fi
    
    # Test 4: Boot sequence
    if test_boot_sequence; then
        test_results+=("Boot Sequence: PASS")
    else
        test_results+=("Boot Sequence: FAIL")
    fi
    
    # Test 5: Log verification
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
        print_success "All tests passed! The daemon service starts automatically on boot."
    else
        print_warning "Some tests failed. Check the output above for details."
    fi
    
    echo -e "\n${BLUE}To clean up:${NC}"
    echo -e "Run: ./start-daemon.sh stop"
}

# Run main function
main "$@"
