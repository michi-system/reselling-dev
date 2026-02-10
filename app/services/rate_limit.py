from __future__ import annotations

import threading
import time

_lock = threading.Lock()
_last_called_at: dict[str, float] = {}


def wait_for_slot(key: str, min_interval_seconds: float) -> None:
    if min_interval_seconds <= 0:
        return

    with _lock:
        now = time.monotonic()
        last_called = _last_called_at.get(key)
        if last_called is None:
            _last_called_at[key] = now
            return

        remaining = min_interval_seconds - (now - last_called)
        if remaining > 0:
            time.sleep(remaining)
            now = time.monotonic()

        _last_called_at[key] = now
