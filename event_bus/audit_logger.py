"""JSONL Audit Trail Logging"""

from pathlib import Path
from datetime import datetime
import json
import threading
from typing import Dict, Any

from event_bus.event import Event


class AuditLogger:
    """Writes audit trail to JSONL file"""

    def __init__(self, log_path: str = "C:/dev/neoeve/.cache/event_bus_audit.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log_event(self, event: Event, state: str, details: Dict[str, Any] = None) -> None:
        """Log event state transition"""
        try:
            with self._lock:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    record = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "event_id": event.event_id,
                        "event_type": event.event_type.value,
                        "mission_id": event.mission_id,
                        "state": state,
                        "details": details or {}
                    }
                    f.write(json.dumps(record) + "\n")
        except Exception as e:
            # Log to stderr but don't fail
            print(f"ERROR: Failed to write audit log: {e}")

    def log_error(self, event_id: str, error: str) -> None:
        """Log error event"""
        try:
            with self._lock:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    record = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "event_id": event_id,
                        "state": "ERROR",
                        "error": error
                    }
                    f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"ERROR: Failed to write error log: {e}")
