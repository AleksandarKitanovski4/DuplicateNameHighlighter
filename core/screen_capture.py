"""
Screen capture and change detection functionality
"""

import logging
import time
import numpy as np
from PIL import Image, ImageGrab, ImageChops
import imagehash
import pyautogui
import cv2

logger = logging.getLogger(__name__)

class ScreenCapture:
    """Handles screen capture and change detection"""
    
    def __init__(self):
        self.last_screenshot = None
        self.last_hash = None
        self.hash_threshold = 5  # Hamming distance threshold for change detection
        self.scroll_threshold = 10  # Threshold for scroll detection
        self.last_scroll_direction = None
        self.scroll_history = []  # Track recent scroll events
        
        # Configure pyautogui
        pyautogui.FAILSAFE = False  # Disable failsafe for automated use
        
        logger.info("Screen capture initialized")
    
    def capture_region(self, region):
        """Capture screenshot of specified region
        
        Args:
            region: Tuple of (x, y, width, height)
            
        Returns:
            PIL Image object or None if capture fails
        """
        try:
            if not region or len(region) != 4:
                logger.error("Invalid region specified for capture")
                return None
            
            x, y, width, height = region
            
            # Validate region bounds
            if width <= 0 or height <= 0:
                logger.error(f"Invalid region dimensions: {width}x{height}")
                return None
            
            # Capture using PyAutoGUI (which uses PIL internally)
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            
            if screenshot is None:
                logger.error("Failed to capture screenshot")
                return None
            
            # Store reference to last screenshot
            self.last_screenshot = screenshot.copy()
            
            logger.debug(f"Captured region {x},{y} {width}x{height}")
            return screenshot
            
        except Exception as e:
            logger.error(f"Error capturing region: {str(e)}", exc_info=True)
            return None
    
    def capture_full_screen(self):
        """Capture full screen screenshot
        
        Returns:
            PIL Image object or None if capture fails
        """
        try:
            screenshot = pyautogui.screenshot()
            logger.debug("Captured full screen")
            return screenshot
            
        except Exception as e:
            logger.error(f"Error capturing full screen: {str(e)}")
            return None
    
    def has_changed(self, current_image, threshold=None):
        """Check if current image differs from last image
        
        Args:
            current_image: PIL Image object to compare
            threshold: Optional threshold for change detection
            
        Returns:
            Boolean indicating if image has changed significantly
        """
        try:
            if current_image is None:
                return False
            
            if threshold is None:
                threshold = self.hash_threshold
            
            # Calculate hash for current image
            current_hash = imagehash.average_hash(current_image)
            
            # If we don't have a previous hash, consider it changed
            if self.last_hash is None:
                self.last_hash = current_hash
                return True
            
            # Calculate difference
            hash_diff = current_hash - self.last_hash
            
            # Update last hash
            self.last_hash = current_hash
            
            # Check if difference exceeds threshold
            has_changed = hash_diff > threshold
            
            if has_changed:
                logger.debug(f"Image changed (hash difference: {hash_diff})")
            else:
                logger.debug(f"No significant change (hash difference: {hash_diff})")
            
            return has_changed
            
        except Exception as e:
            logger.error(f"Error in change detection: {str(e)}")
            return True  # Assume changed if we can't determine
    
    def get_change_percentage(self, current_image):
        """Get percentage of change between current and last image
        
        Args:
            current_image: PIL Image object
            
        Returns:
            Float percentage (0.0 to 100.0)
        """
        try:
            if current_image is None or self.last_screenshot is None:
                return 100.0
            
            # Ensure images are same size
            if current_image.size != self.last_screenshot.size:
                return 100.0
            
            # Convert to same mode
            if current_image.mode != self.last_screenshot.mode:
                current_image = current_image.convert(self.last_screenshot.mode)
            
            # Calculate pixel differences
            diff = ImageChops.difference(current_image, self.last_screenshot)
            
            # Convert to grayscale and get histogram
            diff_gray = diff.convert('L')
            histogram = diff_gray.histogram()
            
            # Calculate percentage of changed pixels
            total_pixels = sum(histogram)
            changed_pixels = sum(histogram[1:])  # Exclude completely unchanged pixels
            
            if total_pixels == 0:
                return 0.0
            
            change_percentage = (changed_pixels / total_pixels) * 100.0
            return change_percentage
            
        except Exception as e:
            logger.error(f"Error calculating change percentage: {str(e)}")
            return 100.0  # Assume maximum change on error
    
    def detect_scroll(self, current_image):
        """Detect if content has scrolled and determine direction
        
        Args:
            current_image: PIL Image object
            
        Returns:
            Dictionary with scroll information or None
        """
        try:
            if current_image is None or self.last_screenshot is None:
                return None
            
            # Convert PIL images to numpy arrays for OpenCV processing
            current_np = np.array(current_image.convert('L'))
            last_np = np.array(self.last_screenshot.convert('L'))
            
            # Ensure images are same size
            if current_np.shape != last_np.shape:
                return None
            
            # Use template matching to detect scroll direction
            height, width = current_np.shape
            strip_height = height // 3
            
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
            correlation_threshold = 0.7
            
            if down_score > correlation_threshold and down_score > up_score:
                scroll_info = {
                    'direction': 'down',
                    'magnitude': int(down_score * strip_height),
                    'confidence': down_score,
                    'timestamp': time.time()
                }
                logger.debug(f"Scroll down detected (confidence: {down_score:.3f})")
                
            elif up_score > correlation_threshold and up_score > down_score:
                scroll_info = {
                    'direction': 'up',
                    'magnitude': int(up_score * strip_height),
                    'confidence': up_score,
                    'timestamp': time.time()
                }
                logger.debug(f"Scroll up detected (confidence: {up_score:.3f})")
            
            # Update scroll history
            if scroll_info:
                self.scroll_history.append(scroll_info)
                # Keep only last 10 scroll events
                if len(self.scroll_history) > 10:
                    self.scroll_history.pop(0)
                self.last_scroll_direction = scroll_info['direction']
            
            return scroll_info
            
        except Exception as e:
            logger.error(f"Error in scroll detection: {str(e)}")
            return None
    
    def adjust_marker_positions(self, markers, scroll_info):
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
            
            # Check if marker is still within visible area
            if adjusted_marker['y'] + adjusted_marker['height'] > 0:
                adjusted_markers.append(adjusted_marker)
        
        logger.debug(f"Adjusted {len(adjusted_markers)} markers for {direction} scroll")
        return adjusted_markers
    
    def is_scroll_event(self, current_image):
        """Check if current image change is likely a scroll event
        
        Args:
            current_image: PIL Image object
            
        Returns:
            Boolean indicating if change is likely a scroll
        """
        scroll_info = self.detect_scroll(current_image)
        return scroll_info is not None and scroll_info['confidence'] > 0.8
    
    def get_scroll_history(self):
        """Get recent scroll history
        
        Returns:
            List of recent scroll events
        """
        return self.scroll_history.copy()
    
    def save_screenshot(self, image, filename):
        """Save screenshot to file
        
        Args:
            image: PIL Image object
            filename: Output filename
        """
        try:
            if image is None:
                logger.error("No image to save")
                return False
            
            image.save(filename)
            logger.info(f"Screenshot saved to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving screenshot: {str(e)}")
            return False
    
    def get_screen_info(self):
        """Get screen information
        
        Returns:
            Dictionary with screen information
        """
        try:
            screen_size = pyautogui.size()
            return {
                'width': screen_size.width,
                'height': screen_size.height,
                'position': pyautogui.position()
            }
            
        except Exception as e:
            logger.error(f"Error getting screen info: {str(e)}")
            return {}
