import random
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

DATA = random.Random(3).randbytes(0x10000)

PROGRAM = random.Random(4).randbytes(spc7110.PROGRAM_BYTES)


def a_part() -> Any:
    return spc7110.Chip("spc7110", rom=PROGRAM + DATA).reset()


def pointed(offset: int, settings: int = 0, adjust: int = 0, stride: int = 0) -> Any:
    chip = a_part()
    for register, value in (
        (0x4814, adjust & 0xFF),
        (0x4815, adjust >> 8),
        (0x4816, stride & 0xFF),
        (0x4817, stride >> 8),
        (0x4811, offset & 0xFF),
        (0x4812, (offset >> 8) & 0xFF),
        (0x4813, offset >> 16),
        (0x4818, settings),
    ):
        chip.write(register, value)
    return chip


def offset_of(chip: Any) -> int:
    return int(chip.read(0x4811) | chip.read(0x4812) << 8 | chip.read(0x4813) << 16)


class FetchTest(unittest.TestCase):
    def test_the_port_holds_the_byte_at_the_offset(self) -> None:
        # Arrange
        chip = pointed(0x1234)

        # Act
        found = chip.read(0x4810)

        # Assert
        self.assertEqual(found, DATA[0x1234])

    def test_reading_it_moves_the_offset_on_by_one(self) -> None:
        # Arrange
        chip = pointed(0x1234)

        # Act
        found = [chip.read(0x4810) for _ in range(3)]

        # Assert
        self.assertEqual((found, offset_of(chip)), (list(DATA[0x1234:0x1237]), 0x1237))

    def test_the_stride_register_sets_the_step_when_selected(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x01, stride=0x10)

        # Act
        found = [chip.read(0x4810) for _ in range(2)]

        # Assert
        self.assertEqual(found, [DATA[0x1000], DATA[0x1010]])

    def test_a_signed_stride_steps_backwards(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x05, stride=0xFFFF)

        # Act
        chip.read(0x4810)

        # Assert
        self.assertEqual(offset_of(chip), 0x0FFF)

    def test_the_adjust_is_added_when_enabled(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x02, adjust=0x0020)

        # Act
        found = chip.read(0x4810)

        # Assert
        self.assertEqual(found, DATA[0x1020])

    def test_a_signed_adjust_reaches_backwards(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x0A, adjust=0xFFFE)

        # Act
        found = chip.read(0x4810)

        # Assert
        self.assertEqual(found, DATA[0x0FFE])

    def test_bit_four_moves_the_adjust_instead_of_the_offset(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x12, adjust=0x0004)

        # Act
        chip.read(0x4810)

        # Assert
        self.assertEqual((offset_of(chip), chip.read(0x4814)), (0x1000, 0x05))

    def test_the_offset_wraps_at_its_twenty_three_bits(self) -> None:
        # Arrange
        chip = pointed(0x7FFFFF)

        # Act
        chip.read(0x4810)

        # Assert
        self.assertEqual(offset_of(chip), 0x000000)


class SeekTest(unittest.TestCase):
    def test_trigger_one_adds_the_adjust_when_its_low_byte_is_written(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x20)

        # Act
        chip.write(0x4814, 0x30)

        # Assert
        self.assertEqual((offset_of(chip), chip.read(0x4810)), (0x1030, DATA[0x1030]))

    def test_trigger_two_adds_it_when_its_high_byte_is_written(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x40, adjust=0x0030)

        # Act
        chip.write(0x4815, 0x01)

        # Assert
        self.assertEqual(offset_of(chip), 0x1130)

    def test_trigger_three_adds_it_when_the_seek_register_is_read(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x60, adjust=0x0030)

        # Act
        returned = chip.read(0x481A)

        # Assert
        self.assertEqual((returned, offset_of(chip)), (0x00, 0x1030))

    def test_reading_the_seek_register_under_another_trigger_moves_nothing(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x20, adjust=0x0030)

        # Act
        chip.read(0x481A)

        # Assert
        self.assertEqual(offset_of(chip), 0x1000)

    def test_writing_the_high_adjust_byte_with_the_adjust_on_fetches_again(self) -> None:
        # Arrange
        chip = pointed(0x1000, settings=0x02)

        # Act
        chip.write(0x4815, 0x01)

        # Assert
        self.assertEqual(chip.read(0x4810), DATA[0x1100])


class RegisterTest(unittest.TestCase):
    def test_the_offset_bank_and_the_settings_keep_seven_bits(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        chip.write(0x4813, 0xFF)
        chip.write(0x4818, 0xFF)

        # Assert
        self.assertEqual((chip.read(0x4813), chip.read(0x4818)), (0x7F, 0x7F))

    def test_the_port_ignores_a_write(self) -> None:
        # Arrange
        chip = pointed(0x1234)

        # Act
        chip.write(0x4810, 0x00)

        # Assert
        self.assertEqual(chip.read(0x4810), DATA[0x1234])

    def test_the_stride_registers_read_back(self) -> None:
        # Arrange
        chip = pointed(0, stride=0xBEEF)

        # Act
        found = (chip.read(0x4816), chip.read(0x4817))

        # Assert
        self.assertEqual(found, (0xEF, 0xBE))

    def test_registers_the_port_does_not_have_drive_nothing(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        found = [chip.read(register) for register in (0x4819, 0x481B, 0x481F)]

        # Assert
        self.assertEqual(found, [None, None, None])


if __name__ == "__main__":
    unittest.main()
