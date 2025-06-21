"""
Duplicate name tracking and management
"""

import logging
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class DuplicateTracker:
    """Tracks and manages duplicate name detection"""
    
    def __init__(self, database, overlay):
        """
        Args:
            database: instance of NameDatabase (with add_name_occurrence, clear_all, get_statistics)
            overlay: instance of Overlay (with update_markers)
        """
        self.database = database
        self.overlay = overlay
        self.session_counts: Dict[str, int] = {}
        logger.info("DuplicateTracker initialized")
    
    def process(self, results: List[Dict]) -> None:
        """
        Process OCR results and highlight duplicates.
        
        Args:
            results: List of dicts with keys: name, x, y, width, height, confidence
        """
        duplicate_boxes: List[Tuple[int,int,int,int]] = []
        
        for entry in results:
            name = entry['name']
            # increment session count
            count = self.session_counts.get(name, 0) + 1
            self.session_counts[name] = count
            
            # persist occurrence (insert or update)
            self.database.add_name_occurrence(name)
            
            # if this is a duplicate (seen > 1), queue for highlighting
            if count > 1:
                duplicate_boxes.append((
                    entry['x'],
                    entry['y'],
                    entry['width'],
                    entry['height']
                ))
                logger.info(f"Duplicate detected: '{name}' (session count={count})")
        
        # update overlay: pass empty list to clear markers when no duplicates
        self.overlay.update_markers(duplicate_boxes)
    
    def reset_session(self) -> None:
        """
        Clear only in-memory session counts and reset overlay markers.
        Database remains intact.
        """
        self.session_counts.clear()
        self.overlay.update_markers([])  # clear all markers
        logger.info("Session counts reset")
    
    def clear_all(self) -> None:
        """
        Clear both session data and persistent database.
        """
        self.reset_session()
        self.database.clear_all()
        logger.info("All data cleared from session and database")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Return statistics combining session and database info:
            session_names: distinct names seen this session
            session_occurrences: total occurrences this session
            database_names: total distinct names in DB
            database_occurrences: total occurrences in DB
        """
        session_names = len(self.session_counts)
        session_occurrences = sum(self.session_counts.values())
        db_stats = self.database.get_statistics()
        
        return {
            'session_names': session_names,
            'session_occurrences': session_occurrences,
            'database_names': db_stats.get('total_names', 0),
            'database_occurrences': db_stats.get('total_occurrences', 0)
        }
    
    def get_duplicate_names(self) -> List[Tuple[str, int]]:
        """
        List names seen more than once in this session, with their session counts.
        """
        return [(n, c) for n, c in self.session_counts.items() if c > 1]
