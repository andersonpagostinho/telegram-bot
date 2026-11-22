"""
Audit Logger - Secure logging of validation operations
"""

import os
import json
from datetime import datetime

class AuditLogger:
    """Log validation operations securely without exposing secrets"""

    def __init__(self, log_file: str = None):
        self.log_file = log_file or os.path.expanduser("~/.cache/neoeve-validator/audit.log")
        self.ensure_log_dir()

    def ensure_log_dir(self):
        """Create log directory if it doesn't exist"""
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    def log_validation(self, task_id: str, verdict: str, cost: float, tokens_used: int):
        """Log a validation operation"""

        entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "verdict": verdict,
            "cost": cost,
            "tokens": tokens_used,
            "api_key_configured": bool(os.getenv("OPENAI_API_KEY"))
        }

        self._write_log(entry)

    def log_error(self, task_id: str, error: str, error_type: str):
        """Log validation error"""

        entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "event": "error",
            "error_type": error_type,
            "error_message": error[:200]  # Truncate long errors
        }

        self._write_log(entry)

    def log_cost_limit_exceeded(self, task_id: str, estimated_cost: float, limit: float):
        """Log when cost limit exceeded"""

        entry = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "event": "cost_limit_exceeded",
            "estimated_cost": estimated_cost,
            "limit": limit
        }

        self._write_log(entry)

    def _write_log(self, entry: dict):
        """Write audit entry to log file"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            # Fail silently to avoid blocking validation
            pass

    def get_daily_cost(self) -> float:
        """Calculate today's total cost from audit log"""

        if not os.path.exists(self.log_file):
            return 0.0

        total = 0.0
        today = datetime.now().date().isoformat()

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("timestamp", "").startswith(today) and "cost" in entry:
                            total += entry["cost"]
                    except:
                        pass
        except:
            pass

        return total

    def get_monthly_cost(self) -> float:
        """Calculate current month's total cost from audit log"""

        if not os.path.exists(self.log_file):
            return 0.0

        total = 0.0
        today = datetime.now()
        month_prefix = f"{today.year}-{today.month:02d}"

        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("timestamp", "").startswith(month_prefix) and "cost" in entry:
                            total += entry["cost"]
                    except:
                        pass
        except:
            pass

        return total
