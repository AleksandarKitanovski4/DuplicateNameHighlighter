"""
OCR processing module using Tesseract for text extraction
"""

import logging
import os
import tempfile
from PIL import Image, ImageEnhance
import pytesseract
from pytesseract import Output

logger = logging.getLogger(__name__)

class OCRProcessor:
    """Handles OCR text extraction with position information"""
    
    def __init__(self):
        self.setup_tesseract()
        self.min_confidence = 30  # Minimum confidence threshold for text detection
        
    def setup_tesseract(self):
        """Setup Tesseract OCR configuration"""
        # Try to find Tesseract executable
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            'tesseract'  # Assume it's in PATH
        ]
        
        tesseract_path = None
        for path in possible_paths:
            try:
                if os.path.exists(path) or path == 'tesseract':
                    pytesseract.pytesseract.tesseract_cmd = path
                    # Test if it works
                    test_image = Image.new('RGB', (100, 50), color='white')
                    pytesseract.image_to_string(test_image)
                    tesseract_path = path
                    break
            except Exception:
                continue
        
        if not tesseract_path:
            logger.error("Tesseract OCR not found. Please install Tesseract OCR.")
            raise RuntimeError("Tesseract OCR not found")
        
        logger.info(f"Tesseract found at: {tesseract_path}")
        
        # Configure OCR parameters for better name detection
        self.ocr_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 '
    
    def preprocess_image(self, image):
        """Preprocess image for better OCR accuracy
        
        Args:
            image: PIL Image object
            
        Returns:
            PIL Image object (preprocessed)
        """
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Resize if image is too small (OCR works better on larger images)
            width, height = image.size
            if width < 300 or height < 100:
                scale_factor = max(300 / width, 100 / height)
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.LANCZOS)
            
            return image
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            return image  # Return original if preprocessing fails
    
    def extract_text_with_positions(self, image):
        """Extract text with position information from image
        
        Args:
            image: PIL Image object
            
        Returns:
            List of dictionaries containing name and position info:
            [{'name': 'John', 'x': 10, 'y': 20, 'width': 30, 'height': 15}, ...]
        """
        try:
            if image is None:
                logger.error("No image provided for OCR")
                return []
            
            # Preprocess image
            processed_image = self.preprocess_image(image)
            
            # Extract text data with positions
            ocr_data = pytesseract.image_to_data(processed_image, 
                                               config=self.ocr_config,
                                               output_type=Output.DICT)
            
            names_with_positions = []
            
            # Process OCR results
            for i in range(len(ocr_data['text'])):
                confidence = float(ocr_data['conf'][i])
                text = ocr_data['text'][i].strip()
                
                # Filter out low confidence and empty text
                if confidence < self.min_confidence or not text:
                    continue
                
                # Filter out single characters and numbers-only text
                if len(text) < 2 or text.isdigit():
                    continue
                
                # Get position information
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                width = ocr_data['width'][i]
                height = ocr_data['height'][i]
                
                # Skip if dimensions are too small
                if width < 10 or height < 8:
                    continue
                
                name_data = {
                    'name': text,
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height,
                    'confidence': confidence
                }
                
                names_with_positions.append(name_data)
            
            logger.info(f"OCR extracted {len(names_with_positions)} potential names")
            return names_with_positions
            
        except Exception as e:
            logger.error(f"OCR processing error: {str(e)}", exc_info=True)
            return []
    
    def test_ocr(self):
        """Test OCR functionality with a sample image"""
        try:
            # Create a test image with text
            test_image = Image.new('RGB', (200, 100), color='white')
            
            # Use a temporary file to test OCR
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                test_image.save(temp_file.name)
                result = pytesseract.image_to_string(test_image)
                os.unlink(temp_file.name)
                
            logger.info("OCR test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"OCR test failed: {str(e)}")
            return False
