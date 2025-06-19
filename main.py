#!/usr/bin/env python3
"""
Duplicate Name Highlighter Application
Main entry point for the application
"""

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from gui.main_window import MainWindow
from core.settings_manager import SettingsManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('duplicate_highlighter.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    try:
        # Create QApplication instance
        app = QApplication(sys.argv)
        app.setApplicationName("Duplicate Name Highlighter")
        app.setApplicationVersion("1.0")
        app.setQuitOnLastWindowClosed(False)  # Keep running even if main window is closed
        
        # Enable high DPI scaling
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # Initialize settings manager
        settings_manager = SettingsManager()
        
        # Create and show main window
        main_window = MainWindow(settings_manager)
        main_window.show()
        
        logger.info("Duplicate Name Highlighter application started successfully")
        
        # Start the application event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
