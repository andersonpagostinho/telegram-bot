"""SQLite-based Event Store for Persistent Event Storage"""

import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
import threading

from event_bus.event import Event, EventStatus, EventType
from event_bus.exceptions import PersistenceException


class EventStore:
    """Manages event persistence in SQLite database"""

    def __init__(self, db_path: str = "C:/dev/neoeve/.cache/event_bus.db", use_wal: bool = True):
        """
        Initialize event store.

        Args:
            db_path: Path to SQLite database file
            use_wal: Use WAL mode (disable for testing on Windows)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.use_wal = use_wal
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings"""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Use WAL for production (better concurrency), DELETE mode for tests (avoid locks)
        if self.use_wal:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        else:
            conn.execute("PRAGMA journal_mode=DELETE")  # Traditional rollback journal
            conn.execute("PRAGMA synchronous=FULL")  # More conservative for tests

        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Main events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        event_id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        mission_id TEXT NOT NULL,
                        task_id TEXT,
                        execution_id TEXT,
                        agent_id TEXT NOT NULL,
                        agent_role TEXT,
                        timestamp TEXT NOT NULL,
                        correlation_id TEXT NOT NULL,
                        causation_id TEXT,
                        payload TEXT NOT NULL,
                        schema_version TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'PENDING',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)

                # Processing state table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS processing_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL REFERENCES events(event_id),
                        status TEXT NOT NULL,
                        processed_at TEXT NOT NULL,
                        consumer_id TEXT,
                        error_message TEXT,
                        retry_count INTEGER DEFAULT 0,
                        UNIQUE(event_id, status)
                    )
                """)

                # Idempotency tracking
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS idempotency_keys (
                        idempotency_key TEXT PRIMARY KEY,
                        event_id TEXT NOT NULL REFERENCES events(event_id),
                        result TEXT,
                        created_at TEXT NOT NULL
                    )
                """)

                # Indices for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_mission_id ON events(mission_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON events(task_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_id ON events(agent_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON events(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_correlation_id ON events(correlation_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")

                conn.commit()
        except Exception as e:
            raise PersistenceException(f"Failed to initialize database: {e}")

    def store_event(self, event: Event) -> None:
        """
        Store event in database.

        Args:
            event: Event to store

        Raises:
            PersistenceException: If storage fails
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    now = datetime.utcnow().isoformat()

                    cursor.execute("""
                        INSERT INTO events (
                            event_id, event_type, mission_id, task_id, execution_id,
                            agent_id, agent_role, timestamp, correlation_id, causation_id,
                            payload, schema_version, status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id,
                        event.event_type.value,
                        event.mission_id,
                        event.task_id,
                        event.execution_id,
                        event.agent_id,
                        event.agent_role,
                        event.timestamp,
                        event.correlation_id,
                        event.causation_id,
                        json.dumps(event.payload),
                        event.schema_version,
                        event.status.value,
                        now,
                        now
                    ))

                    conn.commit()
                    self._checkpoint_wal(conn)
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise PersistenceException(f"Event already exists: {event.event_id}")
            raise PersistenceException(f"Integrity error: {e}")
        except Exception as e:
            raise PersistenceException(f"Failed to store event: {e}")

    def get_event(self, event_id: str) -> Optional[Event]:
        """
        Retrieve event by ID.

        Args:
            event_id: Event identifier

        Returns:
            Event if found, None otherwise
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
                    row = cursor.fetchone()

                    if not row:
                        return None

                    return self._row_to_event(row)
        except Exception as e:
            raise PersistenceException(f"Failed to retrieve event: {e}")

    def get_pending_events(self, mission_id: str, limit: int = 10) -> List[Event]:
        """
        Get pending events for a mission.

        Args:
            mission_id: Mission identifier
            limit: Maximum number of events to return

        Returns:
            List of pending events
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM events
                        WHERE mission_id = ? AND status = 'PENDING'
                        ORDER BY timestamp ASC
                        LIMIT ?
                    """, (mission_id, limit))
                    rows = cursor.fetchall()

                    return [self._row_to_event(row) for row in rows]
        except Exception as e:
            raise PersistenceException(f"Failed to get pending events: {e}")

    def update_event_status(self, event_id: str, status: EventStatus, error_msg: Optional[str] = None) -> None:
        """
        Update event processing status.

        Args:
            event_id: Event identifier
            status: New status
            error_msg: Optional error message

        Raises:
            PersistenceException: If update fails
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Update event status
                    cursor.execute("""
                        UPDATE events SET status = ?, updated_at = ?
                        WHERE event_id = ?
                    """, (status.value, datetime.utcnow().isoformat(), event_id))

                    # Log state transition
                    cursor.execute("""
                        INSERT INTO processing_log (event_id, status, processed_at, error_message)
                        VALUES (?, ?, ?, ?)
                    """, (event_id, status.value, datetime.utcnow().isoformat(), error_msg))

                    conn.commit()
                    self._checkpoint_wal(conn)
        except Exception as e:
            raise PersistenceException(f"Failed to update event status: {e}")

    def mark_completed(self, event_id: str) -> None:
        """Mark event as completed"""
        self.update_event_status(event_id, EventStatus.COMPLETED)

    def mark_failed(self, event_id: str, reason: str) -> None:
        """Mark event as failed"""
        self.update_event_status(event_id, EventStatus.FAILED, reason)

    def get_history(self, mission_id: str, limit: int = 100) -> List[Event]:
        """
        Get event history for a mission.

        Args:
            mission_id: Mission identifier
            limit: Maximum number of events

        Returns:
            List of events ordered by timestamp
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM events
                        WHERE mission_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (mission_id, limit))
                    rows = cursor.fetchall()

                    return [self._row_to_event(row) for row in rows]
        except Exception as e:
            raise PersistenceException(f"Failed to get history: {e}")

    def get_stuck_events(self, timeout_minutes: int = 30) -> List[Event]:
        """
        Get events stuck in PROCESSING state.

        Args:
            timeout_minutes: Consider events older than this as stuck

        Returns:
            List of stuck events
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cutoff = (datetime.utcnow() - timedelta(minutes=timeout_minutes)).isoformat()

                    cursor.execute("""
                        SELECT * FROM events
                        WHERE status = 'PROCESSING' AND updated_at < ?
                        ORDER BY timestamp ASC
                    """, (cutoff,))
                    rows = cursor.fetchall()

                    return [self._row_to_event(row) for row in rows]
        except Exception as e:
            raise PersistenceException(f"Failed to get stuck events: {e}")

    def _row_to_event(self, row: sqlite3.Row) -> Event:
        """Convert database row to Event object"""
        event = Event(
            event_id=row["event_id"],
            event_type=EventType(row["event_type"]),
            mission_id=row["mission_id"],
            task_id=row["task_id"],
            execution_id=row["execution_id"],
            agent_id=row["agent_id"],
            agent_role=row["agent_role"] or "",
            timestamp=row["timestamp"],
            correlation_id=row["correlation_id"],
            causation_id=row["causation_id"],
            payload=json.loads(row["payload"]),
            schema_version=row["schema_version"],
        )
        event.status = EventStatus(row["status"])
        event.created_at_local = row["created_at"]
        return event

    def reserve_event_atomic(self, event_id: str) -> bool:
        """
        Atomically reserve event for processing (PENDING -> PROCESSING).

        Uses BEGIN IMMEDIATE to prevent race conditions with concurrent consumers.

        Args:
            event_id: Event to reserve

        Returns:
            True if successfully reserved, False if event in different state

        Raises:
            PersistenceException: If operation fails
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()

                    # Explicit IMMEDIATE transaction for exclusive lock
                    cursor.execute("BEGIN IMMEDIATE")

                    try:
                        # Atomic: Check status AND update in single operation
                        cursor.execute("""
                            UPDATE events
                            SET status = ?, updated_at = ?
                            WHERE event_id = ? AND status = ?
                        """, (
                            EventStatus.PROCESSING.value,
                            datetime.utcnow().isoformat(),
                            event_id,
                            EventStatus.PENDING.value
                        ))

                        success = cursor.rowcount > 0

                        if success:
                            # Also log state transition
                            cursor.execute("""
                                INSERT INTO processing_log (event_id, status, processed_at)
                                VALUES (?, ?, ?)
                            """, (event_id, EventStatus.PROCESSING.value, datetime.utcnow().isoformat()))

                            conn.commit()
                        else:
                            conn.rollback()

                        return success
                    except Exception as e:
                        conn.rollback()
                        raise e
        except Exception as e:
            raise PersistenceException(f"Failed to reserve event: {e}")

    def _checkpoint_wal(self, conn: sqlite3.Connection) -> None:
        """
        Checkpoint WAL to ensure all data persisted and locks released.

        Windows/SQLite: WAL checkpoint must be AGGRESSIVE to release locks before close().
        """
        try:
            cursor = conn.cursor()
            # Aggressive checkpoint: TRUNCATE restarts and truncates WAL file
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass

    def _close_connection(self, conn: sqlite3.Connection) -> None:
        """Explicitly close connection and checkpoint WAL"""
        try:
            self._checkpoint_wal(conn)
            conn.close()
        except Exception:
            pass

    def cleanup_old_events(self, days: int = 30) -> int:
        """
        Clean up old completed/failed events.

        Args:
            days: Delete events older than this

        Returns:
            Number of events deleted
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

                    cursor.execute("""
                        DELETE FROM events
                        WHERE (status IN ('COMPLETED', 'FAILED', 'DEAD_LETTER'))
                        AND created_at < ?
                    """, (cutoff,))

                    deleted = cursor.rowcount
                    conn.commit()
                    self._checkpoint_wal(conn)
                    return deleted
        except Exception as e:
            raise PersistenceException(f"Failed to cleanup events: {e}")
