import sys
import unittest
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

MULTIPLY_DONE = 31

DIVIDE_DONE = 41


def a_part() -> Any:
    return spc7110.Chip("spc7110").reset()


def multiplied(multiplicand: int, multiplier: int, signed: bool = False) -> Any:
    chip = a_part()
    chip.write(0x482E, int(signed))
    chip.write(0x4820, multiplicand & 0xFF)
    chip.write(0x4821, multiplicand >> 8)
    chip.write(0x4824, multiplier & 0xFF)
    chip.write(0x4825, multiplier >> 8)
    return chip


def divided(dividend: int, divisor: int, signed: bool = False) -> Any:
    chip = a_part()
    chip.write(0x482E, int(signed))
    for at in range(4):
        chip.write(0x4820 + at, (dividend >> (8 * at)) & 0xFF)
    chip.write(0x4826, divisor & 0xFF)
    chip.write(0x4827, divisor >> 8)
    return chip


def result(chip: Any) -> int:
    return int(sum(chip.read(0x4828 + at) << (8 * at) for at in range(4)))


def remainder(chip: Any) -> int:
    return int(chip.read(0x482C) | chip.read(0x482D) << 8)


class MultiplyTest(unittest.TestCase):
    def test_an_unsigned_product_lands_in_four_bytes(self) -> None:
        # Arrange
        chip = multiplied(0x1234, 0x5678)

        # Act
        chip.tick(MULTIPLY_DONE)

        # Assert
        self.assertEqual(result(chip), 0x06260060)

    def test_the_largest_unsigned_product_fits(self) -> None:
        # Arrange
        chip = multiplied(0xFFFF, 0xFFFF)

        # Act
        chip.tick(MULTIPLY_DONE)

        # Assert
        self.assertEqual(result(chip), 0xFFFE0001)

    def test_a_signed_product_is_twos_complement(self) -> None:
        # Arrange
        chip = multiplied(0xFFFE, 0x0003, signed=True)

        # Act
        chip.tick(MULTIPLY_DONE)

        # Assert
        self.assertEqual(result(chip), 0xFFFFFFFA)

    def test_the_status_reads_busy_while_it_runs(self) -> None:
        # Arrange
        chip = multiplied(2, 3)

        # Act
        chip.tick(MULTIPLY_DONE - 1)

        # Assert
        self.assertEqual((chip.read(0x482F), result(chip)), (0x81, 0))

    def test_and_keeps_only_the_low_bit_after(self) -> None:
        # Arrange
        chip = multiplied(2, 3)

        # Act
        chip.tick(MULTIPLY_DONE)

        # Assert
        self.assertEqual((chip.read(0x482F), result(chip)), (0x01, 6))

    def test_an_operand_written_during_the_wait_is_the_one_used(self) -> None:
        # Arrange
        chip = multiplied(2, 3).tick(10)

        # Act
        chip.write(0x4820, 5)

        # Assert
        self.assertEqual(result(chip.tick(MULTIPLY_DONE - 10)), 15)


class DivideTest(unittest.TestCase):
    def test_an_unsigned_quotient_and_remainder(self) -> None:
        # Arrange
        chip = divided(100000, 7)

        # Act
        chip.tick(DIVIDE_DONE)

        # Assert
        self.assertEqual((result(chip), remainder(chip)), (14285, 5))

    def test_a_signed_quotient_rounds_toward_zero(self) -> None:
        # Arrange
        chip = divided(0xFFFFFFF9, 0x0002, signed=True)

        # Act
        chip.tick(DIVIDE_DONE)

        # Assert
        self.assertEqual((result(chip), remainder(chip)), (0xFFFFFFFD, 0xFFFF))

    def test_a_signed_remainder_takes_the_dividends_sign(self) -> None:
        # Arrange
        chip = divided(7, 0xFFFE, signed=True)

        # Act
        chip.tick(DIVIDE_DONE)

        # Assert
        self.assertEqual((result(chip), remainder(chip)), (0xFFFFFFFD, 1))

    def test_dividing_by_zero_gives_zero_and_keeps_the_dividends_low_half(self) -> None:
        # Arrange
        chip = divided(0x12345678, 0)

        # Act
        chip.tick(DIVIDE_DONE)

        # Assert
        self.assertEqual((result(chip), remainder(chip)), (0, 0x5678))

    def test_the_most_negative_dividend_over_minus_one_wraps(self) -> None:
        # Arrange
        chip = divided(0x80000000, 0xFFFF, signed=True)

        # Act
        chip.tick(DIVIDE_DONE)

        # Assert
        self.assertEqual((result(chip), remainder(chip)), (0x80000000, 0))

    def test_the_status_reads_busy_until_it_is_done(self) -> None:
        # Arrange
        chip = divided(9, 3)

        # Act
        found = (chip.tick(DIVIDE_DONE - 1).read(0x482F), chip.tick(1).read(0x482F))

        # Assert
        self.assertEqual(found, (0x80, 0x00))

    def test_a_multiply_and_a_divide_written_together_run_in_turn(self) -> None:
        # Arrange
        chip = divided(9, 3)
        chip.write(0x4825, 0)

        # Act
        chip.tick(MULTIPLY_DONE + 40)

        # Assert
        self.assertEqual((result(chip), chip.read(0x482F)), (3, 0x01))


class RegisterTest(unittest.TestCase):
    def test_the_sign_setting_keeps_one_bit(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        chip.write(0x482E, 0xFF)

        # Assert
        self.assertEqual(chip.read(0x482E), 0x01)

    def test_the_results_and_the_status_ignore_a_write(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        for register in (0x4828, 0x4829, 0x482A, 0x482B, 0x482C, 0x482D, 0x482F):
            chip.write(register, 0xFF)

        # Assert
        self.assertEqual([chip.read(register) for register in range(0x4828, 0x482E)], [0] * 6)

    def test_the_operands_read_back(self) -> None:
        # Arrange
        chip = a_part()

        # Act
        chip.write(0x4823, 0xA5)

        # Assert
        self.assertEqual(chip.read(0x4823), 0xA5)


if __name__ == "__main__":
    unittest.main()
