import unittest
import sys
from unittest.mock import MagicMock

# Mock mpyq before importing sc2reader components
sys.modules['mpyq'] = MagicMock()

from sc2reader.decoders import ByteDecoder, BitPackedDecoder

class TestDecoders(unittest.TestCase):
    def test_byte_decoder_read_range(self):
        contents = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
        decoder = ByteDecoder(contents, endian="LITTLE")

        # Standard slice
        self.assertEqual(decoder.read_range(2, 5), b"\x02\x03\x04")

        # Start of buffer
        self.assertEqual(decoder.read_range(0, 3), b"\x00\x01\x02")

        # End of buffer
        self.assertEqual(decoder.read_range(7, 10), b"\x07\x08\x09")

        # Out of bounds - should behave like python slicing
        self.assertEqual(decoder.read_range(8, 15), b"\x08\x09")
        self.assertEqual(decoder.read_range(15, 20), b"")

        # Negative indices - also standard python slicing behavior
        self.assertEqual(decoder.read_range(-3, -1), b"\x07\x08")

        # Ensure it doesn't affect or depends on the current position
        decoder.read(5)
        self.assertEqual(decoder.tell(), 5)
        self.assertEqual(decoder.read_range(0, 2), b"\x00\x01")
        self.assertEqual(decoder.tell(), 5)

    def test_bit_packed_decoder_read_range(self):
        contents = b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09"
        decoder = BitPackedDecoder(contents)

        # Standard slice
        self.assertEqual(decoder.read_range(2, 5), b"\x02\x03\x04")

        # Start of buffer
        self.assertEqual(decoder.read_range(0, 3), b"\x00\x01\x02")

        # End of buffer
        self.assertEqual(decoder.read_range(7, 10), b"\x07\x08\x09")

        # Out of bounds
        self.assertEqual(decoder.read_range(8, 15), b"\x08\x09")

        # Ensure it doesn't affect or depends on the current position
        decoder.read_bits(8)
        self.assertEqual(decoder.tell(), 1)
        self.assertEqual(decoder.read_range(0, 2), b"\x00\x01")
        self.assertEqual(decoder.tell(), 1)

if __name__ == "__main__":
    unittest.main()
