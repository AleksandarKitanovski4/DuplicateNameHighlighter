"""
SQLite database management for persistent data storage
"""

import sqlite3
import logging
import os
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    """SQLite database manager for duplicate name tracking"""
    
    def __init__(self, db_file='duplicate_names.db'):
        self.db_file = db_file
        self.init_database()
        logger.info(f"Database initialized: {db_file}")
    
    def init_database(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create names table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS names (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_occurrences INTEGER DEFAULT 1,
                        UNIQUE(name)
                    )
                ''')
                
                # Create occurrences table for detailed tracking
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS occurrences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name_id INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        count INTEGER DEFAULT 1,
                        session_id TEXT,
                        FOREIGN KEY (name_id) REFERENCES names (id)
                    )
                ''')
                
                # Create indexes for better performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_names_name ON names(name)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_occurrences_name_id ON occurrences(name_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_occurrences_timestamp ON occurrences(timestamp)')
                
                conn.commit()
                logger.info("Database tables initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}", exc_info=True)
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_file, timeout=10.0)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {str(e)}")
            raise
        finally:
            if conn:
                conn.close()
    
    def add_name_occurrence(self, name, count=1, session_id=None):
        """Add or update name occurrence
        
        Args:
            name: Name to add/update
            count: Number of occurrences in this scan
            session_id: Optional session identifier
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if name exists
                cursor.execute('SELECT id, total_occurrences FROM names WHERE name = ?', (name,))
                result = cursor.fetchone()
                
                if result:
                    # Update existing name
                    name_id = result['id']
                    new_total = result['total_occurrences'] + count
                    
                    cursor.execute('''
                        UPDATE names 
                        SET last_seen = CURRENT_TIMESTAMP, total_occurrences = ?
                        WHERE id = ?
                    ''', (new_total, name_id))
                else:
                    # Insert new name
                    cursor.execute('''
                        INSERT INTO names (name, total_occurrences)
                        VALUES (?, ?)
                    ''', (name, count))
                    name_id = cursor.lastrowid
                
                # Add occurrence record
                cursor.execute('''
                    INSERT INTO occurrences (name_id, count, session_id)
                    VALUES (?, ?, ?)
                ''', (name_id, count, session_id))
                
                conn.commit()
                logger.debug(f"Added occurrence for '{name}': count={count}")
                
        except Exception as e:
            logger.error(f"Error adding name occurrence: {str(e)}", exc_info=True)
    
    def get_name_count(self, name):
        """Get total occurrence count for a name
        
        Args:
            name: Name to look up
            
        Returns:
            Integer count of occurrences
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT total_occurrences FROM names WHERE name = ?', (name,))
                result = cursor.fetchone()
                return result['total_occurrences'] if result else 0
                
        except Exception as e:
            logger.error(f"Error getting name count: {str(e)}")
            return 0
    
    def get_all_names(self):
        """Get all tracked names
        
        Returns:
            List of name records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, first_seen, last_seen, total_occurrences
                    FROM names
                    ORDER BY total_occurrences DESC, last_seen DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting all names: {str(e)}")
            return []
    
    def get_recent_names(self, limit=50):
        """Get recently seen names
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of recent name records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, last_seen, total_occurrences
                    FROM names
                    ORDER BY last_seen DESC
                    LIMIT ?
                ''', (limit,))
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting recent names: {str(e)}")
            return []
    
    def get_duplicate_names(self, min_count=2):
        """Get names that appear more than specified count
        
        Args:
            min_count: Minimum occurrence count to be considered duplicate
            
        Returns:
            List of duplicate name records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, first_seen, last_seen, total_occurrences
                    FROM names
                    WHERE total_occurrences >= ?
                    ORDER BY total_occurrences DESC, last_seen DESC
                ''', (min_count,))
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting duplicate names: {str(e)}")
            return []
    
    def get_statistics(self):
        """Get database statistics
        
        Returns:
            Dictionary with database statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total unique names
                cursor.execute('SELECT COUNT(*) as count FROM names')
                total_names = cursor.fetchone()['count']
                
                # Total occurrences
                cursor.execute('SELECT SUM(total_occurrences) as sum FROM names')
                total_occurrences = cursor.fetchone()['sum'] or 0
                
                # Duplicate names (appearing more than once)
                cursor.execute('SELECT COUNT(*) as count FROM names WHERE total_occurrences > 1')
                duplicate_names = cursor.fetchone()['count']
                
                # Most recent activity
                cursor.execute('SELECT MAX(last_seen) as latest FROM names')
                latest_activity = cursor.fetchone()['latest']
                
                return {
                    'total_names': total_names,
                    'total_occurrences': total_occurrences,
                    'duplicate_names': duplicate_names,
                    'latest_activity': latest_activity
                }
                
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}
    
    def search_names(self, query, limit=50):
        """Search for names matching query
        
        Args:
            query: Search query string
            limit: Maximum results to return
            
        Returns:
            List of matching name records
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                search_pattern = f'%{query}%'
                cursor.execute('''
                    SELECT name, first_seen, last_seen, total_occurrences
                    FROM names
                    WHERE name LIKE ?
                    ORDER BY total_occurrences DESC, last_seen DESC
                    LIMIT ?
                ''', (search_pattern, limit))
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error searching names: {str(e)}")
            return []
    
    def delete_name(self, name):
        """Delete a name and all its occurrences
        
        Args:
            name: Name to delete
            
        Returns:
            Boolean success status
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get name ID
                cursor.execute('SELECT id FROM names WHERE name = ?', (name,))
                result = cursor.fetchone()
                
                if result:
                    name_id = result['id']
                    
                    # Delete occurrences first (foreign key constraint)
                    cursor.execute('DELETE FROM occurrences WHERE name_id = ?', (name_id,))
                    
                    # Delete name
                    cursor.execute('DELETE FROM names WHERE id = ?', (name_id,))
                    
                    conn.commit()
                    logger.info(f"Deleted name '{name}' and all occurrences")
                    return True
                else:
                    logger.warning(f"Name '{name}' not found for deletion")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting name: {str(e)}")
            return False
    
    def clear_all_data(self):
        """Clear all data from database
        
        Returns:
            Boolean success status
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM occurrences')
                cursor.execute('DELETE FROM names')
                conn.commit()
                logger.info("All database data cleared")
                return True
                
        except Exception as e:
            logger.error(f"Error clearing database: {str(e)}")
            return False
    
    def export_to_csv(self, filename):
        """Export data to CSV file
        
        Args:
            filename: Output CSV filename
            
        Returns:
            Boolean success status
        """
        try:
            import csv
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, first_seen, last_seen, total_occurrences
                    FROM names
                    ORDER BY total_occurrences DESC
                ''')
                
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['Name', 'First Seen', 'Last Seen', 'Total Occurrences'])
                    
                    for row in cursor.fetchall():
                        writer.writerow([row['name'], row['first_seen'], 
                                       row['last_seen'], row['total_occurrences']])
                
                logger.info(f"Data exported to CSV: {filename}")
                return True
                
        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
            return False
    
    def close(self):
        """Close database (cleanup method)"""
        # SQLite connections are closed automatically with context manager
        logger.info("Database closed")
    
    def vacuum(self):
        """Optimize database by reclaiming space"""
        try:
            with self.get_connection() as conn:
                conn.execute('VACUUM')
                logger.info("Database vacuumed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error vacuuming database: {str(e)}")
            return False
    
    def get_all_seen_names(self):
        """Get all seen names for CSV export
        Returns:
            List of tuples: (name, first_seen, total_occurrences)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT name, first_seen, total_occurrences
                    FROM names
                    ORDER BY first_seen ASC
                ''')
                return [(row['name'], row['first_seen'], row['total_occurrences']) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all seen names: {str(e)}")
            return []
