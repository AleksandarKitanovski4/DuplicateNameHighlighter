"""
Main GUI window for the Duplicate Name Highlighter application
"""

import sys
import logging
import time

from PyQt5.QtGui import QPixmap, QPainter, QColor, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QCheckBox, QMessageBox,
    QGroupBox, QSystemTrayIcon, QMenu, QAction
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
    scan_completed = pyqtSignal(list)
    scroll_detected = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, screen_capture, ocr_processor, region):
        super().__init__()
        self.screen_capture = screen_capture
        self.ocr_processor = ocr_processor
        self.region = region
        self.running = False

    # … rest of ScanWorker methods …



class MainWindow(QMainWindow):
    """Main settings window to control scanning and display status"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Duplicate Name Highlighter")
        self.setFixedSize(300, 300)

        # Core components
        self.screen_capture  = ScreenCapture()
        self.database        = Database("duplicate_names.db")
        self.ocr_processor   = OCRProcessor()
        self.overlay_window  = OverlayWindow()
        self.duplicate_tracker = DuplicateTracker(self.database, overlay=self.overlay_window)

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
        self.auto_cb.setEnabled(False)
        layout.addWidget(self.auto_cb)

        # Scan interval
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Interval (s):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(3)
        hl.addWidget(self.interval_spin)
        layout.addLayout(hl)

        # Manual scan button group
        scan_group = QGroupBox("Scan Options")
        scan_layout = QHBoxLayout(scan_group)
        self.manual_scan_btn = QPushButton("Scan Now")
        self.manual_scan_btn.clicked.connect(self.scan)
        scan_layout.addWidget(self.manual_scan_btn)
        scan_group.setLayout(scan_layout)
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
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self.export_csv)
        session_layout.addWidget(self.export_csv_btn)
        self.show_logs_btn = QPushButton("Show Logs")
        self.show_logs_btn.clicked.connect(self.show_logs)
        session_layout.addWidget(self.show_logs_btn)
        session_group.setLayout(session_layout)
        layout.addWidget(session_group)

        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("QLabel { color: #007ACC; }")
        layout.addWidget(self.status_label)

        # Timer and signals
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan)
        self.region_btn.clicked.connect(self.select_region)
        self.auto_cb.toggled.connect(self.on_auto_toggled)
        self.interval_spin.valueChanged.connect(self.update_interval)

    def setup_system_tray(self):
        """Setup system tray icon"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available")
            return
        self.tray_icon = QSystemTrayIcon(self)
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(0, 122, 204))
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()
        self.tray_icon.setIcon(QIcon(pixmap))
        self.tray_icon.setToolTip("Duplicate Name Highlighter")
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
        """Hide overlay and exit cleanly."""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
            logger.info("Application minimized to system tray")
        else:
            self.quit_application()

    def quit_application(self):
        """Quit the application completely"""
        logger.info("Shutting down application")
        if self.timer.isActive():
            self.timer.stop()
        if hasattr(self, 'scan_worker') and self.scan_worker.isRunning():
            self.scan_worker.stop()
        if hasattr(self, 'overlay_window'):
            self.overlay_window.hide()
        self.save_settings()
        self.database.close()
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()

    def select_region(self):
        """Start region selection"""
        self.hide()
        self.region_selector.start_selection()
        self.show()

    def on_region_selected(self, region):
        """Region selected callback"""
        if region:
            self.screen_capture.set_region(region)
            self.status_label.setText(f"Region: {region}")
            self.auto_cb.setEnabled(True)
            self.manual_scan_btn.setEnabled(True)
        else:
            self.status_label.setText("No region selected")

    def on_auto_toggled(self, checked):
        """Toggle auto-scan"""
        if checked:
            if not self.screen_capture.region:
                QMessageBox.warning(self, "No Region Selected",
                                    "Please select a capture region first.")
                self.auto_cb.setChecked(False)
                return
            self.timer.start(self.interval_spin.value() * 1000)
            self.status_label.setText(f"Auto-scan every {self.interval_spin.value()}s")
        else:
            self.timer.stop()
            self.status_label.setText("Auto-scan disabled")

    def update_interval(self, val):
        """Update scan interval"""
        self.timer.setInterval(val * 1000)
        if self.auto_cb.isChecked():
            self.timer.start()

    def scan(self):
        """Perform one scan"""
        if not self.screen_capture.region:
            QMessageBox.warning(self, "No Region Selected",
                                "Please select a capture region first.")
            self.auto_cb.setChecked(False)
            return
        if hasattr(self, 'scan_worker') and self.scan_worker.isRunning():
            logger.debug("Scan already in progress")
            return
        self.status_label.setText("Scanning...")
        self.manual_scan_btn.setEnabled(False)
        self.scan_worker = ScanWorker(self.screen_capture,
                                      self.ocr_processor,
                                      self.screen_capture.region)
        self.scan_worker.scan_completed.connect(self.on_scan_completed)
        self.scan_worker.scroll_detected.connect(self.on_scroll_detected)
        self.scan_worker.error_occurred.connect(self.on_scan_error)
        self.scan_worker.start()

    def on_scroll_detected(self, scroll_info):
        """Handle scroll detection"""
        try:
            markers = self.overlay_window.get_current_markers()
            if markers:
                adjusted = self.screen_capture.adjust_marker_positions(markers, scroll_info)
                self.overlay_window.update_markers_from_adjusted(adjusted)
            self.status_label.setText(f"Scroll: {scroll_info['direction']}")
        except Exception as e:
            logger.error(f"Scroll handling error: {e}")

    def on_scan_completed(self, names_with_positions):
        """Handle completed OCR scan"""
        # Scroll info
        scroll_info = None
        if hasattr(self.screen_capture, 'get_scroll_history'):
            hist = self.screen_capture.get_scroll_history()
            if hist:
                scroll_info = hist[-1]

        # Duplicates
        duplicates = self.duplicate_tracker.process_names(names_with_positions, scroll_info)
        if duplicates:
            region = self.get_current_region()
            self.overlay_window.update_markers(duplicates, region)
            self.status_label.setText(f"Found {len(duplicates)} duplicates")
        else:
            self.overlay_window.clear_markers()
            self.status_label.setText("No duplicates found")

        # Final stats
        self.status_label.setText("Scanning...")
        try:
            ok = self.screen_capture.capture_and_process()
        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            self.status_label.setText("Scan error")
            return
        stats = self.screen_capture.get_statistics()
        if ok:
            self.status_label.setText(
                f"Session: {stats['session_names']} names, "
                f"{stats['session_occurrences']} occurrences"
            )
        else:
            self.status_label.setText("No change or no text")

    def reset_session(self):
        """Reset in-memory session counts"""
        reply = QMessageBox.question(
            self, "Reset Session",
            "Clear current session data?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.screen_capture.reset_session()
            self.status_label.setText("Session reset")

    def clear_database(self):
        """Clear session and database"""
        reply = QMessageBox.question(
            self, "Clear Database",
            "Delete all stored data?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.database.clear_all()
            self.status_label.setText("Database cleared")

    def export_csv(self):
        """Export all seen names to CSV"""
        import csv
        from PyQt5.QtWidgets import QFileDialog
        import os
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            self.status_label.setText("Export cancelled")
            return
        path = os.path.join(folder, f"duplicates_{int(time.time())}.csv")
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['name','first_seen','count'])
            for row in self.database.get_all_seen_names():
                w.writerow(row)
        self.status_label.setText(f"Exported to {path}")

    def show_logs(self):
        """Open the current log file"""
        import subprocess, platform, os
        log = 'duplicate_highlighter.log'
        if not os.path.exists(log):
            self.status_label.setText("No log file found")
            return
        try:
            if platform.system()=="Windows":
                os.startfile(log)
            elif platform.system()=="Darwin":
                subprocess.run(['open', log], check=True)
            else:
                subprocess.run(['xdg-open', log], check=True)
            self.status_label.setText("Log opened")
        except Exception as e:
            logger.error(f"Failed to open log: {e}")

def main():
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
