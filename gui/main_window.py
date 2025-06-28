"""
Main GUI window for the Duplicate Name Highlighter application
"""

import sys
import logging

from PIL.ImageQt import QPixmap
from PyQt5.QtGui import QPainter, QColor, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QCheckBox, QMessageBox, QGroupBox, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, Qt

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


from core.screen_capture import ScreenCapture

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main settings window to control scanning and display status"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Duplicate Name Highlighter")
        self.setFixedSize(300, 300)

        # Core components
        self.screen_capture = ScreenCapture()

        # Region selector (PyQt overlay/dialog)
        self.region_selector = RegionSelector()
        self.region_selector.region_selected.connect(self.on_region_selected)

        # Build UI
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Region selection
        self.region_btn = QPushButton("Select Region")
        layout.addWidget(self.region_btn)

        # Auto-scan toggle
        self.auto_cb = QCheckBox("Enable Auto-Scan")
        self.auto_cb.setEnabled(False)  # овозможува по избор на регион
        layout.addWidget(self.auto_cb)

        # Scan interval
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Interval (s):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(3)
        hl.addWidget(self.interval_spin)
        layout.addLayout(hl)

        # Manual scan button (овозможи по избор на регион)
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

        self.manual_scan_btn.setEnabled(False)
        layout.addWidget(self.manual_scan_btn)

        # Reset and Clear
        self.reset_btn = QPushButton("Reset Session")
        self.clear_btn = QPushButton("Clear Database")
        layout.addWidget(self.reset_btn)
        layout.addWidget(self.clear_btn)

        # Status
        self.status_lbl = QLabel("Ready")
        layout.addWidget(self.status_lbl)

        # Timer for auto-scan
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan)

        # Connect UI signals
        self.region_btn.clicked.connect(self.select_region)
        self.auto_cb.toggled.connect(self.on_auto_toggled)
        self.interval_spin.valueChanged.connect(self.update_interval)
        self.manual_scan_btn.clicked.connect(self.scan)
        self.reset_btn.clicked.connect(self.reset_session)
        self.clear_btn.clicked.connect(self.clear_all)

        # Initialize interval
        self.update_interval(self.interval_spin.value())


    def select_region(self):
        """Hide main window, започни избор на регија, па прикажи повторно."""
        self.hide()
        self.region_selector.start_selection()
        self.show()

    def on_region_selected(self, region):
        """Callback кога корисникот завршил со избор на регија."""
        if region:
            self.screen_capture.set_region(region)
            self.status_lbl.setText(f"Region: {region}")
            logger.info(f"Region set to {region}")
            # Овозможи го auto-сакен и копчето за Scan
            self.auto_cb.setEnabled(True)
            self.manual_scan_btn.setEnabled(True)
        else:
            self.status_lbl.setText("No region selected")
            logger.info("Region selection cancelled")

    def on_auto_toggled(self, checked):
        """Start/stop periodic scanning."""
        if checked:
            if not self.screen_capture.region:
                QMessageBox.warning(
                    self, "No Region Selected",
                    "Please select a capture region first."
                )
                self.auto_cb.setChecked(False)
                return

            interval_ms = self.interval_spin.value() * 1000
            self.timer.start(interval_ms)
            self.status_lbl.setText(f"Auto-scan every {self.interval_spin.value()}s")
            logger.info("Auto-scan enabled")
        else:
            self.timer.stop()
            self.status_lbl.setText("Auto-scan disabled")
            logger.info("Auto-scan disabled")

    def update_interval(self, val):
        """Update timer interval."""
        self.timer.setInterval(val * 1000)
        if self.auto_cb.isChecked():
            self.timer.start()

    def scan(self):
        """Perform one scan."""
        if not self.screen_capture.region:
            QMessageBox.warning(
                self, "No Region Selected",
                "Please select a capture region first."
            )
            self.timer.stop()
            self.auto_cb.setChecked(False)
            self.status_lbl.setText("No region defined")
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

        self.status_lbl.setText("Scanning...")
        try:
            # ОВДЕ – повик без аргумент!
            ok = self.screen_capture.capture_and_process()

        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            self.status_lbl.setText("Scan error")
            return

        stats = self.screen_capture.get_statistics()
        if ok:
            self.status_lbl.setText(
                f"Session: {stats['session_names']} names, "
                f"{stats['session_occurrences']} occurrences"
            )
        else:
            self.status_lbl.setText("No change or no text")

    def reset_session(self):
        """Reset in-memory session counts."""
        reply = QMessageBox.question(
            self, "Reset Session",
            "Clear current session data?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.screen_capture.reset_session()
            self.status_lbl.setText("Session reset")
            logger.info("Session reset by user")

    def clear_all(self):
        """Clear both session and database."""
        reply = QMessageBox.question(
            self, "Clear Database",
            "Delete all stored data?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.screen_capture.clear_all()
            self.status_lbl.setText("Database cleared")
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

    def closeEvent(self, event):
        """Hide overlay and exit cleanly."""
        self.screen_capture.hide_overlay()
        event.accept()


def main():
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
