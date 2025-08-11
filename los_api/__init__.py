# LOS API package for SDP Roulette System
# This package provides API functions for different game types and environments

# Import sub-packages
from . import sb    # SicBo API
from . import vr    # VIP Roulette API
from . import sr    # Speed Roulette API
from . import bcr   # Baccarat API

# Import common utilities
from .get_access_token import get_access_token

__all__ = [
    'sb',
    'vr', 
    'sr',
    'bcr',
    'get_access_token'
]

# Version information
__version__ = '2.0.0'
__author__ = 'Studio SDP Team'

# __all__ = ['start_post', 'deal_post', 'finish_post', 'visibility_post', 'get_roundID']