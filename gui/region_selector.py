"""
Screen region selection widget for defining the monitoring area
"""

import logging
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QRect
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QCursor

logger = logging.getLogger(__name__)

class RegionSelector(QWidget):
    """Widget for selecting screen region by dragging"""
    
    region_selected = pyqtSignal(tuple)  # Emits (x, y, width, height) or None if cancelled
    
    def __init__(self):
        super().__init__()
        self.selection_active = False
        self.start_pos = None
        self.end_pos = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the selector UI"""
        # Make window frameless and transparent
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.3)
        
        # Set cursor
        self.setCursor(QCursor(Qt.CrossCursor))
    
    def start_selection(self):
        """Start the region selection process"""
        # Get screen geometry
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        
        # Make window cover entire screen
        self.setGeometry(screen_geometry)
        self.show()
        self.raise_()
        self.activateWindow()
        
        self.selection_active = True
        self.start_pos = None
        self.end_pos = None
        
        logger.info("Region selection started")
    
    def mousePressEvent(self, event):
        """Handle mouse press event"""
        if event.button() == Qt.LeftButton and self.selection_active:
            self.start_pos = event.pos()
            self.end_pos = event.pos()
            self.update()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move event"""
        if self.selection_active and self.start_pos:
            self.end_pos = event.pos()
            self.update()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release event"""
        if event.button() == Qt.LeftButton and self.selection_active and self.start_pos:
            self.end_pos = event.pos()
            self.finish_selection()
    
    def keyPressEvent(self, event):
        """Handle key press event"""
        if event.key() == Qt.Key_Escape:
            self.cancel_selection()
        super().keyPressEvent(event)
    
    def paintEvent(self, event):
        """Paint the selection rectangle"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill entire screen with semi-transparent overlay
        overlay_color = QColor(0, 0, 0, 100)
        painter.fillRect(self.rect(), overlay_color)
        
        # Draw selection rectangle if we have start and end positions
        if self.start_pos and self.end_pos:
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # Clear the selected area (make it transparent)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(selection_rect, Qt.transparent)
            
            # Draw selection border
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor(0, 122, 204), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(selection_rect)
            
            # Draw corner handles
            handle_size = 8
            handle_color = QColor(0, 122, 204)
            painter.setBrush(QBrush(handle_color))
            painter.setPen(Qt.NoPen)
            
            # Top-left handle
            painter.drawRect(selection_rect.left() - handle_size//2, 
                           selection_rect.top() - handle_size//2, 
                           handle_size, handle_size)
            
            # Top-right handle
            painter.drawRect(selection_rect.right() - handle_size//2, 
                           selection_rect.top() - handle_size//2, 
                           handle_size, handle_size)
            
            # Bottom-left handle
            painter.drawRect(selection_rect.left() - handle_size//2, 
                           selection_rect.bottom() - handle_size//2, 
                           handle_size, handle_size)
            
            # Bottom-right handle
            painter.drawRect(selection_rect.right() - handle_size//2, 
                           selection_rect.bottom() - handle_size//2, 
                           handle_size, handle_size)
    
    def finish_selection(self):
        """Complete the selection process"""
        if self.start_pos and self.end_pos:
            selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # Ensure minimum size
            if selection_rect.width() < 10 or selection_rect.height() < 10:
                logger.warning("Selection too small, cancelling")
                self.cancel_selection()
                return
            
            # Convert to screen coordinates
            screen_rect = (selection_rect.x(), selection_rect.y(), 
                          selection_rect.width(), selection_rect.height())
            
            self.hide()
            self.selection_active = False
            self.region_selected.emit(screen_rect)
            
            logger.info(f"Region selected: {screen_rect}")
        else:
            self.cancel_selection()
    
    def cancel_selection(self):
        """Cancel the selection process"""
        self.hide()
        self.selection_active = False
        self.start_pos = None
        self.end_pos = None
        self.region_selected.emit(None)
        logger.info("Region selection cancelled")
