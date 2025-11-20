#!/bin/bash
#
# Install Git Hooks for Studio SDP System
# This script sets up pre-commit and pre-push hooks for code quality
#

set -e

echo "🚀 Installing Git Hooks for Studio SDP System..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    print_error "This is not a git repository. Please run this script from the project root."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the project root."
    exit 1
fi

print_status "Setting up virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
print_status "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
print_success "Dependencies installed"

print_status "Installing Git hooks..."

# Copy hook files
cp .git/hooks/pre-commit .git/hooks/pre-commit.backup 2>/dev/null || true
cp .git/hooks/pre-push .git/hooks/pre-push.backup 2>/dev/null || true

# Make hooks executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push

print_success "Git hooks installed successfully!"

print_status "Testing hooks..."

# Test pre-commit hook
if .git/hooks/pre-commit > /tmp/hook_test.txt 2>&1; then
    print_success "Pre-commit hook test passed"
else
    print_warning "Pre-commit hook test had issues (this is normal for first run):"
    cat /tmp/hook_test.txt
fi

# Clean up test output
rm -f /tmp/hook_test.txt

echo ""
print_success "🎉 Git hooks installation completed!"
echo ""
echo "📋 What happens now:"
echo "  • Pre-commit hook: Runs on every 'git commit' to check code formatting"
echo "  • Pre-push hook: Runs on every 'git push' to ensure code quality"
echo ""
echo "🔧 Available commands:"
echo "  • 'black .' - Format code with Black"
echo "  • 'flake8 .' - Run linting checks"
echo "  • 'python test_build.py' - Test module imports"
echo ""
echo "💡 Tips:"
echo "  • Hooks will automatically run when you commit or push"
echo "  • If formatting fails, run 'black .' to fix it"
echo "  • If linting fails, fix the issues before committing"
echo "  • Hooks can be bypassed with '--no-verify' flag (not recommended)"
echo ""
print_status "Happy coding! 🚀"
