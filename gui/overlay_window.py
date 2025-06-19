"""
Transparent overlay window for displaying duplicate name markers
"""

import logging
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont

logger = logging.getLogger(__name__)

class OverlayWindow(QWidget):
    """Transparent overlay window for displaying markers"""
    
    def __init__(self):
        super().__init__()
        self.markers = []  # List of marker data: (x, y, width, height, name, color)
        self.setup_ui()
        
        # Timer for marker animations (optional)
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_frame = 0
    
    def setup_ui(self):
        """Setup the overlay window"""
        # Make window transparent and always on top
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | 
                           Qt.Tool | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Set window to cover entire screen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.setGeometry(screen_geometry)
        
        logger.info("Overlay window initialized")
    
    def update_markers(self, duplicates, region):
        """Update markers for duplicate names
        
        Args:
            duplicates: List of duplicate entries with name, positions, and occurrence count
            region: Tuple of (x, y, width, height) of the monitored region
        """
        self.markers = []
        
        if not duplicates or not region:
            self.hide()
            return
        
        region_x, region_y, region_width, region_height = region
        
        # Create markers for each duplicate
        for duplicate in duplicates:
            name = duplicate['name']
            positions = duplicate['positions']
            count = duplicate['count']
            
            # Determine marker color based on occurrence count
            if count == 2:
                color = QColor(255, 165, 0, 180)  # Orange for first duplicate
            elif count == 3:
                color = QColor(255, 69, 0, 180)   # Red-orange for second duplicate
            else:
                color = QColor(255, 0, 0, 180)    # Red for multiple duplicates
            
            # Add marker for each position of this duplicate name
            for pos in positions:
                # Convert relative position to absolute screen coordinates
                marker_x = region_x + pos['x']
                marker_y = region_y + pos['y']
                marker_width = pos['width']
                marker_height = pos['height']
                
                self.markers.append({
                    'x': marker_x,
                    'y': marker_y,
                    'width': marker_width,
                    'height': marker_height,
                    'name': name,
                    'color': color,
                    'count': count
                })
        
        if self.markers:
            self.show()
            self.update()
            # Start subtle animation
            if not self.animation_timer.isActive():
                self.animation_timer.start(500)  # Update every 500ms
            logger.info(f"Updated overlay with {len(self.markers)} markers")
        else:
            self.hide()
    
    def clear_markers(self):
        """Clear all markers"""
        self.markers = []
        self.animation_timer.stop()
        self.hide()
        logger.info("Overlay markers cleared")
    
    def paintEvent(self, event):
        """Paint the markers on the overlay"""
        if not self.markers:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for marker in self.markers:
            self.draw_marker(painter, marker)
    
    def draw_marker(self, painter, marker):
        """Draw a single marker
        
        Args:
            painter: QPainter instance
            marker: Dictionary containing marker information
        """
        x = marker['x']
        y = marker['y']
        width = marker['width']
        height = marker['height']
        color = marker['color']
        name = marker['name']
        count = marker['count']
        
        # Apply animation effect (subtle pulsing)
        alpha_factor = 0.8 + 0.2 * (0.5 + 0.5 * 
                      (1 if self.animation_frame % 2 == 0 else -1))
        animated_color = QColor(color)
        animated_color.setAlpha(int(color.alpha() * alpha_factor))
        
        # Draw border rectangle
        border_pen = QPen(animated_color, 2, Qt.SolidLine)
        painter.setPen(border_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(x, y, width, height)
        
        # Draw corner indicator (small filled circle)
        indicator_size = 8
        indicator_color = QColor(animated_color)
        indicator_color.setAlpha(255)  # Make indicator fully opaque
        
        painter.setBrush(QBrush(indicator_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(x - indicator_size//2, y - indicator_size//2, 
                          indicator_size, indicator_size)
        
        # Draw occurrence count badge
        if count > 2:
            badge_size = 16
            badge_x = x + width - badge_size
            badge_y = y - badge_size//2
            
            # Badge background
            badge_bg = QColor(255, 255, 255, 200)
            painter.setBrush(QBrush(badge_bg))
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.drawEllipse(badge_x, badge_y, badge_size, badge_size)
            
            # Badge text
            font = QFont()
            font.setPointSize(8)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor(0, 0, 0)))
            
            text_rect = painter.fontMetrics().boundingRect(str(count))
            text_x = badge_x + (badge_size - text_rect.width()) // 2
            text_y = badge_y + (badge_size + text_rect.height()) // 2 - 2
            
            painter.drawText(text_x, text_y, str(count))
    
    def update_animation(self):
        """Update animation frame"""
        self.animation_frame += 1
        if self.markers:
            self.update()
        else:
            self.animation_timer.stop()
    
    def showEvent(self, event):
        """Handle show event"""
        super().showEvent(event)
        # Ensure window stays on top and transparent to input
        self.raise_()
        self.activateWindow()
    
    def resizeEvent(self, event):
        """Handle resize event"""
        super().resizeEvent(event)
        # Ensure overlay covers entire screen when resized
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        if self.geometry() != screen_geometry:
            self.setGeometry(screen_geometry)
