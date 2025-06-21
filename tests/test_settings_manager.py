import unittest
import os
import json
from core.settings_manager import SettingsManager

class TestSettingsManager(unittest.TestCase):
    def setUp(self):
        self.test_file = 'test_settings.json'
        # Remove if exists
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
    def test_load_defaults(self):
        sm = SettingsManager(settings_file=self.test_file)
        self.assertIn('scan_interval', sm.settings)
        self.assertEqual(sm.get_setting('scan_interval'), 3)
    def test_save_and_load(self):
        sm = SettingsManager(settings_file=self.test_file)
        sm.set_setting('scan_interval', 7)
        sm.save_settings()
        sm2 = SettingsManager(settings_file=self.test_file)
        self.assertEqual(sm2.get_setting('scan_interval'), 7)

if __name__ == '__main__':
    unittest.main() 