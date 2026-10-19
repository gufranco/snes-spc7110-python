import random
import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

MEGABYTE = 0x100000

IMAGE = random.Random(8).randbytes(2 * MEGABYTE)

ARES_POWER_BANKS = [0x00, 0x00, 0x01, 0x02, 0x00]

BANK_REGISTERS = (0x4830, 0x4831, 0x4832, 0x4833, 0x4834)

UNIT_REGISTERS = (0x4801, 0x4802, 0x4804, 0x4811, 0x4814, 0x4820, 0x4824, 0x4826)


def registers(chip: Any, which: tuple[int, ...]) -> list[int]:
    return [chip.read(register) for register in which]


def refuses(chip: Any, address: int) -> bool:
    try:
        chip.read(address)
    except spc7110.OutOfRange:
        return True
    return False


class ConstructionTest(unittest.TestCase):
    def test_without_a_rom_it_builds_a_program_and_a_data_rom_of_its_own(self) -> None:
        # Arrange
        model = "spc7110"

        # Act
        chip = spc7110.Chip(model)

        # Assert
        self.assertEqual((len(chip.program), len(chip.data), chip.ram), (MEGABYTE, MEGABYTE, None))

    def test_a_rom_it_is_handed_is_the_one_it_keeps(self) -> None:
        # Arrange
        rom = IMAGE

        # Act
        chip = spc7110.Chip("spc7110", rom=rom)

        # Assert
        self.assertEqual((chip.rom is rom, chip.data), (True, IMAGE[MEGABYTE:]))

    def test_a_rom_with_no_data_after_the_program_is_refused(self) -> None:
        # Arrange
        rom = bytes(MEGABYTE)

        # Act
        attempt = lambda: spc7110.Chip("spc7110", rom=rom)  # noqa: E731

        # Assert
        self.assertRaises(spc7110.Empty, attempt)

    def test_save_ram_with_no_bytes_in_it_is_refused(self) -> None:
        # Arrange
        ram = bytearray()

        # Act
        attempt = lambda: spc7110.Chip("spc7110", rom=IMAGE, ram=ram)  # noqa: E731

        # Assert
        self.assertRaises(spc7110.Empty, attempt)

    def test_the_registers_come_up_scrambled_rather_than_cleared(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE)

        # Act
        found = registers(chip, UNIT_REGISTERS)

        # Assert
        self.assertNotEqual(found, [0] * len(UNIT_REGISTERS))

    def test_the_same_seed_scrambles_the_same_way(self) -> None:
        # Arrange
        seed = 1234

        # Act
        found = [
            registers(spc7110.Chip("spc7110", rom=IMAGE, seed=seed), UNIT_REGISTERS)
            for _ in range(2)
        ]

        # Assert
        self.assertEqual(found[0], found[1])

    def test_a_different_seed_scrambles_differently(self) -> None:
        # Arrange
        seeds = (1, 2)

        # Act
        found = [
            registers(spc7110.Chip("spc7110", rom=IMAGE, seed=seed), UNIT_REGISTERS)
            for seed in seeds
        ]

        # Assert
        self.assertNotEqual(found[0], found[1])

    def test_a_scrambled_part_can_be_clocked_before_any_reset(self) -> None:
        # Arrange
        chips = [spc7110.Chip("spc7110", rom=IMAGE, seed=seed) for seed in range(8)]

        # Act
        clocked = [chip.tick(100) for chip in chips]

        # Assert
        self.assertEqual(clocked, chips)

    def test_it_prints_as_a_chip_naming_its_model(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE)

        # Act
        shown = repr(chip)

        # Assert
        self.assertEqual(shown, "<Chip spc7110>")


class ResetTest(unittest.TestCase):
    def test_reset_sets_the_bank_registers_ares_powers_up_with(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE)

        # Act
        chip.reset()

        # Assert
        self.assertEqual(registers(chip, BANK_REGISTERS), ARES_POWER_BANKS)

    def test_and_clears_every_unit_register_ares_clears(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE)

        # Act
        chip.reset()

        # Assert
        self.assertEqual(registers(chip, UNIT_REGISTERS), [0] * len(UNIT_REGISTERS))

    def test_and_drops_an_operation_that_was_waiting(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE).reset()
        chip.write(0x4820, 3)
        chip.write(0x4825, 0)
        chip.reset()

        # Act
        chip.tick(100)

        # Assert
        self.assertEqual(chip.read(0x482F), 0x00)

    def test_reset_and_tick_hand_the_part_back(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE)

        # Act
        handed = (chip.reset(), chip.tick())

        # Assert
        self.assertEqual(handed, (chip, chip))


class DecodeTest(unittest.TestCase):
    def test_bank_50_is_the_decompression_port(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE).reset()

        # Act
        chip.read(0x501234)

        # Assert
        self.assertEqual((chip.read(0x4809), chip.read(0x480A)), (0xFF, 0xFF))

    def test_bank_58_is_register_eight(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE).reset()

        # Act
        found = chip.read(0x58FFFF)

        # Assert
        self.assertEqual(found, 0x00)

    def test_the_registers_answer_in_the_mirrored_low_banks(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE).reset()

        # Act
        chip.write(0xBF4801, 0x42)

        # Assert
        self.assertEqual(chip.read(0x004801), 0x42)

    def test_a_write_to_rom_changes_nothing(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE).reset()

        # Act
        chip.write(0xC00000, IMAGE[0] ^ 0xFF)

        # Assert
        self.assertEqual(chip.read(0xC00000), IMAGE[0])

    def test_addresses_the_part_does_not_decode_are_refused(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE).reset()
        addresses = (0x000000, 0x004000, 0x4840, 0x400000, 0x7E0000, 0x1000000, -1)

        # Act
        refused = [address for address in addresses if refuses(chip, address)]

        # Assert
        self.assertEqual(refused, list(addresses))

    def test_every_window_the_part_decodes_answers(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE).reset()
        addresses = (0x004800, 0x00483F, 0x008000, 0x3FFFFF, 0x500000, 0x580000, 0xFFFFFF)

        # Act
        refused = [address for address in addresses if refuses(chip, address)]

        # Assert
        self.assertEqual(refused, [])

    def test_a_write_to_an_undecoded_address_is_refused_too(self) -> None:
        # Arrange
        chip = spc7110.Chip("spc7110", rom=IMAGE).reset()

        # Act
        attempt = lambda: chip.write(0x004840, 0)  # noqa: E731

        # Assert
        self.assertRaises(spc7110.OutOfRange, attempt)


if __name__ == "__main__":
    unittest.main()
