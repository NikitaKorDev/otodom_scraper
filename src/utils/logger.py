"""Console logging and polite request pacing."""

from __future__ import annotations

import random
import time


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def human_delay(a: float = 0.8, b: float = 2.2) -> None:
    time.sleep(random.uniform(a, b))
