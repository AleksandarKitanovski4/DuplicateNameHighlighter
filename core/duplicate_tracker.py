"""
Duplicate name tracking and management
"""

import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class DuplicateTracker:
    """Tracks and manages duplicate name detection"""
    
    def __init__(self, database):
        self.database = database
        self.session_names = set()  # Names seen in current session
        self.name_positions = defaultdict(list)  # Track positions of each name
        self.name_counts = defaultdict(int)  # Count occurrences of each name
        
        logger.info("Duplicate tracker initialized")
    
    def process_names(self, names_with_positions):
        """Process extracted names and identify duplicates
        
        Args:
            names_with_positions: List of name data from OCR
            
        Returns:
            List of duplicate entries with positions and counts
        """
        if not names_with_positions:
            return []
        
        try:
            current_scan_names = {}
            duplicates = []
            
            # Group names from current scan by normalized name
            for name_data in names_with_positions:
                name = name_data['name']
                normalized_name = self.normalize_name(name)
                
                if normalized_name not in current_scan_names:
                    current_scan_names[normalized_name] = []
                
                current_scan_names[normalized_name].append({
                    'x': name_data['x'],
                    'y': name_data['y'],
                    'width': name_data['width'],
                    'height': name_data['height'],
                    'confidence': name_data['confidence']
                })
            
            # Process each unique name from current scan
            for normalized_name, positions in current_scan_names.items():
                # Update database
                self.database.add_name_occurrence(normalized_name, len(positions))
                
                # Check if this name was seen before in session or database
                total_count = self.database.get_name_count(normalized_name)
                was_in_session = normalized_name in self.session_names
                
                # Add to session names
                self.session_names.add(normalized_name)
                
                # If this name has been seen before (either in session or in database)
                if total_count > len(positions) or was_in_session:
                    duplicates.append({
                        'name': normalized_name,
                        'positions': positions,
                        'count': total_count,
                        'is_new_duplicate': not was_in_session
                    })
                    
                    logger.info(f"Duplicate detected: '{normalized_name}' (count: {total_count})")
            
            return duplicates
            
        except Exception as e:
            logger.error(f"Error processing names: {str(e)}", exc_info=True)
            return []
    
    def normalize_name(self, name):
        """Normalize name for comparison
        
        Args:
            name: Raw name string
            
        Returns:
            Normalized name string
        """
        # Convert to lowercase and strip whitespace
        normalized = name.lower().strip()
        
        # Remove common OCR artifacts
        normalized = normalized.replace('|', 'l')  # Pipe to lowercase L
        normalized = normalized.replace('0', 'o')  # Zero to lowercase O
        normalized = normalized.replace('1', 'l')  # One to lowercase L
        
        # Remove non-alphabetic characters except spaces and hyphens
        allowed_chars = set('abcdefghijklmnopqrstuvwxyz -')
        normalized = ''.join(c for c in normalized if c in allowed_chars)
        
        # Collapse multiple spaces
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def is_duplicate(self, name):
        """Check if a name is a duplicate
        
        Args:
            name: Name to check
            
        Returns:
            Boolean indicating if name is duplicate
        """
        normalized_name = self.normalize_name(name)
        return (normalized_name in self.session_names or 
                self.database.get_name_count(normalized_name) > 0)
    
    def get_name_statistics(self):
        """Get statistics about tracked names
        
        Returns:
            Dictionary with statistics
        """
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
        logger.info("Session data reset")
    
    def add_manual_name(self, name):
        """Manually add a name to tracking
        
        Args:
            name: Name to add
        """
        normalized_name = self.normalize_name(name)
        self.session_names.add(normalized_name)
        self.database.add_name_occurrence(normalized_name, 1)
        logger.info(f"Manually added name: '{normalized_name}'")
    
    def remove_name(self, name):
        """Remove a name from tracking
        
        Args:
            name: Name to remove
        """
        normalized_name = self.normalize_name(name)
        if normalized_name in self.session_names:
            self.session_names.remove(normalized_name)
        
        # Note: We don't remove from database to maintain history
        logger.info(f"Removed name from session: '{normalized_name}'")
    
    def get_duplicate_history(self, limit=100):
        """Get history of duplicate detections
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of duplicate detection records
        """
        try:
            return self.database.get_recent_names(limit)
        except Exception as e:
            logger.error(f"Error getting duplicate history: {str(e)}")
            return []
