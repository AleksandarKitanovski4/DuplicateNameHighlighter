#!/usr/bin/env python3
"""
Simple OCR Demo without complex dependencies
"""

import os
import sys
import logging
from PIL import Image, ImageDraw, ImageFont
import pytesseract

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_tesseract():
    """Test if Tesseract is available"""
    try:
        # Create a simple test image
        test_image = Image.new('RGB', (200, 50), color='white')
        draw = ImageDraw.Draw(test_image)
        draw.text((10, 10), "TEST", fill='black')
        
        # Test OCR
        result = pytesseract.image_to_string(test_image)
        logger.info(f"Tesseract test result: '{result.strip()}'")
        return True
    except Exception as e:
        logger.error(f"Tesseract test failed: {str(e)}")
        return False

def create_sample_image():
    """Create a sample image with names"""
    try:
        # Create image
        width, height = 600, 400
        image = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(image)
        
        # Sample names (with duplicates)
        names = [
            "John Smith", "Alice Johnson", "Bob Wilson",
            "John Smith", "Carol Davis", "Alice Johnson", 
            "David Brown", "John Smith", "Eve Miller"
        ]
        
        # Draw names
        y_pos = 50
        for name in names:
            draw.text((50, y_pos), name, fill='black')
            y_pos += 35
        
        return image
    except Exception as e:
        logger.error(f"Error creating image: {str(e)}")
        return None

def extract_names_basic(image):
    """Extract names using basic OCR"""
    try:
        # Simple OCR extraction
        text = pytesseract.image_to_string(image)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        logger.info(f"Extracted text lines: {lines}")
        return lines
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}")
        return []

def find_duplicates(names):
    """Find duplicate names in the list"""
    name_counts = {}
    duplicates = []
    
    for name in names:
        if name in name_counts:
            name_counts[name] += 1
            if name_counts[name] == 2:  # First time it becomes duplicate
                duplicates.append(name)
        else:
            name_counts[name] = 1
    
    return duplicates, name_counts

def main():
    """Main demo function"""
    logger.info("Simple OCR Demo Starting...")
    
    # Test Tesseract
    if not test_tesseract():
        logger.error("Tesseract is not working properly")
        return 1
    
    # Create sample image
    sample_image = create_sample_image()
    if sample_image is None:
        logger.error("Failed to create sample image")
        return 1
    
    # Save sample image
    sample_image.save("sample.png")
    logger.info("Sample image saved as 'sample.png'")
    
    # Extract names
    extracted_names = extract_names_basic(sample_image)
    if not extracted_names:
        logger.warning("No names extracted")
        return 1
    
    logger.info(f"Extracted {len(extracted_names)} names")
    
    # Find duplicates
    duplicates, counts = find_duplicates(extracted_names)
    
    if duplicates:
        logger.info(f"Found duplicates: {duplicates}")
        logger.info("Name counts:")
        for name, count in counts.items():
            if count > 1:
                logger.info(f"  '{name}': {count} times")
    else:
        logger.info("No duplicates found")
    
    logger.info("Demo completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())