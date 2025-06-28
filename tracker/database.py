"""
SQLite database management for persistent data storage
"""

import sqlite3
import logging
import threading
import time
from contextlib import contextmanager
from typing import List, Tuple, Dict, Optional

logger = logging.getLogger(__name__)

class Database:
    """SQLite database manager for duplicate name tracking"""

    def __init__(self, db_file: str = "duplicate_names.db"):
        self.db_file = db_file
        # allow multi‐threaded access
        self._lock = threading.Lock()
        self._initialize_schema()
        logger.info(f"Database initialized at: {self.db_file}")

    def _initialize_schema(self):
        """Create tables if they don't exist."""
        with self._get_connection() as conn:
            c = conn.cursor()
            # main seen_names table
            c.execute("""
                CREATE TABLE IF NOT EXISTS seen_names (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    name                TEXT    NOT NULL UNIQUE,
                    first_seen_ts       REAL    NOT NULL,
                    last_seen_ts        REAL    NOT NULL,
                    total_occurrences   INTEGER NOT NULL
                );
            """)
            # detailed per‐scan occurrences
            c.execute("""
                CREATE TABLE IF NOT EXISTS name_occurrences (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_id     INTEGER NOT NULL,
                    ts          REAL    NOT NULL,
                    count       INTEGER NOT NULL,
                    session_id  TEXT,
                    FOREIGN KEY(name_id) REFERENCES seen_names(id)
                );
            """)
            # indexes
            c.execute("CREATE INDEX IF NOT EXISTS idx_seen_names_name ON seen_names(name);")
            c.execute("CREATE INDEX IF NOT EXISTS idx_name_occurrences_name_id ON name_occurrences(name_id);")
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Thread‐safe context manager yielding a sqlite3.Connection."""
        conn = sqlite3.connect(self.db_file, timeout=10.0)
        try:
            yield conn
        finally:
            conn.close()

    def record_names(self,
                     names: List[str],
                     counts: Optional[List[int]] = None,
                     session_id: Optional[str] = None) -> None:
        """
        Insert or update a batch of names from one scan.

        :param names: list of detected names
        :param counts: parallel list of counts (defaults to all 1s)
        :param session_id: optional session identifier
        """
        if counts is None:
            counts = [1] * len(names)

        now = time.time()
        with self._lock, self._get_connection() as conn:
            c = conn.cursor()
            for name, cnt in zip(names, counts):
                # upsert into seen_names
                c.execute("""
                    SELECT id, total_occurrences
                      FROM seen_names
                     WHERE name = ?
                """, (name,))
                row = c.fetchone()
                if row:
                    name_id, total = row
                    new_total = total + cnt
                    c.execute("""
                        UPDATE seen_names
                           SET last_seen_ts = ?,
                               total_occurrences = ?
                         WHERE id = ?
                    """, (now, new_total, name_id))
                else:
                    c.execute("""
                        INSERT INTO seen_names
                            (name, first_seen_ts, last_seen_ts, total_occurrences)
                        VALUES (?, ?, ?, ?)
                    """, (name, now, now, cnt))
                    name_id = c.lastrowid

                # record in name_occurrences
                c.execute("""
                    INSERT INTO name_occurrences
                        (name_id, ts, count, session_id)
                    VALUES (?, ?, ?, ?)
                """, (name_id, now, cnt, session_id))

            conn.commit()

    def get_total_count(self, name: str) -> int:
        """Return the total occurrence count for a given name."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT total_occurrences FROM seen_names WHERE name = ?", (name,))
            row = c.fetchone()
            return row[0] if row else 0

    def get_all_seen(self) -> List[Dict]:
        """
        Return all seen names, ordered by most‐frequent first.
        Each record is a dict with keys:
        name, first_seen_ts, last_seen_ts, total_occurrences
        """
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT name, first_seen_ts, last_seen_ts, total_occurrences
                  FROM seen_names
              ORDER BY total_occurrences DESC, last_seen_ts DESC
            """)
            cols = [col[0] for col in c.description]
            return [dict(zip(cols, row)) for row in c.fetchall()]

    def get_duplicates(self, min_occurrences: int = 2) -> List[Dict]:
        """Return only those names seen at least `min_occurrences` times."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT name, first_seen_ts, last_seen_ts, total_occurrences
                  FROM seen_names
                 WHERE total_occurrences >= ?
              ORDER BY total_occurrences DESC, last_seen_ts DESC
            """, (min_occurrences,))
            cols = [col[0] for col in c.description]
            return [dict(zip(cols, row)) for row in c.fetchall()]

    def get_stats(self) -> Dict[str, float]:
        """
        Return some quick stats:
        - unique_names
        - total_occurrences
        - duplicates (names with occurrences>1)
        """
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM seen_names")
            unique_names = c.fetchone()[0]
            c.execute("SELECT SUM(total_occurrences) FROM seen_names")
            total_occ = c.fetchone()[0] or 0
            c.execute("SELECT COUNT(*) FROM seen_names WHERE total_occurrences>1")
            dup_count = c.fetchone()[0]
            return {
                "unique_names": unique_names,
                "total_occurrences": total_occ,
                "duplicate_names": dup_count
            }

    def clear_all(self) -> None:
        """Wipe all stored names and occurrences."""
        with self._lock, self._get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM name_occurrences")
            c.execute("DELETE FROM seen_names")
            conn.commit()
            logger.info("Cleared all database records")
