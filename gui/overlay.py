"""
Transparent overlay window for displaying duplicate name markers
"""

import logging
from typing import List, Tuple, Dict
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush

logger = logging.getLogger(__name__)

class Overlay:
    """Transparent overlay for displaying duplicate name markers"""
    
    def __init__(self):
        self.widget = OverlayWidget()
        self.widget.show()  # Keep the overlay window ready
        self.clear_markers()
        logger.info("Overlay initialized")
        
    def update_markers(self, boxes: List[Tuple[int, int, int, int]]):
        """Update markers with new duplicate boxes"""
        self.widget.markers = boxes
        self.widget.update()
        if boxes:
            self.widget.show()
            logger.info(f"Overlay: {len(boxes)} markers shown")
        else:
            self.widget.hide()
            logger.info("Overlay: no markers to show, hiding overlay")
    
    def update_markers_with_offset(self, boxes: List[Tuple[int, int, int, int]], offset_x: int = 0, offset_y: int = 0):
        """Update markers with position offset for scroll adjustment
        
        Args:
            boxes: List of marker boxes (x, y, width, height)
            offset_x: Horizontal offset to apply
            offset_y: Vertical offset to apply
        """
        adjusted_boxes = []
        for x, y, w, h in boxes:
            adjusted_boxes.append((x + offset_x, y + offset_y, w, h))
        
        self.update_markers(adjusted_boxes)
        logger.debug(f"Updated {len(adjusted_boxes)} markers with offset ({offset_x}, {offset_y})")
    
    def adjust_markers_for_scroll(self, scroll_info: Dict):
        """Adjust marker positions based on scroll information
        
        Args:
            scroll_info: Dictionary with 'direction' and 'magnitude' keys
        """
        if not scroll_info or not self.widget.markers:
            return
        
        direction = scroll_info['direction']
        magnitude = scroll_info['magnitude']
        
        adjusted_markers = []
        for x, y, w, h in self.widget.markers:
            if direction == 'down':
                # Content scrolled down, markers move up
                new_y = y - magnitude
            elif direction == 'up':
                # Content scrolled up, markers move down
                new_y = y + magnitude
            else:
                new_y = y
            
            # Check if marker is still within visible area (with tolerance)
            if new_y + h > -50:  # Allow slight overflow
                adjusted_markers.append((x, new_y, w, h))
        
        self.widget.markers = adjusted_markers
        self.widget.update()
        logger.debug(f"Adjusted {len(adjusted_markers)} markers for {direction} scroll")
    
    def clear_markers(self):
        """Clear all markers"""
        self.widget.markers = []
        self.widget.hide()
        logger.info("Overlay markers cleared")
    
    def get_marker_positions(self) -> List[Tuple[int, int, int, int]]:
        """Get current marker positions"""
        return self.widget.markers.copy()


class OverlayWidget(QWidget):
    """Transparent widget for drawing markers"""
    
    def __init__(self):
        super().__init__()
        self.markers: List[Tuple[int, int, int, int]] = []
        self._setup_window()
        
    def _setup_window(self):
        """Configure window flags and attributes"""
        flags = (
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setWindowFlags(flags)
        
        # Transparent background
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Click-through: mouse events pass through to underlying windows
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # Do not steal focus when shown
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        # Cover the entire virtual desktop
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.geometry()
            self.setGeometry(screen_geom)
        logger.info("OverlayWidget window configured")
    
    def paintEvent(self, event):
        """Draw all markers"""
        if not self.markers:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for x, y, w, h in self.markers:
            self._draw_marker(painter, QRect(x, y, w, h))
    
    def _draw_marker(self, painter: QPainter, rect: QRect):
        """Draw a semi-transparent rectangle and a corner dot"""
        # Semi-transparent red border
        pen = QPen(QColor(255, 0, 0, 180), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)
        
        # Solid red corner dot
        dot_size = 8
        brush = QBrush(QColor(255, 0, 0, 255))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(
            rect.topLeft().x() - dot_size//2,
            rect.topLeft().y() - dot_size//2,
            dot_size,
            dot_size
        )
    
    def showEvent(self, event):
        """Ensure overlay stays on top without taking focus"""
        super().showEvent(event)
        self.raise_()
    
    def resizeEvent(self, event):
        """Keep overlay covering the full screen on resolution changes"""
        super().resizeEvent(event)
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            if self.geometry() != geom:
                self.setGeometry(geom)
                logger.info("OverlayWidget resized to full screen")
