from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_STORAGE_URI = os.getenv("NBGRADER_RATELIMIT_STORAGE_URI", "memory://")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_STORAGE_URI,
    default_limits=[],
)
