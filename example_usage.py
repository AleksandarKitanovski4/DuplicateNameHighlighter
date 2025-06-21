"""
Example usage of the Duplicate Name Highlighter system
"""

import sys
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QSpinBox, QCheckBox
from PyQt5.QtCore import QTimer

from core.screen_capture import ScreenCapture

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Duplicate Name Highlighter")

        # Default capture region
        self.capture = ScreenCapture(region=(100, 100, 800, 600))

        # UI elements
        self.auto_scan_cb = QCheckBox("Enable Auto-Scan")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(3)
        self.interval_label = QLabel("Scan Interval (s):")
        self.stats_label = QLabel("Session: 0 names, 0 occurrences")

        # Buttons
        self.btn_select_region = QPushButton("Select Region")
        self.btn_reset = QPushButton("Reset Session")
        self.btn_clear_db = QPushButton("Clear Database")

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.auto_scan_cb)
        layout.addWidget(self.interval_label)
        layout.addWidget(self.interval_spin)
        layout.addWidget(self.btn_select_region)
        layout.addWidget(self.btn_reset)
        layout.addWidget(self.btn_clear_db)
        layout.addWidget(self.stats_label)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)

        # Timer for auto scanning
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_scan)
        
        # Connect signals
        self.auto_scan_cb.stateChanged.connect(self.toggle_auto_scan)
        self.interval_spin.valueChanged.connect(self.update_interval)
        self.btn_select_region.clicked.connect(self.select_region)
        self.btn_reset.clicked.connect(self.reset_session)
        self.btn_clear_db.clicked.connect(self.clear_database)

        # Initialize
        self.update_interval(self.interval_spin.value())

    def toggle_auto_scan(self, checked):
        if checked:
            self.timer.start()
            logger.info("Auto-scan enabled")
        else:
            self.timer.stop()
            logger.info("Auto-scan disabled")

    def update_interval(self, seconds):
        self.timer.setInterval(seconds * 1000)
        logger.info(f"Scan interval set to {seconds}s")

    def select_region(self):
        # Hide main window, let user draw region (assumes method exists)
        self.hide()
        region = self.capture.region_selector()  # implement region_selector in ScreenCapture
        if region:
            self.capture.set_region(region)
            logger.info(f"Region set to {region}")
        self.show()

    def on_scan(self):
        processed = self.capture.capture_and_process()
        if processed:
            stats = self.capture.get_statistics()
            self.stats_label.setText(
                f"Session: {stats['session_names']} names, {stats['session_occurrences']} occurrences"
            )

    def reset_session(self):
        self.capture.reset_session()
        self.stats_label.setText("Session: 0 names, 0 occurrences")

    def clear_database(self):
        self.capture.clear_all()
        self.stats_label.setText("Session: 0 names, 0 occurrences")

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s"
    )
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    logger.info("Duplicate Name Highlighter started")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
