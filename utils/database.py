"""
Database module for persisting duplicate name tracking data
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class NameDatabase:
    """SQLite database for tracking seen names and their counts"""

    def __init__(self, db_path: Path = None):
        if db_path is None:
            # Default to a database file in the project root
            db_path = Path(__file__).parent.parent / "duplicate_names.db"
        self.db_path = Path(db_path)
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"Database initialized at: {self.db_path}")

    def _init_database(self):
        """Initialize the database with required tables and PRAGMAs."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Use Write-Ahead Logging for better concurrency and performance
                cursor.execute("PRAGMA journal_mode = WAL;")
                # Create the SeenNames table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS SeenNames (
                        name TEXT PRIMARY KEY,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        count INTEGER NOT NULL
                    )
                """)
                conn.commit()
                logger.info("Database tables initialized (WAL mode enabled)")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def get_count(self, name: str) -> int:
        """Get the current count for a specific name, or 0 if not present."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count FROM SeenNames WHERE name = ?", (name,))
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"Error fetching count for '{name}': {e}")
            return 0

    def add_name_occurrence(self, name: str, occurrences: int = 1):
        """
        Record one or more occurrences of a name:
         - if new, insert with count=occurrences
         - if exists, increment count by occurrences
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count FROM SeenNames WHERE name = ?", (name,))
                row = cursor.fetchone()
                if row:
                    cursor.execute(
                        "UPDATE SeenNames SET count = count + ? WHERE name = ?",
                        (occurrences, name)
                    )
                    logger.debug(f"Incremented '{name}' by {occurrences}")
                else:
                    cursor.execute(
                        "INSERT INTO SeenNames (name, count) VALUES (?, ?)",
                        (name, occurrences)
                    )
                    logger.debug(f"Inserted '{name}' with count {occurrences}")
                conn.commit()
        except Exception as e:
            logger.error(f"Error adding occurrence for '{name}': {e}")

    def get_statistics(self) -> dict:
        """
        Return summary stats:
         - total_names: number of distinct names
         - total_occurrences: sum of all counts
         - top_names: list of top 10 (name, count) tuples
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), SUM(count) FROM SeenNames")
                total_names, total_occurrences = cursor.fetchone()
                total_names = total_names or 0
                total_occurrences = total_occurrences or 0

                cursor.execute(
                    "SELECT name, count FROM SeenNames ORDER BY count DESC LIMIT 10"
                )
                top_names = cursor.fetchall()

                return {
                    'total_names': total_names,
                    'total_occurrences': total_occurrences,
                    'top_names': top_names
                }
        except Exception as e:
            logger.error(f"Error fetching statistics: {e}")
            return {'total_names': 0, 'total_occurrences': 0, 'top_names': []}

    def get_recent_names(self, limit: int = 100) -> list[tuple]:
        """
        Return the most recently seen names, up to `limit`.
        Each entry is (name, count, first_seen).
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name, count, first_seen FROM SeenNames "
                    "ORDER BY first_seen DESC LIMIT ?",
                    (limit,)
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error fetching recent names: {e}")
            return []

    def clear_all(self):
        """Delete all records from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM SeenNames")
                conn.commit()
                logger.info("All records cleared from database")
        except Exception as e:
            logger.error(f"Error clearing database: {e}")
