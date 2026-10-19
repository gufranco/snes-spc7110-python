import random
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

TABLE = 0x000008

ENTRIES = ((0, 0x0100), (1, 0x2000), (2, 0x4000), (3, 0x6000))

ARES_MODE0 = "848a6a30df8d5f17aea91437ae3aec80f7dd2a43984905b2f83c44a2f040acfa"

ARES_MODE1 = (
    "46a04365127446a197b9739933921b32237a396a3362a330db62960d0d8b0d71"
    "0dc3874b230536278a31d8ffc77d2c1a"
)

ARES_MODE2 = (
    "783f63bc22c4ba6db96a8eccaec2abdfb757bdcb1738ed26a1aec353c9d2c8b2"
    "918cacf8c217d4d3ddb5b19d3d0b144dbcba95218df65c6d2d36717056386721"
)

ARES_MODE1_SEEK_THREE = "46a197b9739933921b32237a396a3362a330db62960d0d8b0d710dc3874b2305"

ARES_MODE2_STRIDE_TWO = (
    "783f22c4b96aaec2918cc217ddb53d0bb7571738a1aec9d2bcba8df62d365638"
    "3c167c6c3e9c578fb2240a860a187bc92b31667222f4f97a8a4a9427f0fe8edc"
)

ARES_MODE0_STRIDE_ZERO = "84848484848484848484848484848484"

START_CLOCKS = 21


def a_cartridge() -> bytes:
    data = bytearray(random.Random(1).randbytes(0x10000))
    for index, (mode, address) in enumerate(ENTRIES):
        at = TABLE + 4 * index
        data[at : at + 4] = bytes((mode, address >> 16, (address >> 8) & 0xFF, address & 0xFF))
    return random.Random(2).randbytes(spc7110.PROGRAM_BYTES) + bytes(data)


def a_part() -> Any:
    return spc7110.Chip("spc7110", rom=a_cartridge()).reset()


def started(index: int, control: int = 0, seek: int = 0, stride: int = 0, part: Any = None) -> Any:
    chip = a_part() if part is None else part
    for register, value in (
        (0x4801, TABLE & 0xFF),
        (0x4802, (TABLE >> 8) & 0xFF),
        (0x4803, TABLE >> 16),
        (0x4804, index),
        (0x480B, control),
        (0x4805, seek & 0xFF),
        (0x4807, stride),
    ):
        chip.write(register, value)
    chip.write(0x4806, seek >> 8)
    return chip


def drained(chip: Any, count: int) -> str:
    return bytes(chip.read(0x4800) for _ in range(count)).hex()


class OutputTest(unittest.TestCase):
    def test_a_one_bit_stream_reads_what_ares_reads(self) -> None:
        # Arrange
        chip = started(0).tick(START_CLOCKS)

        # Act
        found = drained(chip, 32)

        # Assert
        self.assertEqual(found, ARES_MODE0)

    def test_a_two_bit_stream_reads_what_ares_reads(self) -> None:
        # Arrange
        chip = started(1).tick(START_CLOCKS)

        # Act
        found = drained(chip, 48)

        # Assert
        self.assertEqual(found, ARES_MODE1)

    def test_a_four_bit_stream_reads_what_ares_reads(self) -> None:
        # Arrange
        chip = started(2).tick(START_CLOCKS)

        # Act
        found = drained(chip, 64)

        # Assert
        self.assertEqual(found, ARES_MODE2)

    def test_a_seek_skips_whole_rows_before_the_first_read(self) -> None:
        # Arrange
        chip = started(1, control=0x02, seek=3).tick(START_CLOCKS)

        # Act
        found = drained(chip, 32)

        # Assert
        self.assertEqual(found, ARES_MODE1_SEEK_THREE)

    def test_a_seek_is_ignored_unless_its_bit_is_set(self) -> None:
        # Arrange
        chip = started(1, control=0x00, seek=3).tick(START_CLOCKS)

        # Act
        found = drained(chip, 48)

        # Assert
        self.assertEqual(found, ARES_MODE1)

    def test_a_stride_skips_rows_between_the_rows_it_keeps(self) -> None:
        # Arrange
        chip = started(2, control=0x01, stride=2).tick(START_CLOCKS)

        # Act
        found = drained(chip, 64)

        # Assert
        self.assertEqual(found, ARES_MODE2_STRIDE_TWO)

    def test_a_stride_of_zero_repeats_one_row(self) -> None:
        # Arrange
        chip = started(0, control=0x01, stride=0).tick(START_CLOCKS)

        # Act
        found = drained(chip, 16)

        # Assert
        self.assertEqual(found, ARES_MODE0_STRIDE_ZERO)


class StartTest(unittest.TestCase):
    def test_the_ready_bit_is_clear_one_clock_before_the_start_lands(self) -> None:
        # Arrange
        chip = started(0)

        # Act
        status = chip.tick(START_CLOCKS - 1).read(0x480C)

        # Assert
        self.assertEqual(status, 0x00)

    def test_and_set_once_it_has(self) -> None:
        # Arrange
        chip = started(0)

        # Act
        status = chip.tick(START_CLOCKS).read(0x480C)

        # Assert
        self.assertEqual(status, 0x80)

    def test_a_new_start_clears_the_ready_bit_at_once(self) -> None:
        # Arrange
        chip = started(0).tick(START_CLOCKS)

        # Act
        status = started(1, part=chip).read(0x480C)

        # Assert
        self.assertEqual(status, 0x00)

    def test_a_directory_entry_naming_mode_three_starts_nothing(self) -> None:
        # Arrange
        chip = started(3).tick(START_CLOCKS)

        # Act
        found = (chip.read(0x480C), drained(chip, 4))

        # Assert
        self.assertEqual(found, (0x00, "00000000"))

    def test_a_read_before_the_start_lands_returns_zero(self) -> None:
        # Arrange
        chip = started(0)

        # Act
        found = drained(chip, 2)

        # Assert
        self.assertEqual(found, "0000")


class CounterTest(unittest.TestCase):
    def test_every_read_of_the_port_counts_the_length_down(self) -> None:
        # Arrange
        chip = started(0).tick(START_CLOCKS)
        chip.write(0x4809, 0x01)
        chip.write(0x480A, 0x00)

        # Act
        drained(chip, 2)

        # Assert
        self.assertEqual((chip.read(0x4809), chip.read(0x480A)), (0xFF, 0xFF))


class RegisterTest(unittest.TestCase):
    def test_the_table_bank_keeps_seven_bits(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        chip.write(0x4803, 0xFF)

        # Assert
        self.assertEqual(chip.read(0x4803), 0x7F)

    def test_the_control_register_keeps_two_bits(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        chip.write(0x480B, 0xFF)

        # Assert
        self.assertEqual(chip.read(0x480B), 0x03)

    def test_the_status_register_ignores_a_write(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        chip.write(0x480C, 0xFF)

        # Assert
        self.assertEqual(chip.read(0x480C), 0x00)

    def test_register_eight_reads_zero_whatever_was_written(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        chip.write(0x4808, 0xFF)

        # Assert
        self.assertEqual(chip.read(0x4808), 0x00)

    def test_the_plain_registers_read_back_what_was_written(self) -> None:
        # Arrange
        chip = a_part()
        written = {0x4801: 0x12, 0x4802: 0x34, 0x4805: 0x56, 0x4807: 0x78, 0x480A: 0x9A}

        # Act
        for register, value in written.items():
            chip.write(register, value)

        # Assert
        self.assertEqual({register: chip.read(register) for register in written}, written)

    def test_registers_between_the_units_drive_nothing(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        found = [chip.read(register) for register in (0x480D, 0x480E, 0x480F)]

        # Assert
        self.assertEqual(found, [None, None, None])


if __name__ == "__main__":
    unittest.main()
