"""
Screen capture, change detection, OCR, and duplicate management
"""

import logging
<<<<<<< HEAD
import time
import numpy as np
from PIL import Image, ImageGrab, ImageChops
import imagehash
import pyautogui
import cv2
=======
from typing import Optional, Tuple, List, Dict
import imagehash
import pyautogui
from PIL import Image
from core.ocr_processor import OCRProcessor
from core.duplicate_tracker import DuplicateTracker
from gui.overlay import Overlay
from utils.database import NameDatabase
>>>>>>> ef98d5a (Finalize repo structure)

logger = logging.getLogger(__name__)

class ScreenCapture:
    """Handles periodic region capture, change detection, OCR, and duplicate highlighting."""
    
    def __init__(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        hash_threshold: int = 5
    ):
        self.region = region
        self.last_hash: Optional[imagehash.ImageHash] = None
        self.hash_threshold = hash_threshold
        
        self.ocr = OCRProcessor()
        self.db = NameDatabase()
        self.overlay = Overlay()
        self.tracker = DuplicateTracker(self.db, self.overlay)
        
        # Disable PyAutoGUI failsafe (corner mouse throw)
        pyautogui.FAILSAFE = False
        
        logger.info("ScreenCapture initialized")
    
    def set_region(self, region: Tuple[int, int, int, int]) -> None:
        """Define the screen region to monitor (x, y, width, height)."""
        self.region = region
        self.last_hash = None
<<<<<<< HEAD
        self.hash_threshold = 5  # Hamming distance threshold for change detection
        self.scroll_threshold = 10  # Threshold for scroll detection
        self.last_scroll_direction = None
        self.scroll_history = []  # Track recent scroll events
        
        # Configure pyautogui
        pyautogui.FAILSAFE = False  # Disable failsafe for automated use
        
        logger.info("Screen capture initialized")
=======
        logger.info(f"Capture region set to {region}")
>>>>>>> ef98d5a (Finalize repo structure)
    
    def capture_and_process(self) -> bool:
        """
        Capture the region, skip OCR if unchanged, otherwise run OCR and duplicate detection.
        Returns True if OCR+processing ran, False if skipped or failed.
        """
        if not self.region:
            logger.error("No capture region defined")
            return False
        
        img = self._grab_region(self.region)
        if img is None:
            return False
        
<<<<<<< HEAD
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
=======
        if not self._has_changed(img):
            logger.debug("Region unchanged; skipping OCR")
            return False
        
        texts = self.ocr.extract_text_with_positions(img)
        if texts:
            logger.info(f"OCR found {len(texts)} entries")
            self.tracker.process(texts)
>>>>>>> ef98d5a (Finalize repo structure)
            return True
        else:
            logger.debug("OCR returned no text")
            self.overlay.clear_markers()
            return False
    
    def _grab_region(self, region: Tuple[int, int, int, int]) -> Optional[Image.Image]:
        """Capture screenshot of the given region via PyAutoGUI."""
        x, y, w, h = region
        if w <= 0 or h <= 0:
            logger.error(f"Invalid region dimensions: {w}×{h}")
            return None
        try:
            img = pyautogui.screenshot(region=region)
            logger.debug(f"Captured region {region}")
            return img
        except Exception as e:
            logger.error(f"Screenshot failed: {e}", exc_info=True)
            return None
    
    def _has_changed(self, img: Image.Image) -> bool:
        """
        Compare pHash of current image to last. If no previous hash, treat as changed.
        Returns True if change exceeds threshold.
        """
        try:
            current = imagehash.phash(img)
            if self.last_hash is None:
                self.last_hash = current
                return True
            diff = current - self.last_hash
            self.last_hash = current
            changed = diff > self.hash_threshold
            logger.debug(f"Hash diff={diff}; threshold={self.hash_threshold}; changed={changed}")
            return changed
        except Exception as e:
            logger.error(f"Change detection error: {e}", exc_info=True)
            # Fallback: always process if unsure
            self.last_hash = None
            return True
    
    def reset_session(self) -> None:
        """Clear in-memory tracking and overlay markers (database persists)."""
        self.tracker.reset_session()
        self.last_hash = None
        logger.info("Session reset")
    
    def clear_all(self) -> None:
        """Clear both session and persistent database, and hide markers."""
        self.tracker.clear_all()
        self.last_hash = None
        logger.info("All data cleared")
    
    def get_statistics(self) -> Dict:
        """Retrieve combined session+database statistics."""
        return self.tracker.get_statistics()
    
    def save_screenshot(self, img: Image.Image, path: str) -> None:
        """Save the last captured image for debugging."""
        try:
            img.save(path)
            logger.info(f"Screenshot saved to {path}")
        except Exception as e:
            logger.error(f"Save screenshot failed: {e}")
    
    def get_screen_info(self) -> Dict:
        """Return screen size and current region."""
        screen = pyautogui.size()
        return {
            'screen_width': screen.width,
            'screen_height': screen.height,
            'region': self.region
        }
