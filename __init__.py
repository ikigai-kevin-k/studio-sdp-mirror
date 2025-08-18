# Studio SDP Roulette System Package
# This file ensures that all modules are properly recognized as part of the
# package

# Package metadata
__version__ = "0.1.0"
__author__ = "Kevin Kuo (Studio Team)"
__description__ = (
    "SDP Game System with Roulette, SicBo, and Baccarat Controllers"
)

# Conditional imports to avoid issues in test environment
try:
    # Import main modules to make them available
    from . import main_sicbo  # noqa: F401
    from . import main_vip  # noqa: F401
    from . import main_speed  # noqa: F401
    from . import main_baccarat  # noqa: F401

    # Make main functions available at package level
    __all__ = ["main_sicbo", "main_vip", "main_speed", "main_baccarat"]
except ImportError:
    # In test environment or when modules are not available
    __all__ = []
