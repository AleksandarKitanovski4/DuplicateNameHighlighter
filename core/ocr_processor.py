"""
OCR processing module using Tesseract for text extraction
"""

import logging
import os
import tempfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import pytesseract
from pytesseract import Output

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Handles OCR text extraction with position information"""

    def __init__(self, min_confidence: float = 60.0):
        self.min_confidence = min_confidence
        self.setup_tesseract()

    def setup_tesseract(self):
        """Locate and configure the Tesseract OCR executable."""
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            'tesseract'  # assume on PATH
        ]
        for path in possible_paths:
            try:
                if os.path.exists(path) or path == 'tesseract':
                    pytesseract.pytesseract.tesseract_cmd = path
                    # quick sanity check
                    img = Image.new('RGB', (10, 10), 'white')
                    pytesseract.image_to_string(img)
                    logger.info(f"Tesseract found at: {path}")
                    return
            except Exception:
                continue
        logger.error("Tesseract OCR not found. Please install it.")
        raise RuntimeError("Tesseract OCR not found")

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Convert to grayscale, scale small images, denoise and binarize
        using OpenCV for optimal OCR results.
        """
        # to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        w, h = image.size
        # scale up to at least 300×100, but no more than 2×
        if w < 300 or h < 100:
            factor = min(2.0, max(300/w, 100/h))
            image = image.resize((int(w*factor), int(h*factor)), Image.LANCZOS)
        arr = np.array(image)
        arr = cv2.medianBlur(arr, 3)
        arr = cv2.adaptiveThreshold(
            arr, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        )
        return Image.fromarray(arr)

    def extract_text_with_positions(self, image: Image.Image) -> list[dict]:
        """
        Run OCR, filter low-confidence or tiny regions, then
        group by block to form multi-word names.
        Returns list of dicts with keys: name, x, y, width, height, confidence.
        """
        if image is None:
            logger.error("No image provided for OCR")
            return []

        processed = self.preprocess_image(image)
        config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz '
        data = pytesseract.image_to_data(
            processed, config=config, output_type=Output.DICT
        )

        entries = []
        n = len(data['text'])
        for i in range(n):
            conf = float(data['conf'][i] or -1)
            txt = data['text'][i].strip()
            if conf < self.min_confidence or len(txt) < 2 or txt.isdigit():
                continue
            x, y, w, h = (data['left'][i], data['top'][i],
                          data['width'][i], data['height'][i])
            if w < 10 or h < 8:
                continue
            entries.append({
                'text': txt,
                'block': data.get('block_num', [0]*n)[i],
                'par': data.get('par_num', [0]*n)[i],
                'x': x, 'y': y, 'width': w, 'height': h, 'conf': conf
            })

        # group by block_num (and par_num)
        grouped = {}
        for e in entries:
            key = (e['block'], e['par'])
            grouped.setdefault(key, []).append(e)

        results = []
        for group in grouped.values():
            # sort left-to-right, top-to-bottom
            group.sort(key=lambda e: (e['y'], e['x']))
            texts = [e['text'] for e in group]
            name = ' '.join(texts).title()
            xs = [e['x'] for e in group]
            ys = [e['y'] for e in group]
            ws = [e['width'] for e in group]
            hs = [e['height'] for e in group]
            confs = [e['conf'] for e in group]
            min_x, min_y = min(xs), min(ys)
            max_x = max(x + w for x, w in zip(xs, ws))
            max_y = max(y + h for y, h in zip(ys, hs))
            results.append({
                'name': name,
                'x': min_x, 'y': min_y,
                'width': max_x - min_x,
                'height': max_y - min_y,
                'confidence': sum(confs)/len(confs)
            })

        logger.info(f"OCR extracted {len(results)} names")
        return results

    def test_extract(self) -> bool:
        """
        Synthetic unit test: draw known names, run extract, assert grouping.
        """
        try:
            img = Image.new('RGB', (400, 200), 'white')
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except Exception:
                font = ImageFont.load_default()
            test_names = [
                ("John Smith", (50, 50)),
                ("Jane Doe", (50, 100)),
                ("Bob Johnson", (200, 50)),
                ("Alice Brown", (200, 100))
            ]
            for txt, pos in test_names:
                draw.text(pos, txt, fill='black', font=font)
            results = self.extract_text_with_positions(img)
            names = {r['name'] for r in results}
            # expect all four full names
            success = set([n for n, _ in test_names]).issubset(names)
            if success:
                logger.info("test_extract passed")
            else:
                logger.warning(f"test_extract failed, found: {names}")
            return success
        except Exception as e:
            logger.error(f"test_extract exception: {e}")
            return False