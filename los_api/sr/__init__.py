# Speed Roulette API package
# This file makes the sr directory a Python package

# Import commonly used functions for convenience
from .api_v2_sr import start_post_v2, deal_post_v2, finish_post_v2, broadcast_post_v2

from .api_v2_uat_sr import (
    start_post_v2_uat,
    deal_post_v2_uat,
    finish_post_v2_uat,
    broadcast_post_v2_uat,
)

from .api_v2_prd_sr import (
    start_post_v2_prd,
    deal_post_v2_prd,
    finish_post_v2_prd,
    broadcast_post_v2_prd,
)

from .api_v2_stg_sr import (
    start_post_v2_stg,
    deal_post_v2_stg,
    finish_post_v2_stg,
    broadcast_post_v2_stg,
)

from .api_v2_qat_sr import (
    start_post_v2_qat,
    deal_post_v2_qat,
    finish_post_v2_qat,
    broadcast_post_v2_qat,
)

__all__ = [
    # Standard API
    "start_post_v2",
    "deal_post_v2",
    "finish_post_v2",
    "broadcast_post_v2",
    # UAT Environment
    "start_post_v2_uat",
    "deal_post_v2_uat",
    "finish_post_v2_uat",
    "broadcast_post_v2_uat",
    # Production Environment
    "start_post_v2_prd",
    "deal_post_v2_prd",
    "finish_post_v2_prd",
    "broadcast_post_v2_prd",
    # Staging Environment
    "start_post_v2_stg",
    "deal_post_v2_stg",
    "finish_post_v2_stg",
    "broadcast_post_v2_stg",
    # QAT Environment
    "start_post_v2_qat",
    "deal_post_v2_qat",
    "finish_post_v2_qat",
    "broadcast_post_v2_qat",
]
