# Studio SDP Roulette System Package
# This file ensures that all modules are properly recognized as part of the
# package

# Import main modules to make them available
from . import main_sicbo
from . import main_vip
from . import main_speed
from . import main_baccarat

# Package metadata
__version__ = "0.1.0"
__author__ = "Kevin Kuo (Studio Team)"
__description__ = "SDP Game System with Roulette, SicBo, and Baccarat Controllers"

# Make main functions available at package level
__all__ = ["main_sicbo", "main_vip", "main_speed", "main_baccarat"]
