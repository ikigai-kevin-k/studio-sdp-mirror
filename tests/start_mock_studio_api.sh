#!/bin/bash
# Quick start script for Mock StudioAPI Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

echo "🚀 Starting Mock StudioAPI Server..."
echo "📋 Usage:"
echo "  - Basic: python tests/mock_studio_api_server.py"
echo "  - Interactive: python tests/mock_studio_api_server.py --interactive"
echo "  - Auto send: python tests/mock_studio_api_server.py --send-sdp-down --table-id ARO-001"
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start the server with interactive mode by default
python tests/mock_studio_api_server.py --interactive "$@"

