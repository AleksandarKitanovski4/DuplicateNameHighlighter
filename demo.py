#!/usr/bin/env python3
"""
Duplicate Name Highlighter - Command Line Demo
Demonstrates OCR functionality without GUI dependencies
"""

import os
import sys
import logging
import tempfile
from PIL import Image, ImageDraw, ImageFont
from core.ocr_processor import OCRProcessor
from core.duplicate_tracker import DuplicateTracker
from core.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_image_with_names():
    """Create a sample image with names for testing OCR"""
    try:
        # Create a white background image
        width, height = 800, 600
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Try to use a standard font, fall back to default if not available
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            try:
                font = ImageFont.load_default()
            except:
                font = None
        
        # Sample names to draw (including some duplicates)
        names = [
            "John Smith", "Alice Johnson", "Bob Wilson", "Carol Davis",
            "John Smith", "David Brown", "Eve Miller", "Frank Garcia",
            "Alice Johnson", "Grace Lee", "Henry Taylor", "Ivy Anderson",
            "John Smith", "Jack Thomas", "Karen White", "Liam Harris"
        ]
        
        # Draw names in a grid pattern
        x_start, y_start = 50, 50
        x_spacing, y_spacing = 180, 40
        
        for i, name in enumerate(names):
            x = x_start + (i % 4) * x_spacing
            y = y_start + (i // 4) * y_spacing
            
            # Draw text with black color
            draw.text((x, y), name, fill='black', font=font)
        
        return image
        
    except Exception as e:
        logger.error(f"Error creating sample image: {str(e)}")
        return None

def test_ocr_functionality():
    """Test OCR processing with sample image"""
    logger.info("Testing OCR functionality...")
    
    try:
        # Create sample image
        sample_image = create_sample_image_with_names()
        if sample_image is None:
            logger.error("Failed to create sample image")
            return False
        
        # Save sample image for reference
        sample_image.save("sample_names.png")
        logger.info("Sample image saved as 'sample_names.png'")
        
        # Initialize OCR processor
        ocr_processor = OCRProcessor()
        
        # Test OCR functionality first
        if not ocr_processor.test_ocr():
            logger.error("OCR test failed")
            return False
        
        # Process the sample image
        logger.info("Processing sample image with OCR...")
        names_with_positions = ocr_processor.extract_text_with_positions(sample_image)
        
        if not names_with_positions:
            logger.warning("No names detected by OCR")
            return False
        
        logger.info(f"OCR detected {len(names_with_positions)} text items:")
        for item in names_with_positions:
            logger.info(f"  - '{item['name']}' at ({item['x']}, {item['y']}) "
                       f"size: {item['width']}x{item['height']} "
                       f"confidence: {item['confidence']:.1f}%")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing OCR: {str(e)}", exc_info=True)
        return False

def test_duplicate_detection():
    """Test duplicate name detection"""
    logger.info("Testing duplicate detection...")
    
    try:
        # Initialize components
        database = Database("test_duplicates.db")
        duplicate_tracker = DuplicateTracker(database)
        ocr_processor = OCRProcessor()
        
        # Create sample image
        sample_image = create_sample_image_with_names()
        if sample_image is None:
            return False
        
        # Process image with OCR
        names_with_positions = ocr_processor.extract_text_with_positions(sample_image)
        
        if not names_with_positions:
            logger.warning("No names detected for duplicate testing")
            return False
        
        # Process names for duplicates
        logger.info("Processing names for duplicate detection...")
        duplicates = duplicate_tracker.process_names(names_with_positions)
        
        if duplicates:
            logger.info(f"Found {len(duplicates)} duplicate entries:")
            for dup in duplicates:
                logger.info(f"  - '{dup['name']}' appears {dup['count']} times")
                for pos in dup['positions']:
                    logger.info(f"    Position: ({pos['x']}, {pos['y']}) "
                               f"size: {pos['width']}x{pos['height']}")
        else:
            logger.info("No duplicates found")
        
        # Get statistics
        stats = duplicate_tracker.get_name_statistics()
        logger.info(f"Statistics: {stats}")
        
        # Clean up test database
        database.close()
        if os.path.exists("test_duplicates.db"):
            os.remove("test_duplicates.db")
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing duplicate detection: {str(e)}", exc_info=True)
        return False

def main():
    """Main demo function"""
    logger.info("Duplicate Name Highlighter - Command Line Demo")
    logger.info("=" * 50)
    
    # Test OCR functionality
    ocr_success = test_ocr_functionality()
    
    if ocr_success:
        logger.info("OCR test passed!")
        
        # Test duplicate detection
        duplicate_success = test_duplicate_detection()
        
        if duplicate_success:
            logger.info("Duplicate detection test passed!")
            logger.info("\nDemo completed successfully!")
            logger.info("Check 'sample_names.png' to see the generated test image.")
            return 0
        else:
            logger.error("Duplicate detection test failed")
            return 1
    else:
        logger.error("OCR test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())