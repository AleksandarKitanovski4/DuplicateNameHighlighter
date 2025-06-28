"""
Scroll tracking and dynamic marker repositioning
"""

import logging
import time
import numpy as np
from typing import List, Dict, Optional, Tuple
from PIL import Image
import cv2

logger = logging.getLogger(__name__)

class ScrollTracker:
    """Detects scroll events and manages marker repositioning"""
    
    def __init__(self, scroll_threshold: int = 10, correlation_threshold: float = 0.7):
        self.scroll_threshold = scroll_threshold
        self.correlation_threshold = correlation_threshold
        self.last_image: Optional[Image.Image] = None
        self.last_ocr_results: List[Dict] = []
        self.scroll_history: List[Dict] = []
        self.last_scroll_direction: Optional[str] = None
        self.scroll_cooldown = 0.5  # Minimum time between scroll detections
        self.last_scroll_time = 0
        
        logger.info("ScrollTracker initialized")
    
    def detect_scroll(self, current_image: Image.Image) -> Optional[Dict]:
        """Detect if content has scrolled and determine direction
        
        Args:
            current_image: PIL Image object
            
        Returns:
            Dictionary with scroll information or None
        """
        try:
            if current_image is None or self.last_image is None:
                self.last_image = current_image
                return None
            
            # Check cooldown
            current_time = time.time()
            if current_time - self.last_scroll_time < self.scroll_cooldown:
                return None
            
            # Convert PIL images to numpy arrays for OpenCV processing
            current_np = np.array(current_image.convert('L'))
            last_np = np.array(self.last_image.convert('L'))
            
            # Ensure images are same size
            if current_np.shape != last_np.shape:
                self.last_image = current_image
                return None
            
            # Use template matching to detect scroll direction
            height, width = current_np.shape
            strip_height = max(height // 4, 50)  # Use 1/4 of height or minimum 50px
            
            # Create strips for comparison
            current_top = current_np[:strip_height, :]
            current_bottom = current_np[-strip_height:, :]
            last_top = last_np[:strip_height, :]
            last_bottom = last_np[-strip_height:, :]
            
            # Compare current top with last bottom (scroll down)
            if current_top.shape == last_bottom.shape:
                down_correlation = cv2.matchTemplate(current_top, last_bottom, cv2.TM_CCOEFF_NORMED)
                down_score = np.max(down_correlation)
            else:
                down_score = 0
            
            # Compare current bottom with last top (scroll up)
            if current_bottom.shape == last_top.shape:
                up_correlation = cv2.matchTemplate(current_bottom, last_top, cv2.TM_CCOEFF_NORMED)
                up_score = np.max(up_correlation)
            else:
                up_score = 0
            
            # Determine scroll direction and magnitude
            scroll_info = None
            
            if down_score > self.correlation_threshold and down_score > up_score:
                scroll_info = {
                    'direction': 'down',
                    'magnitude': int(down_score * strip_height),
                    'confidence': down_score,
                    'timestamp': current_time
                }
                logger.debug(f"Scroll down detected (confidence: {down_score:.3f})")
                
            elif up_score > self.correlation_threshold and up_score > down_score:
                scroll_info = {
                    'direction': 'up',
                    'magnitude': int(up_score * strip_height),
                    'confidence': up_score,
                    'timestamp': current_time
                }
                logger.debug(f"Scroll up detected (confidence: {up_score:.3f})")
            
            # Update scroll history
            if scroll_info:
                self.scroll_history.append(scroll_info)
                # Keep only last 10 scroll events
                if len(self.scroll_history) > 10:
                    self.scroll_history.pop(0)
                self.last_scroll_direction = scroll_info['direction']
                self.last_scroll_time = current_time
            
            self.last_image = current_image
            return scroll_info
            
        except Exception as e:
            logger.error(f"Error in scroll detection: {str(e)}")
            self.last_image = current_image
            return None
    
    def adjust_marker_positions(self, markers: List[Dict], scroll_info: Dict) -> List[Dict]:
        """Adjust marker positions based on scroll direction
        
        Args:
            markers: List of marker dictionaries with x, y, width, height
            scroll_info: Scroll detection result
            
        Returns:
            List of adjusted marker positions
        """
        if not scroll_info or not markers:
            return markers
        
        adjusted_markers = []
        direction = scroll_info['direction']
        magnitude = scroll_info['magnitude']
        
        for marker in markers:
            adjusted_marker = marker.copy()
            
            if direction == 'down':
                # Content scrolled down, markers move up
                adjusted_marker['y'] -= magnitude
            elif direction == 'up':
                # Content scrolled up, markers move down
                adjusted_marker['y'] += magnitude
            
            # Check if marker is still within visible area (with some tolerance)
            if adjusted_marker['y'] + adjusted_marker['height'] > -50:  # Allow slight overflow
                adjusted_markers.append(adjusted_marker)
        
        logger.debug(f"Adjusted {len(adjusted_markers)} markers for {direction} scroll")
        return adjusted_markers
    
    def track_ocr_results(self, ocr_results: List[Dict]) -> Tuple[List[Dict], Optional[Dict]]:
        """Track OCR results and detect scroll-based changes
        
        Args:
            ocr_results: Current OCR results with bounding boxes
            
        Returns:
            Tuple of (adjusted_results, scroll_info)
        """
        if not self.last_ocr_results:
            self.last_ocr_results = ocr_results
            return ocr_results, None
        
        # Simple heuristic: if most bounding boxes moved by similar amount, likely a scroll
        if len(ocr_results) > 0 and len(self.last_ocr_results) > 0:
            # Find matching names between current and last results
            current_names = {result['text']: result for result in ocr_results}
            last_names = {result['text']: result for result in self.last_ocr_results}
            
            common_names = set(current_names.keys()) & set(last_names.keys())
            
            if len(common_names) >= 2:  # Need at least 2 matching names to detect scroll
                y_diffs = []
                for name in common_names:
                    current_y = current_names[name]['bbox'][1]  # y coordinate
                    last_y = last_names[name]['bbox'][1]
                    y_diff = current_y - last_y
                    y_diffs.append(y_diff)
                
                # Check if y_diffs are consistent (indicating scroll)
                if len(y_diffs) >= 2:
                    mean_diff = np.mean(y_diffs)
                    std_diff = np.std(y_diffs)
                    
                    # If standard deviation is low, it's likely a scroll
                    if std_diff < 20:  # Threshold for consistent movement
                        if abs(mean_diff) > self.scroll_threshold:
                            scroll_info = {
                                'direction': 'down' if mean_diff > 0 else 'up',
                                'magnitude': abs(int(mean_diff)),
                                'confidence': 0.8,  # High confidence for OCR-based detection
                                'timestamp': time.time()
                            }
                            
                            # Adjust marker positions
                            adjusted_results = self.adjust_marker_positions(ocr_results, scroll_info)
                            self.last_ocr_results = ocr_results
                            return adjusted_results, scroll_info
        
        self.last_ocr_results = ocr_results
        return ocr_results, None
    
    def is_scroll_event(self, current_image: Image.Image) -> bool:
        """Check if current image change is likely a scroll event
        
        Args:
            current_image: PIL Image object
            
        Returns:
            Boolean indicating if change is likely a scroll
        """
        scroll_info = self.detect_scroll(current_image)
        return scroll_info is not None and scroll_info['confidence'] > 0.8
    
    def get_scroll_history(self) -> List[Dict]:
        """Get recent scroll history
        
        Returns:
            List of recent scroll events
        """
        return self.scroll_history.copy()
    
    def reset(self):
        """Reset scroll tracking state"""
        self.last_image = None
        self.last_ocr_results = []
        self.scroll_history = []
        self.last_scroll_direction = None
        self.last_scroll_time = 0
        logger.info("ScrollTracker reset") 