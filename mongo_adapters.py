import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from db.mongo_adapters import *

# Backwards-compatible shim
__all__ = [
    'mongo_enabled', 'UserTimezonesAdapter', 'BirthdaysAdapter', 'UserProfilesAdapter', 'GiftcodeStateAdapter'
]
