#!/usr/bin/env python3
"""
Duplicate Name Highlighter Application
Main entry point for the application
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer
from gui.main_window import MainWindow
from core.settings_manager import SettingsManager

# Configure logging with rotating file handler
def setup_logging():
    """Setup enhanced logging with rotation and JSON format option"""
    log_file = 'duplicate_highlighter.log'
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create rotating file handler (5MB max, keep 3 backup files)
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

# Setup logging
logger = setup_logging()

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
