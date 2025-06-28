"""
Duplicate name tracking and management
"""

import logging
from typing import List, Dict, Tuple
from datetime import datetime
from collections import defaultdict

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
        self.session_names = set()  # Names seen in current session
        self.name_positions = defaultdict(list)  # Track positions of each name
        self.position_history = {}  # Track position history for scroll adjustment
        self.last_scan_names = set()  # Names from last scan for comparison
        
        logger.info("DuplicateTracker initialized")
    
    def process(self, results: List[Dict]) -> None:
        """
        Process OCR results and highlight duplicates.
        
        Args:
            results: List of dicts with keys: text, bbox (x, y, width, height), confidence
        """
        duplicate_boxes: List[Tuple[int, int, int, int]] = []
        
        # Group results by name
        name_groups = defaultdict(list)
        for entry in results:
            name = entry['text']
            name_groups[name].append(entry)
        
        # Process each name
        for name, entries in name_groups.items():
            # Increment session count
            count = self.session_counts.get(name, 0) + len(entries)
            self.session_counts[name] = count
            
            # Persist occurrence (insert or update)
            for entry in entries:
                self.database.add_name_occurrence(name)
            
            # If this is a duplicate (seen > 1), queue for highlighting
            if count > 1:
                for entry in entries:
                    x, y, w, h = entry['bbox']
                    duplicate_boxes.append((x, y, w, h))
                logger.info(f"Duplicate detected: '{name}' (session count={count})")
        
        # Update overlay: pass empty list to clear markers when no duplicates
        self.overlay.update_markers(duplicate_boxes)
    
    def reset_session(self) -> None:
        """
        Clear only in-memory session counts and reset overlay markers.
        Database remains intact.
        """
        self.session_counts.clear()
        self.session_names.clear()
        self.name_positions.clear()
        self.position_history.clear()
        self.last_scan_names.clear()
        self.overlay.update_markers([])  # clear all markers
        logger.info("Session counts reset")
    
    def clear_all(self) -> None:
        """
        Clear both session data and persistent database.
        """
        self.reset_session()
        self.database.clear_all_data()
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
    
    def update_position_history(self, normalized_name: str, positions: List[Dict]) -> None:
        """Update position history for a name
        
        Args:
            normalized_name: Normalized name string
            positions: List of position dictionaries
        """
        if normalized_name not in self.position_history:
            self.position_history[normalized_name] = []
        
        # Add current positions with timestamp
        timestamp = datetime.now()
        for pos in positions:
            self.position_history[normalized_name].append({
                'x': pos['x'],
                'y': pos['y'],
                'width': pos['width'],
                'height': pos['height'],
                'timestamp': timestamp
            })
        
        # Keep only recent positions (last 10)
        if len(self.position_history[normalized_name]) > 10:
            self.position_history[normalized_name] = self.position_history[normalized_name][-10:]
    
    def adjust_existing_positions(self, scroll_info: Dict) -> None:
        """Adjust existing marker positions based on scroll
        
        Args:
            scroll_info: Scroll detection information
        """
        direction = scroll_info['direction']
        magnitude = scroll_info['magnitude']
        
        for name, positions in self.position_history.items():
            for pos in positions:
                if direction == 'down':
                    pos['y'] -= magnitude
                elif direction == 'up':
                    pos['y'] += magnitude
        
        logger.debug(f"Adjusted positions for {len(self.position_history)} names")
    
    def get_names_scrolled_out(self, region_height: int) -> set:
        """Get names that have scrolled out of view
        
        Args:
            region_height: Height of the monitored region
            
        Returns:
            Set of names that are no longer visible
        """
        scrolled_out = set()
        
        for name, positions in self.position_history.items():
            # Check if all positions for this name are out of view
            all_out_of_view = True
            for pos in positions:
                if pos['y'] + pos['height'] > 0 and pos['y'] < region_height:
                    all_out_of_view = False
                    break
            
            if all_out_of_view:
                scrolled_out.add(name)
        
        return scrolled_out
    
    def get_new_names_since_last_scan(self) -> set:
        """Get names that are new since the last scan
        
        Returns:
            Set of new names
        """
        current_names = set(self.name_positions.keys())
        return current_names - self.last_scan_names
    
    def get_removed_names_since_last_scan(self) -> set:
        """Get names that were present in last scan but not in current
        
        Returns:
            Set of removed names
        """
        current_names = set(self.name_positions.keys())
        return self.last_scan_names - current_names
    
    def normalize_name(self, name: str) -> str:
        """Normalize name for comparison
        
        Args:
            name: Raw name string
            
        Returns:
            Normalized name string
        """
        # Basic normalization: strip whitespace, convert to lowercase
        return name.strip().lower()
