# core/screen_capture.py

"""
Screen capture, change detection, OCR, scrolling, and duplicate management
"""

import logging
from typing import Optional, Tuple, List, Dict
import imagehash
import pyautogui
from PIL import Image
from core.ocr_processor import OCRProcessor
from tracker.duplicate_tracker import DuplicateTracker
from core.scroll_tracker import ScrollTracker
from gui.overlay_window import OverlayWindow
from tracker.database import Database

logger = logging.getLogger(__name__)

class ScreenCapture:
    """Handles periodic region capture, change detection, OCR, and duplicate highlighting."""

    def __init__(
            self,
            region: Optional[Tuple[int, int, int, int]] = None,
            hash_threshold: int = 5,
            scroll_threshold: int = 10
    ):
        self.region: Optional[Tuple[int,int,int,int]] = region
        self.last_hash: Optional[imagehash.ImageHash] = None
        self.hash_threshold = hash_threshold

        # Core helpers
        self.ocr = OCRProcessor()
        self.db = Database()                     # persistent SQLite DB
        self.overlay = OverlayWindow()           # overlay GUI
        self.tracker = DuplicateTracker(         # duplicate logic
            database=self.db,
            overlay=self.overlay
        )
        self.scroll_tracker = ScrollTracker(     # scroll detection
            scroll_threshold=scroll_threshold
        )

        # Disable PyAutoGUI failsafe
        pyautogui.FAILSAFE = False

        # Generate initial session ID
        from datetime import datetime
        self.current_session_id = datetime.utcnow().isoformat()

        logger.info("ScreenCapture initialized")

    def set_region(self, region: Tuple[int,int,int,int]) -> None:
        """Define the screen region to monitor."""
        self.region = region
        self.last_hash = None
        from datetime import datetime
        self.current_session_id = datetime.utcnow().isoformat()
        logger.info(f"Capture region set to {region}")

    def capture_region(self, region: Tuple[int, int, int, int]) -> Optional[Image.Image]:
        """
        Alias за _grab_region(), за да не мора GUI да го менува.
        """
        return self._grab_region(region)

    def has_changed(self, img: Image.Image) -> bool:
        """Wrapper кон private метод _has_changed."""
        return self._has_changed(img)

    def detect_scroll(self, img: Image.Image) -> Optional[Dict]:
        """Wrapper кон ScrollTracker.detect_scroll."""
        return self.scroll_tracker.detect_scroll(img)

    def adjust_marker_positions(self, markers: List[Dict], scroll_info: Dict) -> List[Dict]:
        """Wrapper кон ScrollTracker.adjust_marker_positions."""
        return self.scroll_tracker.adjust_marker_positions(markers, scroll_info)

    def get_scroll_history(self) -> List[Dict]:
        """Wrapper кон ScrollTracker.get_scroll_history."""
        return self.scroll_tracker.get_scroll_history()

    def capture_and_process(self) -> bool:
        """
        Capture the region, skip OCR if unchanged, otherwise run OCR and duplicate detection.
        Returns True if OCR+processing ran, False otherwise.
        """
        if not self.region:
            logger.error("No capture region defined")
            return False

        img = self._grab_region(self.region)
        if img is None:
            return False

        # 1) Scroll detection by image
        scroll_info = self.scroll_tracker.detect_scroll(img)

        # 2) Skip OCR if pHash unchanged
        if not self._has_changed(img):
            if scroll_info:
                logger.debug(f"Scroll on unchanged: {scroll_info['direction']}")
                self._update_markers_for_scroll(scroll_info)
            else:
                logger.debug("Region unchanged; skipping OCR")
            return False

        # 3) Perform OCR
        texts = self.ocr.extract_text_with_positions(img)
        if not texts:
            logger.debug("OCR returned no text")
            self.overlay.clear_markers()
            return False

        logger.info(f"OCR found {len(texts)} entries")

        # 4) OCR-based scroll detection & reposition
        adjusted_texts, ocr_scroll = self.scroll_tracker.track_ocr_results(texts)
        if ocr_scroll and not scroll_info:
            scroll_info = ocr_scroll

        # 5) Process texts through duplicate tracker
        self.tracker.process(adjusted_texts)

        # 6) Marker reposition if scroll
        if scroll_info:
            self._update_markers_for_scroll(scroll_info)

        # 7) Persist raw texts into SQLite
        for item in texts:
            name = item.get("text")
            if name:
                self.db.add_name_occurrence(
                    name,
                    count=1,
                    session_id=self.current_session_id
                )

        return True

    def _grab_region(self, region: Tuple[int,int,int,int]) -> Optional[Image.Image]:
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
        Compare pHash of current image to last. Returns True if diff > threshold.
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
            # fallback: always treat as changed
            self.last_hash = None
            return True

    def _update_markers_for_scroll(self, scroll_info: Dict) -> None:
        """Reposition existing overlay markers when scroll is detected."""
        try:
            current = getattr(self.overlay, "get_current_markers", lambda: [])()
            marker_dicts = [
                {"x": x, "y": y, "width": w, "height": h}
                for (x,y,w,h) in current
            ]
            adjusted = self.scroll_tracker.adjust_marker_positions(marker_dicts, scroll_info)
            tuples = [(m["x"],m["y"],m["width"],m["height"]) for m in adjusted]
            self.overlay.update_markers(tuples)
            logger.debug(f"Updated {len(adjusted)} markers for scroll")
        except Exception as e:
            logger.error(f"Error updating markers for scroll: {e}", exc_info=True)

    def reset_session(self) -> None:
        """Clear in-memory session state (database kept)."""
        self.tracker.reset_session()
        self.scroll_tracker.reset()
        self.last_hash = None
        from datetime import datetime
        self.current_session_id = datetime.utcnow().isoformat()
        logger.info("Session reset")

    def clear_all(self) -> None:
        """Clear both session state and persistent DB."""
        self.tracker.clear_all()
        self.scroll_tracker.reset()
        self.last_hash = None
        self.db.clear_all_data()
        logger.info("All data cleared")

    def get_statistics(self) -> Dict:
        """Return current session + DB stats."""
        return self.tracker.get_statistics()

    def save_screenshot(self, img: Image.Image, path: str) -> None:
        """Save last screenshot for debugging."""
        try:
            img.save(path)
            logger.info(f"Screenshot saved to {path}")
        except Exception as e:
            logger.error(f"Save screenshot failed: {e}", exc_info=True)

    def get_screen_info(self) -> Dict:
        """Return overall screen size and current region."""
        size = pyautogui.size()
        return {
            "screen_width": size.width,
            "screen_height": size.height,
            "region": self.region
        }
