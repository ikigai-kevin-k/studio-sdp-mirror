#!/bin/bash
# Startup script for Mock SBO 001 Daemon Container
# This script manages the daemon container lifecycle

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

# Function to start the daemon
start_daemon() {
    print_status "Starting Mock SBO 001 daemon container..."
    
    # Create directories if they don't exist
    create_directories
    
    # Build and start the container
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    # Wait for container to be ready
    print_status "Waiting for container to be ready..."
    sleep 10
    
    # Check if service is running
    if docker exec "$CONTAINER_NAME" systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Daemon started successfully!"
        print_status "Service status:"
        docker exec "$CONTAINER_NAME" systemctl status "$SERVICE_NAME" --no-pager -l
    else
        print_error "Failed to start daemon service"
        docker compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
}

# Function to stop the daemon
stop_daemon() {
    print_status "Stopping Mock SBO 001 daemon container..."
    docker compose -f "$COMPOSE_FILE" down
    print_success "Daemon stopped successfully"
}

# Function to restart the daemon
restart_daemon() {
    print_status "Restarting Mock SBO 001 daemon container..."
    stop_daemon
    sleep 2
    start_daemon
}

# Function to check daemon status
check_status() {
    print_status "Checking daemon status..."
    
    if docker ps | grep -q "$CONTAINER_NAME"; then
        print_success "Container is running"
        print_status "Service status:"
        docker exec "$CONTAINER_NAME" systemctl status "$SERVICE_NAME" --no-pager -l
    else
        print_warning "Container is not running"
    fi
}

# Function to view logs
view_logs() {
    print_status "Showing daemon logs..."
    docker compose -f "$COMPOSE_FILE" logs -f
}

# Function to show help
show_help() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start the daemon container"
    echo "  stop      Stop the daemon container"
    echo "  restart   Restart the daemon container"
    echo "  status    Check daemon status"
    echo "  logs      View daemon logs"
    echo "  help      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start    # Start the daemon"
    echo "  $0 status   # Check status"
    echo "  $0 logs     # View logs"
}

# Main script logic
main() {
    # Check if Docker is running
    check_docker
    
    case "${1:-start}" in
        start)
            start_daemon
            ;;
        stop)
            stop_daemon
            ;;
        restart)
            restart_daemon
            ;;
        status)
            check_status
            ;;
        logs)
            view_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
