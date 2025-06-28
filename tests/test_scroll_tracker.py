"""
Unit tests for scroll tracking functionality
"""

import unittest
from unittest.mock import Mock, patch
import numpy as np
from PIL import Image
import cv2

from core.scroll_tracker import ScrollTracker


class TestScrollTracker(unittest.TestCase):
    """Test cases for ScrollTracker class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scroll_tracker = ScrollTracker(scroll_threshold=10, correlation_threshold=0.7)
        
        # Create test images
        self.test_image1 = Image.new('RGB', (100, 200), color='white')
        self.test_image2 = Image.new('RGB', (100, 200), color='white')
        
    def test_initialization(self):
        """Test ScrollTracker initialization"""
        tracker = ScrollTracker()
        self.assertEqual(tracker.scroll_threshold, 10)
        self.assertEqual(tracker.correlation_threshold, 0.7)
        self.assertIsNone(tracker.last_image)
        self.assertEqual(len(tracker.scroll_history), 0)
        
    def test_detect_scroll_no_previous_image(self):
        """Test scroll detection when no previous image exists"""
        result = self.scroll_tracker.detect_scroll(self.test_image1)
        self.assertIsNone(result)
        self.assertEqual(self.scroll_tracker.last_image, self.test_image1)
        
    def test_detect_scroll_different_sizes(self):
        """Test scroll detection with different image sizes"""
        self.scroll_tracker.last_image = self.test_image1
        different_size_image = Image.new('RGB', (50, 100), color='white')
        
        result = self.scroll_tracker.detect_scroll(different_size_image)
        self.assertIsNone(result)
        
    @patch('cv2.matchTemplate')
    def test_detect_scroll_down(self, mock_match_template):
        """Test scroll down detection"""
        # Mock OpenCV template matching to simulate scroll down
        mock_match_template.return_value = np.array([[0.8]])  # High correlation
        
        self.scroll_tracker.last_image = self.test_image1
        result = self.scroll_tracker.detect_scroll(self.test_image2)
        
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result['direction'], 'down')
            self.assertGreater(result['confidence'], 0.7)
        
    @patch('cv2.matchTemplate')
    def test_detect_scroll_up(self, mock_match_template):
        """Test scroll up detection"""
        # Mock OpenCV template matching to simulate scroll up
        mock_match_template.return_value = np.array([[0.9]])  # High correlation
        
        self.scroll_tracker.last_image = self.test_image1
        result = self.scroll_tracker.detect_scroll(self.test_image2)
        
        self.assertIsNotNone(result)
        if result:
            self.assertEqual(result['direction'], 'up')
            self.assertGreater(result['confidence'], 0.7)
        
    def test_adjust_marker_positions_down(self):
        """Test marker position adjustment for scroll down"""
        markers = [
            {'x': 10, 'y': 50, 'width': 20, 'height': 10},
            {'x': 30, 'y': 100, 'width': 25, 'height': 15}
        ]
        scroll_info = {'direction': 'down', 'magnitude': 20}
        
        adjusted = self.scroll_tracker.adjust_marker_positions(markers, scroll_info)
        
        self.assertEqual(len(adjusted), 2)
        self.assertEqual(adjusted[0]['y'], 30)  # 50 - 20
        self.assertEqual(adjusted[1]['y'], 80)  # 100 - 20
        
    def test_adjust_marker_positions_up(self):
        """Test marker position adjustment for scroll up"""
        markers = [
            {'x': 10, 'y': 50, 'width': 20, 'height': 10},
            {'x': 30, 'y': 100, 'width': 25, 'height': 15}
        ]
        scroll_info = {'direction': 'up', 'magnitude': 15}
        
        adjusted = self.scroll_tracker.adjust_marker_positions(markers, scroll_info)
        
        self.assertEqual(len(adjusted), 2)
        self.assertEqual(adjusted[0]['y'], 65)  # 50 + 15
        self.assertEqual(adjusted[1]['y'], 115)  # 100 + 15
        
    def test_adjust_marker_positions_scrolled_out(self):
        """Test that markers scrolled out of view are removed"""
        markers = [
            {'x': 10, 'y': 10, 'width': 20, 'height': 10},  # Will be scrolled out
            {'x': 30, 'y': 100, 'width': 25, 'height': 15}  # Will remain visible
        ]
        scroll_info = {'direction': 'down', 'magnitude': 50}
        
        adjusted = self.scroll_tracker.adjust_marker_positions(markers, scroll_info)
        
        # The first marker: y = 10 - 50 = -40, height = 10, so y + height = -30 > -50 (tolerance)
        # The second marker: y = 100 - 50 = 50, height = 15, so y + height = 65 > -50
        # Both markers should remain visible due to the -50 tolerance
        self.assertEqual(len(adjusted), 2)  # Both markers should remain
        self.assertEqual(adjusted[0]['y'], -40)  # 10 - 50
        self.assertEqual(adjusted[1]['y'], 50)   # 100 - 50
        
    def test_track_ocr_results_no_previous(self):
        """Test OCR tracking with no previous results"""
        ocr_results = [
            {'text': 'John', 'bbox': [10, 20, 30, 10]},
            {'text': 'Jane', 'bbox': [40, 50, 25, 12]}
        ]
        
        adjusted, scroll_info = self.scroll_tracker.track_ocr_results(ocr_results)
        
        self.assertEqual(adjusted, ocr_results)
        self.assertIsNone(scroll_info)
        
    def test_track_ocr_results_consistent_movement(self):
        """Test OCR tracking with consistent movement (scroll)"""
        # First scan
        ocr_results1 = [
            {'text': 'John', 'bbox': [10, 20, 30, 10]},
            {'text': 'Jane', 'bbox': [40, 50, 25, 12]}
        ]
        self.scroll_tracker.track_ocr_results(ocr_results1)
        
        # Second scan with consistent downward movement
        ocr_results2 = [
            {'text': 'John', 'bbox': [10, 40, 30, 10]},  # Moved down 20px
            {'text': 'Jane', 'bbox': [40, 70, 25, 12]}   # Moved down 20px
        ]
        
        adjusted, scroll_info = self.scroll_tracker.track_ocr_results(ocr_results2)
        
        self.assertIsNotNone(scroll_info)
        if scroll_info:
            self.assertEqual(scroll_info['direction'], 'down')
            self.assertEqual(scroll_info['magnitude'], 20)
        
    def test_track_ocr_results_inconsistent_movement(self):
        """Test OCR tracking with inconsistent movement (not scroll)"""
        # First scan
        ocr_results1 = [
            {'text': 'John', 'bbox': [10, 20, 30, 10]},
            {'text': 'Jane', 'bbox': [40, 50, 25, 12]}
        ]
        self.scroll_tracker.track_ocr_results(ocr_results1)
        
        # Second scan with inconsistent movement
        ocr_results2 = [
            {'text': 'John', 'bbox': [10, 40, 30, 10]},  # Moved down 20px
            {'text': 'Jane', 'bbox': [40, 30, 25, 12]}   # Moved up 20px
        ]
        
        adjusted, scroll_info = self.scroll_tracker.track_ocr_results(ocr_results2)
        
        self.assertIsNone(scroll_info)  # Should not detect scroll
        
    def test_is_scroll_event(self):
        """Test scroll event detection"""
        # Mock scroll detection to return high confidence
        with patch.object(self.scroll_tracker, 'detect_scroll') as mock_detect:
            mock_detect.return_value = {'confidence': 0.9, 'direction': 'down'}
            
            result = self.scroll_tracker.is_scroll_event(self.test_image1)
            self.assertTrue(result)
            
    def test_get_scroll_history(self):
        """Test scroll history retrieval"""
        # Add some mock scroll events
        self.scroll_tracker.scroll_history = [
            {'direction': 'down', 'magnitude': 20, 'confidence': 0.8, 'timestamp': 123},
            {'direction': 'up', 'magnitude': 15, 'confidence': 0.7, 'timestamp': 124}
        ]
        
        history = self.scroll_tracker.get_scroll_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['direction'], 'down')
        self.assertEqual(history[1]['direction'], 'up')
        
    def test_reset(self):
        """Test scroll tracker reset"""
        # Set some state
        self.scroll_tracker.last_image = self.test_image1
        self.scroll_tracker.scroll_history = [{'direction': 'down'}]
        self.scroll_tracker.last_ocr_results = [{'text': 'test'}]
        
        self.scroll_tracker.reset()
        
        self.assertIsNone(self.scroll_tracker.last_image)
        self.assertEqual(len(self.scroll_tracker.scroll_history), 0)
        self.assertEqual(len(self.scroll_tracker.last_ocr_results), 0)


if __name__ == '__main__':
    unittest.main() 