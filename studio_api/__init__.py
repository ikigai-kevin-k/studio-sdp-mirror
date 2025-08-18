# Studio API package for SDP Roulette System
# This package provides API functions for Studio API endpoints

# Version information
__version__ = "1.0.0"
__author__ = "Kevin Kuo (Studio Team)"

# Conditional imports to avoid dependency issues in test environment
try:
    # Import healthcheck functions
    from .api import (
        healthcheck_get_v1,  # noqa: F401
        table_get_v1,  # noqa: F401
        table_post_v1,  # noqa: F401
        table_patch_v1,  # noqa: F401
    )

    __all__ = [
        # Standard API
        "healthcheck_get_v1",
        "table_get_v1",
        "table_post_v1",
        "table_patch_v1",
    ]
except ImportError:
    # In test environment or when dependencies are not available
    __all__ = []
