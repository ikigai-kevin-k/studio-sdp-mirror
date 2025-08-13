# Studio API package for SDP Roulette System
# This package provides API functions for Studio API endpoints

# Import healthcheck functions
from .api import (
    healthcheck_get_v1,
    table_get_v1,
    table_post_v1,
    table_patch_v1,
)

__all__ = [
    # Standard API
    "healthcheck_get_v1",
    "table_get_v1",
    "table_post_v1",
    "table_patch_v1",
]

# Version information
__version__ = "1.0.0"
__author__ = "Studio SDP Team"
