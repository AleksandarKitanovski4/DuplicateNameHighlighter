"""
Unit tests for settings dialog functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from gui.settings_dialog import SettingsDialog
from core.settings_manager import SettingsManager


class TestSettingsDialog(unittest.TestCase):
    """Test cases for SettingsDialog class"""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for testing"""
        cls.app = QApplication([])
    
    def setUp(self):
        """Set up test fixtures"""
        self.settings_manager = SettingsManager()
        self.dialog = SettingsDialog(self.settings_manager)
        
    def test_initialization(self):
        """Test SettingsDialog initialization"""
        self.assertIsNotNone(self.dialog)
        self.assertEqual(self.dialog.windowTitle(), "Settings")
        self.assertTrue(self.dialog.isModal())
        
    def test_export_csv_button_exists(self):
        """Test that Export CSV button exists in the dialog"""
        self.assertIsNotNone(self.dialog.export_csv_btn)
        self.assertEqual(self.dialog.export_csv_btn.text(), "Export CSV")
        
    @patch('gui.settings_dialog.QFileDialog.getExistingDirectory')
    @patch('gui.settings_dialog.QMessageBox.information')
    @patch('tracker.database.Database')
    def test_export_csv_success(self, mock_db_class, mock_message_box, mock_file_dialog):
        """Test successful CSV export"""
        # Mock file dialog to return a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file_dialog.return_value = temp_dir
            
            # Mock database export to return success
            mock_db = Mock()
            mock_db.export_to_csv.return_value = True
            mock_db_class.return_value = mock_db
            
            # Call export_csv method
            self.dialog.export_csv()
            
            # Verify database export was called
            mock_db.export_to_csv.assert_called_once()
            call_args = mock_db.export_to_csv.call_args[0][0]
            self.assertIn('duplicate_names.csv', call_args)
            self.assertIn(temp_dir, call_args)
            
            # Verify success message was shown
            mock_message_box.assert_called_once()
            call_args = mock_message_box.call_args
            self.assertEqual(call_args[0][1], "Export Complete")
            
    @patch('gui.settings_dialog.QFileDialog.getExistingDirectory')
    @patch('gui.settings_dialog.QMessageBox.warning')
    @patch('tracker.database.Database')
    def test_export_csv_failure(self, mock_db_class, mock_message_box, mock_file_dialog):
        """Test failed CSV export"""
        # Mock file dialog to return a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file_dialog.return_value = temp_dir
            
            # Mock database export to return failure
            mock_db = Mock()
            mock_db.export_to_csv.return_value = False
            mock_db_class.return_value = mock_db
            
            # Call export_csv method
            self.dialog.export_csv()
            
            # Verify failure message was shown
            mock_message_box.assert_called_once()
            call_args = mock_message_box.call_args
            self.assertEqual(call_args[0][1], "Export Failed")
            
    @patch('gui.settings_dialog.QFileDialog.getExistingDirectory')
    def test_export_csv_no_folder_selected(self, mock_file_dialog):
        """Test CSV export when no folder is selected"""
        # Mock file dialog to return empty string (user cancelled)
        mock_file_dialog.return_value = ""
        
        # Call export_csv method
        self.dialog.export_csv()
        
        # Verify no database operations were performed
        # (This would require more complex mocking to verify)
        
    @patch('gui.settings_dialog.QFileDialog.getExistingDirectory')
    @patch('gui.settings_dialog.QMessageBox.critical')
    @patch('tracker.database.Database')
    def test_export_csv_exception(self, mock_db_class, mock_message_box, mock_file_dialog):
        """Test CSV export with exception handling"""
        # Mock file dialog to return a temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_file_dialog.return_value = temp_dir
            
            # Mock database to raise an exception
            mock_db_class.side_effect = Exception("Database error")
            
            # Call export_csv method
            self.dialog.export_csv()
            
            # Verify error message was shown
            mock_message_box.assert_called_once()
            call_args = mock_message_box.call_args
            self.assertEqual(call_args[0][1], "Export Error")
            
    def test_export_csv_with_existing_folder(self):
        """Test CSV export when export folder is already set"""
        # Set export folder in the dialog
        test_folder = "/test/export/folder"
        self.dialog.export_folder_edit.setText(test_folder)
        
        with patch('gui.settings_dialog.QMessageBox.information') as mock_message_box, \
             patch('tracker.database.Database') as mock_db_class:
            
            # Mock database export to return success
            mock_db = Mock()
            mock_db.export_to_csv.return_value = True
            mock_db_class.return_value = mock_db
            
            # Call export_csv method
            self.dialog.export_csv()
            
            # Verify database export was called with correct path
            mock_db.export_to_csv.assert_called_once_with(f"{test_folder}/duplicate_names.csv")
            
            # Verify success message was shown
            mock_message_box.assert_called_once()
            
    def test_browse_export_folder(self):
        """Test browse export folder functionality"""
        test_folder = "/test/folder"
        
        with patch('gui.settings_dialog.QFileDialog.getExistingDirectory') as mock_file_dialog:
            mock_file_dialog.return_value = test_folder
            
            # Call browse_export_folder method
            self.dialog.browse_export_folder()
            
            # Verify the folder was set in the edit field
            self.assertEqual(self.dialog.export_folder_edit.text(), test_folder)
            
    def test_browse_export_folder_cancelled(self):
        """Test browse export folder when user cancels"""
        with patch('gui.settings_dialog.QFileDialog.getExistingDirectory') as mock_file_dialog:
            mock_file_dialog.return_value = ""
            
            # Set initial value
            initial_value = "/initial/folder"
            self.dialog.export_folder_edit.setText(initial_value)
            
            # Call browse_export_folder method
            self.dialog.browse_export_folder()
            
            # Verify the folder was not changed
            self.assertEqual(self.dialog.export_folder_edit.text(), initial_value)


if __name__ == '__main__':
    unittest.main() 