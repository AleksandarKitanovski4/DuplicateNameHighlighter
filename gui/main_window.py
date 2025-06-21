"""
Main GUI window for the Duplicate Name Highlighter application
"""

import logging
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QSpinBox, QCheckBox, QGroupBox,
                            QMessageBox, QSystemTrayIcon, QMenu, QAction)
from PyQt5.QtCore import QTimer, QThread, pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from gui.region_selector import RegionSelector
from gui.overlay_window import OverlayWindow
from core.ocr_processor import OCRProcessor
from tracker.duplicate_tracker import DuplicateTracker
from core.screen_capture import ScreenCapture
from tracker.database import Database

logger = logging.getLogger(__name__)

class ScanWorker(QThread):
    """Worker thread for OCR scanning operations"""
    
    scan_completed = pyqtSignal(list)  # Emits list of detected names with positions
    scroll_detected = pyqtSignal(dict)  # Emits scroll detection info
    error_occurred = pyqtSignal(str)
    
    def __init__(self, screen_capture, ocr_processor, region):
        super().__init__()
        self.screen_capture = screen_capture
        self.ocr_processor = ocr_processor
        self.region = region
        self.running = False
    
    def run(self):
        """Execute OCR scan in background thread"""
        try:
            self.running = True
            
            # Capture screenshot of region
            screenshot = self.screen_capture.capture_region(self.region)
            if screenshot is None:
                self.error_occurred.emit("Failed to capture screenshot")
                return
            
            # Check for scroll events first
            scroll_info = self.screen_capture.detect_scroll(screenshot)
            if scroll_info and scroll_info['confidence'] > 0.8:
                self.scroll_detected.emit(scroll_info)
                logger.info(f"Scroll detected: {scroll_info['direction']} (confidence: {scroll_info['confidence']:.3f})")
            
            # Check if image has changed
            if not self.screen_capture.has_changed(screenshot):
                logger.debug("No changes detected, skipping OCR")
                return
            
            # Process with OCR
            names_with_positions = self.ocr_processor.extract_text_with_positions(screenshot)
            self.scan_completed.emit(names_with_positions)
            
        except Exception as e:
            logger.error(f"Error in scan worker: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"Scan error: {str(e)}")
        finally:
            self.running = False
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        self.quit()
        self.wait()

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager
        self.setup_components()
        self.setup_ui()
        self.setup_system_tray()
        self.load_settings()
        
        # Worker thread for OCR processing
        self.scan_worker = None
        
        # Timer for automatic scanning
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.perform_scan)
        
        logger.info("Main window initialized")
    
    def setup_components(self):
        """Initialize core components"""
        self.database = Database()
        self.duplicate_tracker = DuplicateTracker(self.database)
        self.screen_capture = ScreenCapture()
        self.ocr_processor = OCRProcessor()
        self.overlay_window = OverlayWindow()
        self.region_selector = RegionSelector()
        
        # Connect signals
        self.region_selector.region_selected.connect(self.on_region_selected)
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Duplicate Name Highlighter")
        self.setFixedSize(400, 300)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Region selection group
        region_group = QGroupBox("Screen Region")
        region_layout = QVBoxLayout(region_group)
        
        self.region_label = QLabel("No region selected")
        self.region_label.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        region_layout.addWidget(self.region_label)
        
        self.select_region_btn = QPushButton("Select Region")
        self.select_region_btn.clicked.connect(self.select_region)
        region_layout.addWidget(self.select_region_btn)
        
        layout.addWidget(region_group)
        
        # Scanning controls group
        scan_group = QGroupBox("Scanning Controls")
        scan_layout = QVBoxLayout(scan_group)
        
        # Auto-scan checkbox
        self.auto_scan_checkbox = QCheckBox("Enable Auto-Scan")
        self.auto_scan_checkbox.toggled.connect(self.toggle_auto_scan)
        scan_layout.addWidget(self.auto_scan_checkbox)
        
        # Scan interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Scan Interval (seconds):"))
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(1, 60)
        self.interval_spinbox.setValue(3)
        self.interval_spinbox.valueChanged.connect(self.update_scan_interval)
        interval_layout.addWidget(self.interval_spinbox)
        scan_layout.addLayout(interval_layout)
        
        # Manual scan button
        self.manual_scan_btn = QPushButton("Scan Now")
        self.manual_scan_btn.clicked.connect(self.perform_scan)
        scan_layout.addWidget(self.manual_scan_btn)
        
        layout.addWidget(scan_group)
        
        # Session management group
        session_group = QGroupBox("Session Management")
        session_layout = QVBoxLayout(session_group)
        
        self.reset_session_btn = QPushButton("Reset Current Session")
        self.reset_session_btn.clicked.connect(self.reset_session)
        session_layout.addWidget(self.reset_session_btn)
        
        self.clear_database_btn = QPushButton("Clear Database")
        self.clear_database_btn.clicked.connect(self.clear_database)
        session_layout.addWidget(self.clear_database_btn)
        
        # Export CSV button
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        session_layout.addWidget(self.export_csv_btn)
        
        # Show Logs button
        self.show_logs_btn = QPushButton("Show Logs")
        self.show_logs_btn.clicked.connect(self.show_logs)
        session_layout.addWidget(self.show_logs_btn)
        
        layout.addWidget(session_group)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("QLabel { color: #007ACC; }")
        layout.addWidget(self.status_label)
    
    def setup_system_tray(self):
        """Setup system tray icon"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available")
            return
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Create a simple icon programmatically
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(0, 122, 204))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Duplicate Name Highlighter")
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        """Handle system tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            logger.info("Application minimized to system tray")
        else:
            self.quit_application()
    
    def quit_application(self):
        """Quit the application completely"""
        logger.info("Shutting down application")
        
        # Stop scanning
        self.scan_timer.stop()
        if self.scan_worker and self.scan_worker.isRunning():
            self.scan_worker.stop()
        
        # Hide overlay
        self.overlay_window.hide()
        
        # Save settings
        self.save_settings()
        
        # Close database
        self.database.close()
        
        # Quit application
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()
    
    def select_region(self):
        """Open region selection dialog"""
        self.hide()  # Hide main window during selection
        self.region_selector.start_selection()
    
    def on_region_selected(self, region):
        """Handle region selection completion"""
        self.show()  # Show main window again
        if region:
            x, y, width, height = region
            self.region_label.setText(f"Region: {x},{y} ({width}x{height})")
            self.region_label.setStyleSheet("QLabel { color: #000; }")
            self.settings_manager.set_setting('region', region)
            logger.info(f"Region selected: {region}")
        else:
            logger.info("Region selection cancelled")
    
    def toggle_auto_scan(self, enabled):
        """Toggle automatic scanning"""
        if enabled and self.get_current_region():
            interval = self.interval_spinbox.value() * 1000  # Convert to milliseconds
            self.scan_timer.start(interval)
            self.status_label.setText(f"Auto-scanning every {self.interval_spinbox.value()}s")
            logger.info("Auto-scan enabled")
        else:
            self.scan_timer.stop()
            self.status_label.setText("Auto-scan disabled")
            logger.info("Auto-scan disabled")
    
    def update_scan_interval(self, value):
        """Update scanning interval"""
        if self.scan_timer.isActive():
            self.scan_timer.start(value * 1000)  # Restart with new interval
            self.status_label.setText(f"Auto-scanning every {value}s")
    
    def get_current_region(self):
        """Get the currently selected region"""
        return self.settings_manager.get_setting('region')
    
    def perform_scan(self):
        """Perform OCR scan of the selected region"""
        region = self.get_current_region()
        if not region:
            self.status_label.setText("Please select a region first")
            return
        
        if self.scan_worker and self.scan_worker.isRunning():
            logger.debug("Scan already in progress, skipping")
            return
        
        self.status_label.setText("Scanning...")
        self.manual_scan_btn.setEnabled(False)
        
        # Start scan in worker thread
        self.scan_worker = ScanWorker(self.screen_capture, self.ocr_processor, region)
        self.scan_worker.scan_completed.connect(self.on_scan_completed)
        self.scan_worker.scroll_detected.connect(self.on_scroll_detected)
        self.scan_worker.error_occurred.connect(self.on_scan_error)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.start()
    
    def on_scroll_detected(self, scroll_info):
        """Handle scroll detection"""
        try:
            # Adjust existing marker positions
            current_markers = self.overlay_window.get_current_markers()
            if current_markers:
                adjusted_markers = self.screen_capture.adjust_marker_positions(current_markers, scroll_info)
                self.overlay_window.update_markers_from_adjusted(adjusted_markers)
                
                # Check for names scrolled out of view
                region = self.get_current_region()
                if region:
                    scrolled_out = self.duplicate_tracker.get_names_scrolled_out(region[3])  # height
                    if scrolled_out:
                        logger.info(f"Names scrolled out of view: {scrolled_out}")
            
            self.status_label.setText(f"Scroll detected: {scroll_info['direction']}")
            
        except Exception as e:
            logger.error(f"Error handling scroll detection: {str(e)}", exc_info=True)
    
    def on_scan_completed(self, names_with_positions):
        """Handle completed OCR scan"""
        try:
            # Check for scroll events and get scroll info
            scroll_info = None
            if hasattr(self.screen_capture, 'get_scroll_history'):
                scroll_history = self.screen_capture.get_scroll_history()
                if scroll_history:
                    scroll_info = scroll_history[-1]  # Most recent scroll event
            
            # Process detected names with scroll info
            duplicates = self.duplicate_tracker.process_names(names_with_positions, scroll_info)
            
            if duplicates:
                # Update overlay with duplicate markers
                region = self.get_current_region()
                self.overlay_window.update_markers(duplicates, region)
                self.status_label.setText(f"Found {len(duplicates)} duplicates")
                logger.info(f"Detected {len(duplicates)} duplicate names")
            else:
                self.overlay_window.clear_markers()
                self.status_label.setText("No duplicates found")
                
        except Exception as e:
            logger.error(f"Error processing scan results: {str(e)}", exc_info=True)
            self.status_label.setText("Error processing results")
    
    def on_scan_error(self, error_message):
        """Handle scan error"""
        self.status_label.setText(f"Scan error: {error_message}")
        logger.error(f"Scan error: {error_message}")
    
    def on_scan_finished(self):
        """Handle scan completion"""
        self.manual_scan_btn.setEnabled(True)
    
    def reset_session(self):
        """Reset the current session"""
        reply = QMessageBox.question(self, 'Reset Session', 
                                   'Reset current session memory? This will clear all tracked names for this session.',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.duplicate_tracker.reset_session()
            self.overlay_window.clear_markers()
            self.status_label.setText("Session reset")
            logger.info("Session reset by user")
    
    def clear_database(self):
        """Clear the entire database"""
        reply = QMessageBox.question(self, 'Clear Database', 
                                   'Clear entire database? This will permanently delete all stored data.',
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.database.clear_all_data()
            self.duplicate_tracker.reset_session()
            self.overlay_window.clear_markers()
            self.status_label.setText("Database cleared")
            logger.info("Database cleared by user")
    
    def load_settings(self):
        """Load settings from configuration"""
        # Load region
        region = self.settings_manager.get_setting('region')
        if region:
            x, y, width, height = region
            self.region_label.setText(f"Region: {x},{y} ({width}x{height})")
            self.region_label.setStyleSheet("QLabel { color: #000; }")
        
        # Load auto-scan setting
        auto_scan = self.settings_manager.get_setting('auto_scan', False)
        self.auto_scan_checkbox.setChecked(auto_scan)
        
        # Load scan interval
        interval = self.settings_manager.get_setting('scan_interval', 3)
        self.interval_spinbox.setValue(interval)
        
        logger.info("Settings loaded")
    
    def save_settings(self):
        """Save current settings"""
        self.settings_manager.set_setting('auto_scan', self.auto_scan_checkbox.isChecked())
        self.settings_manager.set_setting('scan_interval', self.interval_spinbox.value())
        self.settings_manager.save_settings()
        logger.info("Settings saved")

    def export_csv(self):
        """Export all seen names to a CSV file"""
        import csv
        from PyQt5.QtWidgets import QFileDialog
        import os
        
        # Get export folder from settings
        export_folder = self.settings_manager.get_setting('export_folder', '')
        if not export_folder:
            export_folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
            if not export_folder:
                self.status_label.setText("Export cancelled")
                return
            self.settings_manager.set_setting('export_folder', export_folder)
            self.settings_manager.save_settings()
        
        # Compose export file path
        from datetime import datetime
        filename = f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        export_path = os.path.join(export_folder, filename)
        
        # Fetch all seen names from the database
        try:
            seen_names = self.database.get_all_seen_names()
            if not seen_names:
                self.status_label.setText("No names to export")
                return
            
            with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['name', 'first_seen_timestamp', 'count'])
                for row in seen_names:
                    writer.writerow(row)
            
            self.status_label.setText(f"Exported to {export_path}")
            logger.info(f"Exported CSV to {export_path}")
        except Exception as e:
            self.status_label.setText("Export failed")
            logger.error(f"CSV export failed: {str(e)}")

    def show_logs(self):
        """Open the current log file in the default system editor"""
        import subprocess
        import platform
        import os
        
        log_file = 'duplicate_highlighter.log'
        
        if not os.path.exists(log_file):
            self.status_label.setText("No log file found")
            return
        
        try:
            system = platform.system()
            
            if system == "Windows":
                os.startfile(log_file)
            elif system == "Darwin":  # macOS
                subprocess.run(['open', log_file], check=True)
            else:  # Linux
                subprocess.run(['xdg-open', log_file], check=True)
            
            self.status_label.setText("Log file opened")
            logger.info("Log file opened by user")
            
        except Exception as e:
            self.status_label.setText("Failed to open log file")
            logger.error(f"Failed to open log file: {str(e)}")
