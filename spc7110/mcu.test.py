import random
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

MEGABYTE = 0x100000

PROGRAM = random.Random(5).randbytes(MEGABYTE)

DATA = random.Random(6).randbytes(3 * MEGABYTE)


def a_part() -> Any:
    return spc7110.Chip("spc7110", rom=PROGRAM + DATA).reset()


def banked(**registers: int) -> Any:
    chip = a_part()
    for name, value in registers.items():
        chip.write(int(name[1:], 16), value)
    return chip


class ProgramTest(unittest.TestCase):
    def test_the_low_banks_read_the_program_rom_upper_halves(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        found = [chip.read(address) for address in (0x008000, 0x0FFFFF, 0x808000)]

        # Assert
        self.assertEqual(found, [PROGRAM[0x8000], PROGRAM[0xFFFFF], PROGRAM[0x8000]])

    def test_bank_c0_reads_the_program_rom_from_its_start(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        found = [chip.read(address) for address in (0xC00000, 0xCF1234)]

        # Assert
        self.assertEqual(found, [PROGRAM[0], PROGRAM[0xF1234]])

    def test_bit_two_of_the_size_register_puts_the_program_rom_in_bank_d0(self) -> None:
        # Arrange
        chip = banked(r4834=0x04)

        # Act
        found = chip.read(0xD00005)

        # Assert
        self.assertEqual(found, PROGRAM[5])


class WindowTest(unittest.TestCase):
    def test_each_window_reads_the_megabyte_its_register_names(self) -> None:
        # Arrange
        chip = banked(r4834=0x02, r4831=0x00, r4832=0x01, r4833=0x02)

        # Act
        found = [chip.read(address) for address in (0xD00010, 0xE00010, 0xF00010)]

        # Assert
        self.assertEqual(found, [DATA[0x10], DATA[MEGABYTE + 0x10], DATA[2 * MEGABYTE + 0x10]])

    def test_the_low_banks_reach_the_same_windows(self) -> None:
        # Arrange
        chip = banked(r4834=0x02, r4832=0x01)

        # Act
        found = chip.read(0x208010)

        # Assert
        self.assertEqual(found, DATA[MEGABYTE + 0x8010])

    def test_a_one_megabyte_size_folds_every_window_onto_the_first(self) -> None:
        # Arrange
        chip = banked(r4834=0x00, r4833=0x02)

        # Act
        found = chip.read(0xF00010)

        # Assert
        self.assertEqual(found, DATA[0x10])

    def test_a_data_rom_short_of_a_power_of_two_mirrors_its_last_part(self) -> None:
        # Arrange
        chip = banked(r4834=0x02, r4833=0x03)

        # Act
        found = chip.read(0xF00010)

        # Assert
        self.assertEqual(found, DATA[2 * MEGABYTE + 0x10])

    def test_the_upper_half_reads_zero_below_the_largest_size(self) -> None:
        # Arrange
        chip = banked(r4834=0x02, r4833=0x04)

        # Act
        found = chip.read(0xF00010)

        # Assert
        self.assertEqual(found, 0x00)

    def test_and_mirrors_at_the_largest_size(self) -> None:
        # Arrange
        chip = banked(r4834=0x03, r4833=0x04)

        # Act
        found = chip.read(0xF00010)

        # Assert
        self.assertEqual(found, DATA[0x10])


class RegisterTest(unittest.TestCase):
    def test_each_bank_register_keeps_the_bits_ares_keeps(self) -> None:
        # Arrange
        chip = a_part()
        registers = (0x4830, 0x4831, 0x4832, 0x4833, 0x4834)

        # Act
        for register in registers:
            chip.write(register, 0xFF)

        # Assert
        self.assertEqual([chip.read(register) for register in registers], [0x87, 7, 7, 7, 7])

    def test_registers_past_the_bank_unit_drive_nothing(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        found = [chip.read(register) for register in (0x4835, 0x483F)]

        # Assert
        self.assertEqual(found, [None, None])

    def test_a_write_past_the_bank_unit_changes_nothing(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        chip.write(0x4835, 0xFF)

        # Assert
        self.assertIsNone(chip.read(0x4835))


class SaveRamTest(unittest.TestCase):
    def test_save_ram_reads_zero_until_bit_seven_enables_it(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=PROGRAM + DATA, ram=bytearray(b"\x5a" * 0x2000)).reset()

        # Act
        found = chip.read(0x006000)

        # Assert
        self.assertEqual(found, 0x00)

    def test_and_reads_its_bytes_once_enabled(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=PROGRAM + DATA, ram=bytearray(b"\x5a" * 0x2000)).reset()
        chip.write(0x4830, 0x80)

        # Act
        found = chip.read(0x807FFF)

        # Assert
        self.assertEqual(found, 0x5A)

    def test_a_write_lands_in_the_ram_it_was_handed_at_its_mirrored_offset(self) -> None:
        # Arrange
        ram = bytearray(0x2000)
        chip = spc7110.Chip("spc7110", rom=PROGRAM + DATA, ram=ram).reset()
        chip.write(0x4830, 0x80)

        # Act
        chip.write(0x016001, 0x77)

        # Assert
        self.assertEqual(ram[0x0001], 0x77)

    def test_a_write_while_disabled_is_dropped(self) -> None:
        # Arrange
        ram = bytearray(0x2000)
        chip = spc7110.Chip("spc7110", rom=PROGRAM + DATA, ram=ram).reset()

        # Act
        chip.write(0x006001, 0x77)

        # Assert
        self.assertEqual(ram[0x0001], 0x00)

    def test_without_save_ram_the_window_is_not_answered(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        attempt = lambda: chip.read(0x006000)  # noqa: E731

        # Assert
        self.assertRaises(spc7110.OutOfRange, attempt)


if __name__ == "__main__":
    unittest.main()
