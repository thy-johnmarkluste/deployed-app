"""
Centralized background job queue for controller operations.

Provides:
- bounded worker pool
- optional de-duplication keys
- lifecycle callbacks (queued/running/succeeded/failed)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue, Empty
import threading
from typing import Any, Callable, Dict, Optional, Tuple
import uuid


JobEventCallback = Callable[[str, "JobRecord", Optional[Exception]], None]


@dataclass
class JobRecord:
    """Represents one enqueued unit of background work."""

    id: str
    name: str
    dedupe_key: Optional[str] = None
    source: str = "system"
    silent: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    status: str = "queued"
    error: Optional[str] = None


class AsyncJobQueue:
    """Simple thread-based async job queue with lifecycle events."""

    def __init__(self, max_workers: int = 4, on_event: Optional[JobEventCallback] = None):
        self._max_workers = max(1, int(max_workers))
        self._on_event = on_event
        self._queue: Queue = Queue()
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._pending_keys = set()
        self._running_keys = set()
        self._workers = []

        for idx in range(self._max_workers):
            t = threading.Thread(target=self._worker_loop, name=f"job-worker-{idx + 1}", daemon=True)
            t.start()
            self._workers.append(t)

    def submit(
        self,
        name: str,
        func: Callable[..., Any],
        args: Tuple[Any, ...] = (),
        kwargs: Optional[Dict[str, Any]] = None,
        *,
        dedupe_key: Optional[str] = None,
        source: str = "system",
        silent: bool = False,
    ) -> Optional[str]:
        """Submit a function call for async execution.

        Returns job id, or None when dedupe blocks submission.
        """
        if self._stop_event.is_set():
            return None

        kwargs = kwargs or {}
        record = JobRecord(
            id=str(uuid.uuid4()),
            name=name,
            dedupe_key=dedupe_key,
            source=source,
            silent=silent,
        )

        with self._lock:
            if dedupe_key and (dedupe_key in self._pending_keys or dedupe_key in self._running_keys):
                return None
            if dedupe_key:
                self._pending_keys.add(dedupe_key)

        self._queue.put((record, func, args, kwargs))
        self._emit("queued", record)
        return record.id

    def stop(self, timeout: float = 1.0):
        """Stop workers gracefully."""
        self._stop_event.set()
        for _ in self._workers:
            self._queue.put(None)
        for t in self._workers:
            t.join(timeout=timeout)

    def _emit(self, event: str, record: JobRecord, error: Optional[Exception] = None):
        if self._on_event:
            self._on_event(event, record, error)

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                payload = self._queue.get(timeout=0.2)
            except Empty:
                continue

            if payload is None:
                self._queue.task_done()
                break

            record, func, args, kwargs = payload
            with self._lock:
                if record.dedupe_key:
                    self._pending_keys.discard(record.dedupe_key)
                    self._running_keys.add(record.dedupe_key)

            record.status = "running"
            record.started_at = datetime.utcnow()
            self._emit("running", record)

            try:
                func(*args, **kwargs)
                record.status = "succeeded"
                self._emit("succeeded", record)
            except Exception as exc:
                record.status = "failed"
                record.error = str(exc)
                self._emit("failed", record, exc)
            finally:
                record.finished_at = datetime.utcnow()
                self._emit("finished", record)
                with self._lock:
                    if record.dedupe_key:
                        self._running_keys.discard(record.dedupe_key)
                self._queue.task_done()
