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
<<<<<<<< HEAD:tracker/duplicate_tracker.py
        self.session_names = set()  # Names seen in current session
        self.name_positions = defaultdict(list)  # Track positions of each name
        self.name_counts = defaultdict(int)  # Count occurrences of each name
        self.position_history = {}  # Track position history for scroll adjustment
        self.last_scan_names = set()  # Names from last scan for comparison
        
        logger.info("Duplicate tracker initialized")
    
    def process_names(self, names_with_positions, scroll_info=None):
        """Process extracted names and identify duplicates
        
        Args:
            names_with_positions: List of name data from OCR
            scroll_info: Optional scroll detection info for position adjustment
            
        Returns:
            List of duplicate entries with positions and counts
========
        self.overlay = overlay
        self.session_counts: Dict[str, int] = {}
        logger.info("DuplicateTracker initialized")
    
    def process(self, results: List[Dict]) -> None:
        """
        Process OCR results and highlight duplicates.
        
        Args:
            results: List of dicts with keys: name, x, y, width, height, confidence
>>>>>>>> ef98d5a (Finalize repo structure):core/duplicate_tracker.py
        """
        duplicate_boxes: List[Tuple[int,int,int,int]] = []
        
        for entry in results:
            name = entry['name']
            # increment session count
            count = self.session_counts.get(name, 0) + 1
            self.session_counts[name] = count
            
            # persist occurrence (insert or update)
            self.database.add_name_occurrence(name)
            
<<<<<<<< HEAD:tracker/duplicate_tracker.py
            # Handle scroll adjustment for existing markers
            if scroll_info:
                self.adjust_existing_positions(scroll_info)
            
            # Process each unique name from current scan
            for normalized_name, positions in current_scan_names.items():
                # Update database
                self.database.add_name_occurrence(normalized_name, len(positions))
                
                # Check if this name was seen before in session or database
                total_count = self.database.get_name_count(normalized_name)
                was_in_session = normalized_name in self.session_names
                
                # Add to session names
                self.session_names.add(normalized_name)
                
                # Update position history
                self.update_position_history(normalized_name, positions)
                
                # If this name has been seen before (either in session or in database)
                if total_count > len(positions) or was_in_session:
                    duplicates.append({
                        'name': normalized_name,
                        'positions': positions,
                        'count': total_count,
                        'is_new_duplicate': not was_in_session
                    })
                    
                    logger.info(f"Duplicate detected: '{normalized_name}' (count: {total_count})")
            
            # Update last scan names for comparison
            self.last_scan_names = set(current_scan_names.keys())
            
            return duplicates
            
        except Exception as e:
            logger.error(f"Error processing names: {str(e)}", exc_info=True)
            return []
    
    def update_position_history(self, normalized_name, positions):
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
    
    def adjust_existing_positions(self, scroll_info):
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
    
    def get_names_scrolled_out(self, region_height):
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
    
    def get_new_names_since_last_scan(self):
        """Get names that are new since the last scan
        
        Returns:
            Set of new names
        """
        current_names = set(self.name_positions.keys())
        return current_names - self.last_scan_names
    
    def get_removed_names_since_last_scan(self):
        """Get names that were present in last scan but not in current
        
        Returns:
            Set of removed names
        """
        current_names = set(self.name_positions.keys())
        return self.last_scan_names - current_names
    
    def normalize_name(self, name):
        """Normalize name for comparison
        
        Args:
            name: Raw name string
            
        Returns:
            Normalized name string
========
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
>>>>>>>> ef98d5a (Finalize repo structure):core/duplicate_tracker.py
        """
        Clear only in-memory session counts and reset overlay markers.
        Database remains intact.
        """
        self.session_counts.clear()
        self.overlay.update_markers([])  # clear all markers
        logger.info("Session counts reset")
    
    def clear_all(self) -> None:
        """
<<<<<<<< HEAD:tracker/duplicate_tracker.py
        try:
            total_names = len(self.session_names)
            database_stats = self.database.get_statistics()
            
            return {
                'session_names': total_names,
                'total_database_names': database_stats.get('total_names', 0),
                'total_occurrences': database_stats.get('total_occurrences', 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            return {}
    
    def reset_session(self):
        """Reset current session data"""
        self.session_names.clear()
        self.name_positions.clear()
        self.name_counts.clear()
        self.position_history.clear()
        self.last_scan_names.clear()
        logger.info("Session data reset")
    
    def add_manual_name(self, name):
        """Manually add a name to tracking
        
        Args:
            name: Name to add
========
        Clear both session data and persistent database.
>>>>>>>> ef98d5a (Finalize repo structure):core/duplicate_tracker.py
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
