from __future__ import annotations

import datetime
from typing import Literal

AbsenceLang = Literal["ru", "kz", "en"]
DEFAULT_SHIFT_START_TIME = datetime.time(hour=8, minute=30)
DEFAULT_SHIFT_END_TIME = datetime.time(hour=17, minute=30)
ARRIVAL_GRACE_MINUTES = 5
