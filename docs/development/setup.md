# Development Setup

This guide explains how to set up a development environment.

## Prerequisites

- Python 3.12+
- Git
- Virtual environment tool

## Setup Steps

### 1. Clone Repository

```bash
git clone https://github.com/studio-sdp/studio-sdp-roulette.git
cd studio-sdp-roulette
```

### 2. Create Virtual Environment

```bash
python3 -m venv ~/sdp-env
source ~/sdp-env/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

### 4. Verify Setup

```bash
pytest --version
black --version
flake8 --version
mypy --version
```

## Development Tools

- **pytest** - Testing framework
- **black** - Code formatter
- **flake8** - Linter
- **mypy** - Type checker

## Related Documentation

- [Code Style Guide](code-style.md)
- [Testing Guide](testing.md)
- [Contributing Guide](contributing.md)

