from __future__ import annotations

import threading
import time

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.batch import list_due_jobs, run_batch_job
from app.services.fx_rate import maybe_refresh_usd_jpy_rate

_stop_event = threading.Event()
_thread: threading.Thread | None = None


def _scheduler_loop() -> None:
    settings = get_settings()
    poll_seconds = max(5, settings.scheduler_poll_seconds)

    while not _stop_event.is_set():
        db = SessionLocal()
        try:
            maybe_refresh_usd_jpy_rate(db)
            due_jobs = list_due_jobs(db)
            for job in due_jobs:
                run_batch_job(db, job)
        finally:
            db.close()

        _stop_event.wait(poll_seconds)


def start_scheduler() -> None:
    global _thread
    settings = get_settings()
    if not settings.scheduler_enabled:
        return
    if _thread and _thread.is_alive():
        return

    _stop_event.clear()
    _thread = threading.Thread(target=_scheduler_loop, daemon=True, name="batch-scheduler")
    _thread.start()


def stop_scheduler() -> None:
    _stop_event.set()
