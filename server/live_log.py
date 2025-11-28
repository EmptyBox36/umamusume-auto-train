from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, asdict
from typing import Deque, List, Dict, Any


@dataclass
class LogEntry:
    id: int
    ts: float
    level: str
    message: str


_lock = threading.Lock()
_buffer: Deque[LogEntry] = deque(maxlen=1000)
_next_id: int = 0
_attached: bool = False


class WebLogHandler(logging.Handler):
    """Handler that stores recent log records in memory for WebUI."""

    def emit(self, record: logging.LogRecord) -> None:
        global _next_id

        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()

        entry = LogEntry(
            id=_next_id,
            ts=record.created or time.time(),
            level=record.levelname,
            message=msg,
        )

        with _lock:
            _buffer.append(entry)
            _next_id += 1


def attach_web_log_handler(level: int = logging.INFO) -> None:
    """
    Attach the web log handler to the root logger.
    Safe to call more than once.
    """
    global _attached
    if _attached:
        return

    handler = WebLogHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    root = logging.getLogger()
    root.addHandler(handler)
    _attached = True

    # visible once in console so we know it ran
    logging.getLogger().warning(">>>> WebLogHandler ATTACHED <<<<")


def get_logs_since(since_id: int) -> List[Dict[str, Any]]:
    with _lock:
        return [asdict(e) for e in _buffer if e.id > since_id]


def get_latest_id() -> int:
    with _lock:
        return _next_id - 1 if _next_id > 0 else -1