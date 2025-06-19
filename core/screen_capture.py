"""
Screen capture and change detection functionality
"""

import logging
import time
from PIL import Image, ImageGrab, ImageChops
import imagehash
import pyautogui

logger = logging.getLogger(__name__)

class ScreenCapture:
    """Handles screen capture and change detection"""
    
    def __init__(self):
        self.last_screenshot = None
        self.last_hash = None
        self.hash_threshold = 5  # Hamming distance threshold for change detection
        
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
        """Detect if content has scrolled
        
        Args:
            current_image: PIL Image object
            
        Returns:
            Dictionary with scroll information or None
        """
        try:
            if current_image is None or self.last_screenshot is None:
                return None
            
            # Simple scroll detection using image correlation
            # This is a basic implementation - could be enhanced
            
            current_hash = imagehash.average_hash(current_image)
            last_hash = imagehash.average_hash(self.last_screenshot)
            
            # If images are very different, might be a scroll
            hash_diff = current_hash - last_hash
            
            if hash_diff > self.hash_threshold * 2:
                # Try to detect vertical scroll by comparing strips
                height = current_image.height
                strip_height = height // 4
                
                # Compare top strip of current with bottom strip of last
                current_top = current_image.crop((0, 0, current_image.width, strip_height))
                last_bottom = self.last_screenshot.crop((0, height - strip_height, 
                                                       self.last_screenshot.width, height))
                
                if current_top.size == last_bottom.size:
                    top_hash = imagehash.average_hash(current_top)
                    bottom_hash = imagehash.average_hash(last_bottom)
                    
                    if top_hash - bottom_hash < self.hash_threshold:
                        return {
                            'direction': 'down',
                            'detected': True,
                            'confidence': 0.8
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting scroll: {str(e)}")
            return None
    
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
