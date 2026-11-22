"""Idempotency Management for Event Deduplication"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import threading

from event_bus.event_store import EventStore
from event_bus.exceptions import DuplicateEventException


class IdempotencyManager:
    """Prevents duplicate event processing"""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store
        self._cache: Dict[str, tuple] = {}
        self._cache_ttl = timedelta(hours=24)
        self._lock = threading.RLock()

    def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if key was already processed"""
        with self._lock:
            if idempotency_key in self._cache:
                return True
            # Could also check DB for recent keys
            return False

    def mark_processed(self, idempotency_key: str, event_id: str, result: Optional[Any] = None) -> None:
        """Mark key as processed"""
        with self._lock:
            self._cache[idempotency_key] = (datetime.utcnow(), event_id, result)

    def get_result(self, idempotency_key: str) -> Optional[Any]:
        """Get cached result of previous processing"""
        with self._lock:
            if idempotency_key in self._cache:
                _, _, result = self._cache[idempotency_key]
                return result
            return None

    def cleanup_expired(self) -> int:
        """Remove expired cache entries"""
        with self._lock:
            now = datetime.utcnow()
            expired = [k for k, (t, _, _) in self._cache.items() if now - t > self._cache_ttl]
            for k in expired:
                del self._cache[k]
            return len(expired)
