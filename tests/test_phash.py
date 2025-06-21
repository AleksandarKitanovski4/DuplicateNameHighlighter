import unittest
from PIL import Image, ImageChops
import imagehash
import numpy as np

class TestPhashDifference(unittest.TestCase):
    def setUp(self):
        # Create two simple images
        self.img1 = Image.new('RGB', (64, 64), color='white')
        self.img2 = Image.new('RGB', (64, 64), color='white')
        # Draw a black rectangle on img2
        for x in range(20, 44):
            for y in range(20, 44):
                self.img2.putpixel((x, y), (0, 0, 0))

    def test_phash_difference(self):
        hash1 = imagehash.phash(self.img1)
        hash2 = imagehash.phash(self.img2)
        diff = hash1 - hash2
        self.assertTrue(diff > 0)
        self.assertIsInstance(diff, int)

if __name__ == '__main__':
    unittest.main() 