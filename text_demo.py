#!/usr/bin/env python3
"""
Text-based demo of duplicate name detection logic
"""

import sqlite3
import json
from datetime import datetime

class SimpleDuplicateTracker:
    """Simple duplicate tracker without complex dependencies"""
    
    def __init__(self):
        self.db_file = 'demo.db'
        self.init_database()
        self.session_names = set()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS names (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                count INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def normalize_name(self, name):
        """Normalize name for comparison"""
        return name.lower().strip()
    
    def add_name(self, name):
        """Add name to database and session"""
        normalized = self.normalize_name(name)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check if name exists
        cursor.execute('SELECT count FROM names WHERE name = ?', (normalized,))
        result = cursor.fetchone()
        
        if result:
            # Update existing
            new_count = result[0] + 1
            cursor.execute('UPDATE names SET count = ?, last_seen = CURRENT_TIMESTAMP WHERE name = ?', 
                         (new_count, normalized))
        else:
            # Insert new
            cursor.execute('INSERT INTO names (name) VALUES (?)', (normalized,))
            new_count = 1
        
        conn.commit()
        conn.close()
        
        # Track in session
        is_duplicate = normalized in self.session_names or new_count > 1
        self.session_names.add(normalized)
        
        return {
            'name': normalized,
            'count': new_count,
            'is_duplicate': is_duplicate,
            'is_session_duplicate': normalized in self.session_names and new_count == 1
        }
    
    def get_duplicates(self):
        """Get all duplicate names"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT name, count FROM names WHERE count > 1 ORDER BY count DESC')
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_stats(self):
        """Get statistics"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) as total, SUM(count) as occurrences FROM names')
        result = cursor.fetchone()
        cursor.execute('SELECT COUNT(*) as duplicates FROM names WHERE count > 1')
        dup_result = cursor.fetchone()
        conn.close()
        
        return {
            'total_unique_names': result[0] if result else 0,
            'total_occurrences': result[1] if result else 0,
            'duplicate_names': dup_result[0] if dup_result else 0,
            'session_names': len(self.session_names)
        }

def simulate_ocr_scan(names_list):
    """Simulate OCR extracting names from an image"""
    print(f"📷 Simulating OCR scan - found {len(names_list)} names:")
    for i, name in enumerate(names_list, 1):
        print(f"  {i}. {name}")
    return names_list

def main():
    """Main demonstration"""
    print("🔍 Duplicate Name Highlighter - Text Demo")
    print("=" * 50)
    
    # Initialize tracker
    tracker = SimpleDuplicateTracker()
    
    # Simulate multiple OCR scans with different name sets
    scan_scenarios = [
        {
            'description': 'First scan - Employee list',
            'names': ['John Smith', 'Alice Johnson', 'Bob Wilson', 'Carol Davis']
        },
        {
            'description': 'Second scan - Meeting attendees',  
            'names': ['John Smith', 'David Brown', 'Alice Johnson', 'Eve Miller']
        },
        {
            'description': 'Third scan - Project team',
            'names': ['Bob Wilson', 'Frank Garcia', 'John Smith', 'Grace Lee']
        },
        {
            'description': 'Fourth scan - Department roster',
            'names': ['Alice Johnson', 'Henry Taylor', 'John Smith', 'Ivy Anderson']
        }
    ]
    
    # Process each scan
    for scan_num, scenario in enumerate(scan_scenarios, 1):
        print(f"\n📋 Scan #{scan_num}: {scenario['description']}")
        print("-" * 40)
        
        # Simulate OCR extraction
        extracted_names = simulate_ocr_scan(scenario['names'])
        
        # Process names for duplicates
        duplicates_found = []
        for name in extracted_names:
            result = tracker.add_name(name)
            if result['is_duplicate']:
                duplicates_found.append(result)
        
        # Report duplicates found in this scan
        if duplicates_found:
            print(f"\n🚨 Duplicates detected in this scan:")
            for dup in duplicates_found:
                status = "NEW DUPLICATE" if dup['count'] == 2 else f"SEEN {dup['count']} TIMES"
                print(f"  ⚠️  '{dup['name']}' - {status}")
        else:
            print(f"\n✅ No duplicates found in this scan")
        
        # Show current statistics
        stats = tracker.get_stats()
        print(f"\n📊 Current Stats:")
        print(f"  • Unique names seen: {stats['total_unique_names']}")
        print(f"  • Total occurrences: {stats['total_occurrences']}")
        print(f"  • Names with duplicates: {stats['duplicate_names']}")
        print(f"  • Names in this session: {stats['session_names']}")
    
    # Final summary
    print(f"\n🎯 Final Results")
    print("=" * 30)
    all_duplicates = tracker.get_duplicates()
    
    if all_duplicates:
        print(f"Found {len(all_duplicates)} names with duplicates:")
        for name, count in all_duplicates:
            print(f"  🔴 '{name}' appeared {count} times")
    else:
        print("No duplicates found across all scans")
    
    # Simulate overlay display
    print(f"\n🖥️  Overlay Display Simulation")
    print("-" * 35)
    print("In the real application, these names would be highlighted:")
    for name, count in all_duplicates:
        color = "🟠 ORANGE" if count == 2 else "🔴 RED" if count >= 3 else "🟡 YELLOW"
        print(f"  {color} marker for '{name}' ({count} occurrences)")
    
    print(f"\n✨ Demo completed successfully!")
    print("The full application would:")
    print("  • Monitor a selected screen region continuously")
    print("  • Use OCR to extract text from screenshots")  
    print("  • Show transparent overlay markers on duplicate names")
    print("  • Provide a GUI for configuration and control")

if __name__ == "__main__":
    main()