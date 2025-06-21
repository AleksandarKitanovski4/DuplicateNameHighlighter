"""
Screen capture, change detection, OCR, and duplicate management
"""

import logging
from typing import Optional, Tuple, List, Dict
import imagehash
import pyautogui
from PIL import Image
from core.ocr_processor import OCRProcessor
from core.duplicate_tracker import DuplicateTracker
from gui.overlay import Overlay
from utils.database import NameDatabase

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
        
        if not self._has_changed(img):
            logger.debug("Region unchanged; skipping OCR")
            return False
        
        texts = self.ocr.extract_text_with_positions(img)
        if texts:
            logger.info(f"OCR found {len(texts)} entries")
            self.tracker.process(texts)
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
