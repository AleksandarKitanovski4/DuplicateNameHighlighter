"""
Image processing utilities for the duplicate name highlighter
"""

import logging
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageChops
import numpy as np

logger = logging.getLogger(__name__)

class ImageUtils:
    """Utility functions for image processing"""
    
    @staticmethod
    def enhance_for_ocr(image):
        """Enhance image for better OCR results
        
        Args:
            image: PIL Image object
            
        Returns:
            Enhanced PIL Image object
        """
        try:
            if image is None:
                return None
            
            # Convert to grayscale if not already
            if image.mode != 'L':
                image = image.convert('L')
            
            # Increase contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Increase sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)
            
            # Apply unsharp mask for better text clarity
            image = image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=2))
            
            # Auto-level to improve contrast
            image = ImageOps.autocontrast(image, cutoff=1)
            
            return image
            
        except Exception as e:
            logger.error(f"Error enhancing image for OCR: {str(e)}")
            return image  # Return original on error
    
    @staticmethod
    def resize_for_ocr(image, min_width=300, min_height=100):
        """Resize image for optimal OCR processing
        
        Args:
            image: PIL Image object
            min_width: Minimum width for OCR
            min_height: Minimum height for OCR
            
        Returns:
            Resized PIL Image object
        """
        try:
            if image is None:
                return None
            
            width, height = image.size
            
            # Calculate scale factor if image is too small
            scale_x = min_width / width if width < min_width else 1
            scale_y = min_height / height if height < min_height else 1
            scale_factor = max(scale_x, scale_y)
            
            # Only resize if necessary
            if scale_factor > 1:
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)
                image = image.resize((new_width, new_height), Image.LANCZOS)
                logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")
            
            return image
            
        except Exception as e:
            logger.error(f"Error resizing image: {str(e)}")
            return image
    
    @staticmethod
    def denoise_image(image):
        """Remove noise from image
        
        Args:
            image: PIL Image object
            
        Returns:
            Denoised PIL Image object
        """
        try:
            if image is None:
                return None
            
            # Convert to numpy array for processing
            img_array = np.array(image)
            
            # Apply median filter to reduce noise
            from scipy import ndimage
            denoised_array = ndimage.median_filter(img_array, size=2)
            
            # Convert back to PIL Image
            denoised_image = Image.fromarray(denoised_array.astype('uint8'))
            
            return denoised_image
            
        except ImportError:
            # Fall back to PIL filters if scipy not available
            return image.filter(ImageFilter.MedianFilter(size=3))
        except Exception as e:
            logger.error(f"Error denoising image: {str(e)}")
            return image
    
    @staticmethod
    def apply_threshold(image, threshold=128):
        """Apply binary threshold to image
        
        Args:
            image: PIL Image object
            threshold: Threshold value (0-255)
            
        Returns:
            Thresholded PIL Image object
        """
        try:
            if image is None:
                return None
            
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # Apply threshold
            def threshold_func(pixel):
                return 255 if pixel > threshold else 0
            
            thresholded = image.point(threshold_func, mode='1')
            
            return thresholded
            
        except Exception as e:
            logger.error(f"Error applying threshold: {str(e)}")
            return image
    
    @staticmethod
    def get_image_stats(image):
        """Get statistical information about image
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with image statistics
        """
        try:
            if image is None:
                return {}
            
            # Convert to grayscale for analysis
            if image.mode != 'L':
                gray_image = image.convert('L')
            else:
                gray_image = image
            
            # Get histogram
            histogram = gray_image.histogram()
            
            # Calculate statistics
            total_pixels = sum(histogram)
            weighted_sum = sum(i * count for i, count in enumerate(histogram))
            mean_brightness = weighted_sum / total_pixels if total_pixels > 0 else 0
            
            # Find min and max brightness
            min_brightness = next(i for i, count in enumerate(histogram) if count > 0)
            max_brightness = next(255 - i for i, count in enumerate(reversed(histogram)) if count > 0)
            
            return {
                'width': image.width,
                'height': image.height,
                'mode': image.mode,
                'mean_brightness': mean_brightness,
                'min_brightness': min_brightness,
                'max_brightness': max_brightness,
                'contrast_ratio': (max_brightness - min_brightness) / 255.0
            }
            
        except Exception as e:
            logger.error(f"Error getting image stats: {str(e)}")
            return {}
    
    @staticmethod
    def calculate_similarity(image1, image2):
        """Calculate similarity between two images
        
        Args:
            image1: First PIL Image object
            image2: Second PIL Image object
            
        Returns:
            Float similarity score (0.0 to 1.0)
        """
        try:
            if image1 is None or image2 is None:
                return 0.0
            
            # Ensure images are same size
            if image1.size != image2.size:
                # Resize to match smaller image
                min_width = min(image1.width, image2.width)
                min_height = min(image1.height, image2.height)
                image1 = image1.resize((min_width, min_height), Image.LANCZOS)
                image2 = image2.resize((min_width, min_height), Image.LANCZOS)
            
            # Convert to same mode
            if image1.mode != image2.mode:
                if image1.mode != 'L':
                    image1 = image1.convert('L')
                if image2.mode != 'L':
                    image2 = image2.convert('L')
            
            # Calculate difference
            diff = ImageChops.difference(image1, image2)
            
            # Get histogram of differences
            histogram = diff.histogram()
            
            # Calculate similarity (inverse of average difference)
            total_pixels = sum(histogram)
            weighted_diff = sum(i * count for i, count in enumerate(histogram))
            avg_diff = weighted_diff / total_pixels if total_pixels > 0 else 0
            
            # Convert to similarity score (0-1)
            similarity = 1.0 - (avg_diff / 255.0)
            
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0
    
    @staticmethod
    def crop_to_content(image, padding=10):
        """Crop image to content area (remove empty borders)
        
        Args:
            image: PIL Image object
            padding: Additional padding around content
            
        Returns:
            Cropped PIL Image object
        """
        try:
            if image is None:
                return None
            
            # Convert to grayscale for analysis
            if image.mode != 'L':
                gray_image = image.convert('L')
            else:
                gray_image = image
            
            # Find bounding box of non-white content
            bbox = gray_image.getbbox()
            
            if bbox is None:
                # Image is completely white/empty
                return image
            
            # Add padding
            left, top, right, bottom = bbox
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(image.width, right + padding)
            bottom = min(image.height, bottom + padding)
            
            # Crop image
            cropped = image.crop((left, top, right, bottom))
            
            logger.debug(f"Cropped image from {image.size} to {cropped.size}")
            return cropped
            
        except Exception as e:
            logger.error(f"Error cropping image: {str(e)}")
            return image
    
    @staticmethod
    def create_thumbnail(image, size=(150, 150)):
        """Create thumbnail of image
        
        Args:
            image: PIL Image object
            size: Tuple of (width, height) for thumbnail
            
        Returns:
            Thumbnail PIL Image object
        """
        try:
            if image is None:
                return None
            
            # Create thumbnail while preserving aspect ratio
            thumbnail = image.copy()
            thumbnail.thumbnail(size, Image.LANCZOS)
            
            return thumbnail
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {str(e)}")
            return image
    
    @staticmethod
    def save_debug_image(image, filename, enhance_for_debug=True):
        """Save image for debugging purposes
        
        Args:
            image: PIL Image object
            filename: Output filename
            enhance_for_debug: Whether to enhance visibility for debugging
            
        Returns:
            Boolean success status
        """
        try:
            if image is None:
                return False
            
            debug_image = image.copy()
            
            if enhance_for_debug:
                # Enhance contrast for better visibility
                if debug_image.mode != 'L':
                    debug_image = debug_image.convert('L')
                
                enhancer = ImageEnhance.Contrast(debug_image)
                debug_image = enhancer.enhance(2.0)
            
            debug_image.save(filename)
            logger.debug(f"Debug image saved: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving debug image: {str(e)}")
            return False
