# Testing Guide

This guide explains how to run tests.

## Running Tests

### All Tests

```bash
pytest
```

### Specific Categories

```bash
# Skip slow tests
pytest -m "not slow"

# Integration tests only
pytest -m integration

# Unit tests only
pytest -m unit
```

### With Coverage

```bash
pytest --cov=. --cov-report=html
```

## Test Structure

```python
async def test_functionality():
    """Test description"""
    logger.info("=" * 60)
    logger.info("Testing Functionality")
    logger.info("=" * 60)
    
    try:
        result = await function_under_test()
        assert result is not None
        logger.info("✅ Test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False
```

## Related Documentation

- [Development Setup](setup.md)
- [Contributing Guide](contributing.md)

