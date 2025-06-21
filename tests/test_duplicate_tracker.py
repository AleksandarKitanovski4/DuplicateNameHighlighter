import unittest
from tracker.duplicate_tracker import DuplicateTracker

class MockDatabase:
    def __init__(self):
        self.names = {}
    def add_name_occurrence(self, name, count=1):
        if name in self.names:
            self.names[name] += count
        else:
            self.names[name] = count
    def get_name_count(self, name):
        return self.names.get(name, 0)
    def get_statistics(self):
        return {'total_names': len(self.names), 'total_occurrences': sum(self.names.values())}
    def get_recent_names(self, limit=100):
        return list(self.names.keys())[:limit]

class TestDuplicateTracker(unittest.TestCase):
    def setUp(self):
        self.db = MockDatabase()
        self.tracker = DuplicateTracker(self.db)
    def test_insert_and_update(self):
        names = [
            {'name': 'Alice', 'x': 0, 'y': 0, 'width': 10, 'height': 10, 'confidence': 90},
            {'name': 'Bob', 'x': 0, 'y': 20, 'width': 10, 'height': 10, 'confidence': 90},
        ]
        # First scan
        dups = self.tracker.process_names(names)
        self.assertEqual(len(dups), 0)
        # Second scan with duplicate
        names2 = [
            {'name': 'Alice', 'x': 0, 'y': 0, 'width': 10, 'height': 10, 'confidence': 90},
            {'name': 'Alice', 'x': 0, 'y': 20, 'width': 10, 'height': 10, 'confidence': 90},
        ]
        dups2 = self.tracker.process_names(names2)
        self.assertTrue(any(d['name'] == 'alice' for d in dups2))
        self.assertEqual(self.db.get_name_count('alice'), 3)

if __name__ == '__main__':
    unittest.main() 