import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

BASE = 8

ONE_MEGABYTE = 0x100000


def a_data_rom(entries: list[tuple[int, int]], size: int = ONE_MEGABYTE) -> bytes:
    held = bytearray(size)
    at = BASE
    for mode, address in entries:
        held[at : at + 4] = bytes((mode, address >> 16, (address >> 8) & 0xFF, address & 0xFF))
        at += 4
    return bytes(held)


class DirectoryTest(unittest.TestCase):
    def test_entries_come_back_as_a_mode_and_an_address(self) -> None:
        # Arrange
        drom = a_data_rom([(2, 0x1000), (0, 0x2000)])

        # Act
        found, _ = spc7110.directory(drom, BASE)

        # Assert
        self.assertEqual(found, [(2, 0x1000), (0, 0x2000)])

    def test_it_stops_where_the_addresses_stop_ascending(self) -> None:
        # Arrange
        drom = a_data_rom([(2, 0x2000), (2, 0x1000)])

        # Act
        found, _ = spc7110.directory(drom, BASE)

        # Assert
        self.assertEqual(found, [(2, 0x2000)])

    def test_it_stops_at_a_mode_the_part_does_not_have(self) -> None:
        # Arrange
        drom = a_data_rom([(2, 0x1000), (7, 0x2000)])

        # Act
        found, _ = spc7110.directory(drom, BASE)

        # Assert
        self.assertEqual(found, [(2, 0x1000)])

    def test_it_stops_at_an_address_past_the_end(self) -> None:
        # Arrange
        drom = a_data_rom([(2, 0x1000), (2, 0x200000)])

        # Act
        found, _ = spc7110.directory(drom, BASE)

        # Assert
        self.assertEqual(found, [(2, 0x1000)])

    def test_it_reports_where_the_directory_ended(self) -> None:
        # Arrange
        drom = a_data_rom([(2, 0x1000), (0, 0x2000)])

        # Act
        _, end = spc7110.directory(drom, BASE)

        # Assert
        self.assertEqual(end, 16)

    def test_a_base_past_the_end_yields_nothing(self) -> None:
        # Arrange
        drom = bytes(16)

        # Act
        found, end = spc7110.directory(drom, 0x1000)

        # Assert
        self.assertEqual((found, end), ([], 0x1000))


class SplitTest(unittest.TestCase):
    def test_the_program_rom_is_the_first_megabyte(self) -> None:
        # Arrange
        expected = ONE_MEGABYTE

        # Act
        published = spc7110.PROGRAM_BYTES

        # Assert
        self.assertEqual(published, expected)

    def test_the_data_rom_is_what_follows_it(self) -> None:
        # Arrange
        image = b"\x11" * ONE_MEGABYTE + b"\x22" * 0x40000

        # Act
        found = spc7110.data_rom(image)

        # Assert
        self.assertEqual(found, b"\x22" * 0x40000)

    def test_an_image_no_larger_than_the_program_rom_has_no_data_rom(self) -> None:
        # Arrange
        image = b"\x11" * ONE_MEGABYTE

        # Act
        found = spc7110.data_rom(image)

        # Assert
        self.assertEqual(found, b"")


if __name__ == "__main__":
    unittest.main()
