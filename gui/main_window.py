# gui/main_window.py

"""
Main GUI window for the Duplicate Name Highlighter application
"""

import sys
import logging
import time

from datetime import datetime
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
    scan_completed   = pyqtSignal(list)
    scroll_detected  = pyqtSignal(dict)
    error_occurred   = pyqtSignal(str)

    def __init__(self, screen_capture: ScreenCapture, ocr_processor: OCRProcessor, region: tuple):
        super().__init__()
        self.screen_capture = screen_capture
        self.ocr_processor  = ocr_processor
        self.region         = region
        self.running        = False

    def run(self):
        try:
            self.running = True

            # 1) grab screenshot
            img = self.screen_capture.capture_region(self.region)
            if img is None:
                self.error_occurred.emit("Failed to capture screenshot")
                return

            # 2) detect scroll first
            scroll = self.screen_capture.detect_scroll(img)
            if scroll and scroll.get("confidence", 0) > 0.8:
                self.scroll_detected.emit(scroll)
                logger.info(f"Scroll: {scroll['direction']}")

            # 3) skip if unchanged
            if not self.screen_capture.has_changed(img):
                return

            # 4) OCR
            try:
                names = self.ocr_processor.extract_text_with_positions(img)
            except Exception as e:
                self.error_occurred.emit(f"OCR error: {e}")
                return

            self.scan_completed.emit(names)

        except Exception as e:
            logger.error(f"ScanWorker error: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
        finally:
            self.running = False

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class MainWindow(QMainWindow):
    """Main settings window to control scanning and display status"""

    def __init__(self):
        super().__init__()
        self.current_session_id = datetime.utcnow().isoformat()
        self.setWindowTitle("Duplicate Name Highlighter")
        # let it expand vertically so nothing is clipped
        self.resize(300, 550)

        # ─── Core components ────────────────────────────────────
        self.screen_capture    = ScreenCapture()
        self.database          = Database("duplicate_names.db")
        self.ocr_processor     = OCRProcessor()
        self.overlay_window    = OverlayWindow()
        self.duplicate_tracker = DuplicateTracker(self.database,
                                                  overlay=self.overlay_window)

        # ─── Region selector ───────────────────────────────────
        self.region_selector = RegionSelector()
        self.region_selector.region_selected.connect(self.on_region_selected)

        # ─── Build UI ──────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)

        # — Region Picker —
        self.region_btn = QPushButton("Select Region")
        layout.addWidget(self.region_btn)

        # — Auto-scan checkbox —
        self.auto_cb = QCheckBox("Enable Auto-Scan")
        self.auto_cb.setEnabled(False)
        layout.addWidget(self.auto_cb)

        # — Interval —
        hl = QHBoxLayout()
        hl.addWidget(QLabel("Interval (s):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(3)
        hl.addWidget(self.interval_spin)
        layout.addLayout(hl)

        # — Manual Scan Group —
        scan_group  = QGroupBox("Scan Options")
        scan_group.setFlat(True)
        scan_layout = QHBoxLayout(scan_group)
        self.manual_scan_btn = QPushButton("Scan Now")
        scan_layout.addWidget(self.manual_scan_btn)
        layout.addWidget(scan_group)

        # — Session Management —
        session_group  = QGroupBox("Session Management")
        session_layout = QVBoxLayout(session_group)
        self.reset_session_btn    = QPushButton("Reset Session")
        self.clear_database_btn   = QPushButton("Clear Database")
        self.export_csv_btn       = QPushButton("Export CSV")
        self.show_logs_btn        = QPushButton("Show Logs")
        for btn in (self.reset_session_btn,
                    self.clear_database_btn,
                    self.export_csv_btn,
                    self.show_logs_btn):
            session_layout.addWidget(btn)
        layout.addWidget(session_group)

        # — Status Label —
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #007ACC;")
        layout.addWidget(self.status_label)

        # ─── Timer & Connections ────────────────────────────────
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.scan)

        self.region_btn.clicked.connect(self.select_region)
        self.auto_cb.toggled.connect(self.on_auto_toggled)
        self.interval_spin.valueChanged.connect(self.update_interval)
        self.manual_scan_btn.clicked.connect(self.scan)
        self.reset_session_btn.clicked.connect(self.reset_session)
        self.clear_database_btn.clicked.connect(self.clear_all)
        self.export_csv_btn.clicked.connect(self.export_csv)
        self.show_logs_btn.clicked.connect(self.show_logs)

    def select_region(self):
        """Start region selection overlay"""
        self.hide()
        self.region_selector.start_selection()
        self.show()

    def on_region_selected(self, region: tuple):
        """Called when user finishes selecting a region"""
        if region:
            self.screen_capture.set_region(region)
            self.status_label.setText(f"Region: {region}")
            self.auto_cb.setEnabled(True)
            self.manual_scan_btn.setEnabled(True)
        else:
            self.status_label.setText("No region selected")

    def on_auto_toggled(self, checked: bool):
        """Enable or disable periodic scanning"""
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

    def update_interval(self, value: int):
        """Adjust scan interval"""
        self.timer.setInterval(value * 1000)
        if self.auto_cb.isChecked():
            self.timer.start()

    def scan(self):
        """Kick off one OCR pass in background"""
        # require region
        if not self.screen_capture.region:
            QMessageBox.warning(self, "No Region Selected",
                                "Please select a capture region first.")
            return

        # don't overlap
        if hasattr(self, 'scan_worker') and self.scan_worker.isRunning():
            return

        self.status_label.setText("Scanning…")
        self.manual_scan_btn.setEnabled(False)

        # start worker
        self.scan_worker = ScanWorker(
            self.screen_capture,
            self.ocr_processor,
            self.screen_capture.region
        )
        self.scan_worker.scan_completed.connect(self.on_scan_completed)
        self.scan_worker.scroll_detected.connect(self.on_scroll_detected)
        self.scan_worker.error_occurred.connect(self.on_scan_error)
        self.scan_worker.finished.connect(lambda: self.manual_scan_btn.setEnabled(True))
        self.scan_worker.start()

    def on_scroll_detected(self, info: dict):
        """Move markers when the page scrolls"""
        markers = self.overlay_window.get_current_markers()
        if markers:
            adjusted = self.screen_capture.adjust_marker_positions(markers, info)
            self.overlay_window.update_markers_from_adjusted(adjusted)
        self.status_label.setText(f"Scroll: {info['direction']}")

    def on_scan_error(self, msg: str):
        """Show OCR or capture error"""
        self.status_label.setText(f"Error: {msg}")
        self.manual_scan_btn.setEnabled(True)

    def on_scan_completed(self, names_with_positions: list):
        """Process OCR results & highlight duplicates"""
        # 1) detect scroll info
        scroll_info = None
        hist = getattr(self.screen_capture, "get_scroll_history", lambda: [])()
        if hist:
            scroll_info = hist[-1]

        # — persist this scan’s raw OCR texts into SQLite —
        texts = [item['text'] for item in names_with_positions]
        for txt in texts:
            self.database.add_name_occurrence(txt, count=1,
                                              session_id=self.current_session_id)

        # 2) find duplicates
        duplicates = self.duplicate_tracker.process_names(names_with_positions, scroll_info)

        # 3) update overlay
        if duplicates:
            region = self.screen_capture.region
            self.overlay_window.update_markers(duplicates, region)
            self.status_label.setText(f"Found {len(duplicates)} duplicates")
        else:
            self.overlay_window.clear_markers()
            self.status_label.setText("No duplicates found")

        # 4) show final session stats
        ok = False
        try:
            ok = self.screen_capture.capture_and_process()
        except Exception as e:
            logger.error(f"Final capture error: {e}", exc_info=True)

        stats = getattr(self.screen_capture, "get_statistics", lambda: {})()
        if ok and stats:
            self.status_label.setText(
                f"Session: {stats.get('session_names',0)} names, "
                f"{stats.get('session_occurrences',0)} occurrences"
            )

        self.manual_scan_btn.setEnabled(True)

    def reset_session(self):
        """Clear the in-memory duplicate-tracker state"""
        if QMessageBox.question(self, "Reset Session",
                                "Clear current session data?",
                                QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.screen_capture.reset_session()
            self.status_label.setText("Session reset")

    def clear_all(self):
        """Wipe both session & database"""
        if QMessageBox.question(self, "Clear Database",
                                "Delete all stored data?",
                                QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.database.clear_all()
            self.status_label.setText("Database cleared")

    def export_csv(self):
        """Export seen names to a CSV file"""
        from PyQt5.QtWidgets import QFileDialog
        import csv, os
        folder = QFileDialog.getExistingDirectory(self, "Select Export Folder")
        if not folder:
            self.status_label.setText("Export cancelled")
            return
        path = os.path.join(folder, f"duplicates_{int(time.time())}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "first_seen", "count"])
            for row in self.database.get_all_seen_names():
                writer.writerow(row)
        self.status_label.setText(f"Exported CSV to {path}")

    def show_logs(self):
        """Open the current log file in the system editor"""
        import platform, subprocess, os
        log = "duplicate_highlighter.log"
        if not os.path.exists(log):
            self.status_label.setText("No log file found")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(log)
            elif platform.system() == "Darwin":
                subprocess.run(["open", log], check=True)
            else:
                subprocess.run(["xdg-open", log], check=True)
            self.status_label.setText("Log opened")
        except Exception as e:
            logger.error(f"Open log error: {e}")
            self.status_label.setText("Failed to open log")

    def closeEvent(self, event):
        """Minimize to tray or quit cleanly"""
        if hasattr(self, "tray_icon") and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

def main():
    logging.basicConfig(level=logging.INFO)
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
