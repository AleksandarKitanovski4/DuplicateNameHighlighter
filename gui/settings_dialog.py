"""
Settings dialog for configuring application parameters
"""

import logging
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                            QPushButton, QLabel, QSpinBox, QLineEdit, QGroupBox,
                            QCheckBox, QComboBox, QColorDialog, QFileDialog,
                            QMessageBox, QTabWidget, QWidget, QSlider)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    settings_changed = pyqtSignal()  # Emitted when settings are changed
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setup_ui()
        self.load_current_settings()
        
        logger.info("Settings dialog initialized")
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # General settings tab
        general_tab = self.create_general_tab()
        tab_widget.addTab(general_tab, "General")
        
        # OCR settings tab
        ocr_tab = self.create_ocr_tab()
        tab_widget.addTab(ocr_tab, "OCR")
        
        # Display settings tab
        display_tab = self.create_display_tab()
        tab_widget.addTab(display_tab, "Display")
        
        # Export settings tab
        export_tab = self.create_export_tab()
        tab_widget.addTab(export_tab, "Export")
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.reset_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def create_general_tab(self):
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Auto-scan settings
        scan_group = QGroupBox("Auto-Scan Settings")
        scan_layout = QGridLayout(scan_group)
        
        scan_layout.addWidget(QLabel("Scan Interval (seconds):"), 0, 0)
        self.scan_interval_spin = QSpinBox()
        self.scan_interval_spin.setRange(1, 60)
        self.scan_interval_spin.setValue(3)
        scan_layout.addWidget(self.scan_interval_spin, 0, 1)
        
        scan_layout.addWidget(QLabel("Change Detection Threshold:"), 1, 0)
        self.hash_threshold_spin = QSpinBox()
        self.hash_threshold_spin.setRange(1, 20)
        self.hash_threshold_spin.setValue(5)
        scan_layout.addWidget(self.hash_threshold_spin, 1, 1)
        
        layout.addWidget(scan_group)
        
        # Scroll detection settings
        scroll_group = QGroupBox("Scroll Detection")
        scroll_layout = QGridLayout(scroll_group)
        
        scroll_layout.addWidget(QLabel("Scroll Detection Threshold:"), 0, 0)
        self.scroll_threshold_spin = QSpinBox()
        self.scroll_threshold_spin.setRange(5, 50)
        self.scroll_threshold_spin.setValue(10)
        scroll_layout.addWidget(self.scroll_threshold_spin, 0, 1)
        
        layout.addWidget(scroll_group)
        
        layout.addStretch()
        return widget
    
    def create_ocr_tab(self):
        """Create OCR settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # OCR configuration
        ocr_group = QGroupBox("OCR Configuration")
        ocr_layout = QGridLayout(ocr_group)
        
        ocr_layout.addWidget(QLabel("Language:"), 0, 0)
        self.language_combo = QComboBox()
        self.language_combo.addItems(["eng", "fra", "deu", "spa", "ita"])
        ocr_layout.addWidget(self.language_combo, 0, 1)
        
        ocr_layout.addWidget(QLabel("Page Segmentation Mode:"), 1, 0)
        self.psm_spin = QSpinBox()
        self.psm_spin.setRange(0, 13)
        self.psm_spin.setValue(6)
        ocr_layout.addWidget(self.psm_spin, 1, 1)
        
        ocr_layout.addWidget(QLabel("Minimum Confidence (%):"), 2, 0)
        self.min_confidence_spin = QSpinBox()
        self.min_confidence_spin.setRange(0, 100)
        self.min_confidence_spin.setValue(30)
        ocr_layout.addWidget(self.min_confidence_spin, 2, 1)
        
        ocr_layout.addWidget(QLabel("Character Whitelist:"), 3, 0)
        self.whitelist_edit = QLineEdit()
        self.whitelist_edit.setText("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ")
        ocr_layout.addWidget(self.whitelist_edit, 3, 1)
        
        layout.addWidget(ocr_group)
        layout.addStretch()
        return widget
    
    def create_display_tab(self):
        """Create display settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Marker colors
        color_group = QGroupBox("Marker Colors")
        color_layout = QGridLayout(color_group)
        
        # First duplicate color
        color_layout.addWidget(QLabel("First Duplicate (Count=2):"), 0, 0)
        self.first_duplicate_color_btn = QPushButton()
        self.first_duplicate_color_btn.setFixedSize(60, 25)
        self.first_duplicate_color_btn.clicked.connect(lambda: self.choose_color('first_duplicate'))
        color_layout.addWidget(self.first_duplicate_color_btn, 0, 1)
        
        # Multiple duplicates color
        color_layout.addWidget(QLabel("Multiple Duplicates (Count≥3):"), 1, 0)
        self.multiple_duplicate_color_btn = QPushButton()
        self.multiple_duplicate_color_btn.setFixedSize(60, 25)
        self.multiple_duplicate_color_btn.clicked.connect(lambda: self.choose_color('multiple_duplicate'))
        color_layout.addWidget(self.multiple_duplicate_color_btn, 1, 1)
        
        layout.addWidget(color_group)
        
        # Marker style
        style_group = QGroupBox("Marker Style")
        style_layout = QGridLayout(style_group)
        
        style_layout.addWidget(QLabel("Marker Opacity (%):"), 0, 0)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(70)
        style_layout.addWidget(self.opacity_slider, 0, 1)
        
        layout.addWidget(style_group)
        layout.addStretch()
        return widget
    
    def create_export_tab(self):
        """Create export settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # CSV export settings
        export_group = QGroupBox("CSV Export")
        export_layout = QGridLayout(export_group)
        
        export_layout.addWidget(QLabel("Export Folder:"), 0, 0)
        self.export_folder_edit = QLineEdit()
        self.export_folder_edit.setPlaceholderText("Select folder for CSV exports")
        export_layout.addWidget(self.export_folder_edit, 0, 1)
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_export_folder)
        export_layout.addWidget(self.browse_btn, 0, 2)
        
        export_layout.addWidget(QLabel("Auto-export on session end:"), 1, 0)
        self.auto_export_checkbox = QCheckBox()
        export_layout.addWidget(self.auto_export_checkbox, 1, 1)
        
        layout.addWidget(export_group)
        layout.addStretch()
        return widget
    
    def choose_color(self, color_type):
        """Open color picker dialog"""
        current_color = self.get_current_color(color_type)
        color = QColorDialog.getColor(current_color, self, f"Choose {color_type.replace('_', ' ').title()} Color")
        
        if color.isValid():
            if color_type == 'first_duplicate':
                self.first_duplicate_color_btn.setStyleSheet(f"background-color: {color.name()}")
            elif color_type == 'multiple_duplicate':
                self.multiple_duplicate_color_btn.setStyleSheet(f"background-color: {color.name()}")
    
    def get_current_color(self, color_type):
        """Get current color for color type"""
        if color_type == 'first_duplicate':
            return QColor(255, 165, 0)  # Orange
        elif color_type == 'multiple_duplicate':
            return QColor(255, 0, 0)    # Red
        return QColor(255, 255, 255)    # Default white
    
    def browse_export_folder(self):
        """Browse for export folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if folder:
            self.export_folder_edit.setText(folder)
    
    def load_current_settings(self):
        """Load current settings into the dialog"""
        try:
            # General settings
            self.scan_interval_spin.setValue(self.settings_manager.get_setting('scan_interval', 3))
            self.hash_threshold_spin.setValue(self.settings_manager.get_setting('hash_threshold', 5))
            self.scroll_threshold_spin.setValue(self.settings_manager.get_setting('scroll_threshold', 10))
            
            # OCR settings
            self.language_combo.setCurrentText(self.settings_manager.get_setting('ocr_config.language', 'eng'))
            self.psm_spin.setValue(self.settings_manager.get_setting('ocr_config.psm', 6))
            self.min_confidence_spin.setValue(self.settings_manager.get_setting('min_confidence', 30))
            self.whitelist_edit.setText(self.settings_manager.get_setting('ocr_config.whitelist_chars', 
                                                                        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '))
            
            # Display settings
            marker_colors = self.settings_manager.get_setting('marker_colors', {})
            first_color = marker_colors.get('duplicate', [255, 165, 0, 180])
            multiple_color = marker_colors.get('multiple', [255, 0, 0, 180])
            
            self.first_duplicate_color_btn.setStyleSheet(f"background-color: rgb({first_color[0]}, {first_color[1]}, {first_color[2]})")
            self.multiple_duplicate_color_btn.setStyleSheet(f"background-color: rgb({multiple_color[0]}, {multiple_color[1]}, {multiple_color[2]})")
            
            opacity = int(marker_colors.get('duplicate', [255, 165, 0, 180])[3] * 100 / 255)
            self.opacity_slider.setValue(opacity)
            
            # Export settings
            self.export_folder_edit.setText(self.settings_manager.get_setting('export_folder', ''))
            self.auto_export_checkbox.setChecked(self.settings_manager.get_setting('auto_export', False))
            
        except Exception as e:
            logger.error(f"Error loading settings: {str(e)}")
    
    def save_settings(self):
        """Save settings from dialog"""
        try:
            # General settings
            self.settings_manager.set_setting('scan_interval', self.scan_interval_spin.value())
            self.settings_manager.set_setting('hash_threshold', self.hash_threshold_spin.value())
            self.settings_manager.set_setting('scroll_threshold', self.scroll_threshold_spin.value())
            
            # OCR settings
            self.settings_manager.set_setting('ocr_config.language', self.language_combo.currentText())
            self.settings_manager.set_setting('ocr_config.psm', self.psm_spin.value())
            self.settings_manager.set_setting('min_confidence', self.min_confidence_spin.value())
            self.settings_manager.set_setting('ocr_config.whitelist_chars', self.whitelist_edit.text())
            
            # Display settings
            opacity = self.opacity_slider.value() / 100.0
            
            # Get colors from buttons
            first_color_style = self.first_duplicate_color_btn.styleSheet()
            multiple_color_style = self.multiple_duplicate_color_btn.styleSheet()
            
            # Parse colors (simplified - in production you'd want more robust parsing)
            first_color = [255, 165, 0, int(255 * opacity)]  # Default orange
            multiple_color = [255, 0, 0, int(255 * opacity)]  # Default red
            
            marker_colors = {
                'duplicate': first_color,
                'multiple': multiple_color,
                'opacity': opacity
            }
            self.settings_manager.set_setting('marker_colors', marker_colors)
            
            # Export settings
            self.settings_manager.set_setting('export_folder', self.export_folder_edit.text())
            self.settings_manager.set_setting('auto_export', self.auto_export_checkbox.isChecked())
            
            # Save to file
            if self.settings_manager.save_settings():
                self.settings_changed.emit()
                self.accept()
                logger.info("Settings saved successfully")
            else:
                QMessageBox.warning(self, "Error", "Failed to save settings")
                
        except Exception as e:
            logger.error(f"Error saving settings: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(self, "Reset Settings", 
                                   "Reset all settings to defaults? This cannot be undone.",
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_to_defaults()
            self.load_current_settings()
            logger.info("Settings reset to defaults") 