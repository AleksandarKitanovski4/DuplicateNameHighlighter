"""
Screen capture, change detection, OCR, and duplicate management
"""

import logging
from typing import Optional, Tuple, List, Dict
import imagehash
import pyautogui
from PIL import Image
from core.ocr_processor import OCRProcessor
from tracker.duplicate_tracker import DuplicateTracker
from core.scroll_tracker import ScrollTracker
from gui.overlay import Overlay
from utils.database import NameDatabase

logger = logging.getLogger(__name__)

class ScreenCapture:
    """Handles periodic region capture, change detection, OCR, and duplicate highlighting."""
    
    def __init__(
        self,
        region: Optional[Tuple[int, int, int, int]] = None,
        hash_threshold: int = 5,
        scroll_threshold: int = 10
    ):
        self.region = region
        self.last_hash: Optional[imagehash.ImageHash] = None
        self.hash_threshold = hash_threshold
        
        self.ocr = OCRProcessor()
        self.db = NameDatabase()
        self.overlay = Overlay()
        self.tracker = DuplicateTracker(self.db, self.overlay)
        self.scroll_tracker = ScrollTracker(scroll_threshold=scroll_threshold)
        
        # Disable PyAutoGUI failsafe (corner mouse throw)
        pyautogui.FAILSAFE = False
        
        logger.info("ScreenCapture initialized")
    
    def set_region(self, region: Tuple[int, int, int, int]) -> None:
        """Define the screen region to monitor (x, y, width, height)."""
        self.region = region
        self.last_hash = None
        logger.info(f"Capture region set to {region}")
    
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
        
        # Detect scroll events
        scroll_info = self.scroll_tracker.detect_scroll(img)
        
        if not self._has_changed(img):
            # Even if image hasn't changed, check for scroll events
            if scroll_info:
                logger.debug(f"Scroll detected during unchanged image: {scroll_info['direction']}")
                # Update marker positions for scroll
                self._update_markers_for_scroll(scroll_info)
            else:
                logger.debug("Region unchanged; skipping OCR")
            return False
        
        texts = self.ocr.extract_text_with_positions(img)
        if texts:
            logger.info(f"OCR found {len(texts)} entries")
            
            # Track OCR results for scroll detection
            adjusted_texts, ocr_scroll_info = self.scroll_tracker.track_ocr_results(texts)
            
            # Use OCR-based scroll detection if available
            if ocr_scroll_info and not scroll_info:
                scroll_info = ocr_scroll_info
            
            # Process texts and update markers
            self.tracker.process(adjusted_texts)
            
            # Update marker positions if scroll detected
            if scroll_info:
                self._update_markers_for_scroll(scroll_info)
            
            return True
        else:
            logger.debug("OCR returned no text")
            self.overlay.clear_markers()
            return False
    
    def _update_markers_for_scroll(self, scroll_info: Dict) -> None:
        """Update overlay markers for scroll events"""
        try:
            # Get current markers from overlay
            current_markers = self.overlay.widget.markers if hasattr(self.overlay, 'widget') else []
            
            # Convert to dictionary format for adjustment
            marker_dicts = []
            for x, y, w, h in current_markers:
                marker_dicts.append({'x': x, 'y': y, 'width': w, 'height': h})
            
            # Adjust marker positions
            adjusted_markers = self.scroll_tracker.adjust_marker_positions(marker_dicts, scroll_info)
            
            # Convert back to tuple format and update overlay
            adjusted_tuples = [(m['x'], m['y'], m['width'], m['height']) for m in adjusted_markers]
            self.overlay.update_markers(adjusted_tuples)
            
            logger.debug(f"Updated {len(adjusted_markers)} markers for scroll")
            
        except Exception as e:
            logger.error(f"Error updating markers for scroll: {str(e)}")
    
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
        self.scroll_tracker.reset()
        self.last_hash = None
        logger.info("Session reset")
    
    def clear_all(self) -> None:
        """Clear both session and persistent database, and hide markers."""
        self.tracker.clear_all()
        self.scroll_tracker.reset()
        self.last_hash = None
        logger.info("All data cleared")
    
    def get_statistics(self) -> Dict:
        """Retrieve combined session+database statistics."""
        return self.tracker.get_statistics()
    
    def get_scroll_history(self) -> List[Dict]:
        """Get scroll detection history"""
        return self.scroll_tracker.get_scroll_history()
    
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
