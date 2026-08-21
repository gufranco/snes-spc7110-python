import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spc7110 import tables


class EvolutionTest(unittest.TestCase):
    def test_the_table_has_the_rows_the_coder_walks(self) -> None:
        self.assertEqual(len(tables.EVOLUTION), 53)

    def test_every_row_carries_a_probability_two_successors_and_a_flag(self) -> None:
        for row in tables.EVOLUTION:
            self.assertEqual(len(row), 4)

    def test_every_probability_fits_in_a_byte(self) -> None:
        for row in tables.EVOLUTION:
            self.assertTrue(0 < row[tables.PROBABILITY] <= 0xFF)

    def test_every_successor_names_a_row_that_exists(self) -> None:
        for row in tables.EVOLUTION:
            self.assertLess(row[tables.NEXT_LPS], len(tables.EVOLUTION))
            self.assertLess(row[tables.NEXT_MPS], len(tables.EVOLUTION))

    def test_the_flag_that_swaps_the_symbols_is_a_flag(self) -> None:
        for row in tables.EVOLUTION:
            self.assertIn(row[tables.TOGGLE_INVERT], (0, 1))

    def test_only_the_rows_that_start_a_run_may_swap_the_symbols(self) -> None:
        swapping = [at for at, row in enumerate(tables.EVOLUTION) if row[tables.TOGGLE_INVERT]]

        self.assertEqual(swapping, [0, 6, 19, 39, 47])

    def test_the_probabilities_fall_away_from_each_starting_row(self) -> None:
        self.assertGreater(
            tables.EVOLUTION[1][tables.PROBABILITY], tables.EVOLUTION[5][tables.PROBABILITY]
        )


class ContextTest(unittest.TestCase):
    def test_the_context_table_has_a_row_for_every_context(self) -> None:
        self.assertEqual(len(tables.MODE2_CONTEXT), 32)

    def test_each_row_names_where_to_go_for_either_symbol(self) -> None:
        for row in tables.MODE2_CONTEXT:
            self.assertEqual(len(row), 2)

    def test_every_successor_names_a_context_that_exists(self) -> None:
        for row in tables.MODE2_CONTEXT:
            for successor in row:
                self.assertLess(successor, len(tables.MODE2_CONTEXT))

    def test_the_upper_half_all_settles_on_the_same_context(self) -> None:
        for row in tables.MODE2_CONTEXT[15:]:
            self.assertEqual(row, (31, 31))


class MortonTest(unittest.TestCase):
    def test_the_two_plane_shuffle_has_a_table_per_half(self) -> None:
        self.assertEqual(len(tables.MORTON16), 2)

    def test_and_the_four_plane_shuffle_one_per_quarter(self) -> None:
        self.assertEqual(len(tables.MORTON32), 4)

    def test_every_table_covers_a_whole_byte(self) -> None:
        for table in tables.MORTON16 + tables.MORTON32:
            self.assertEqual(len(table), 256)

    def test_taking_nothing_apart_gives_nothing(self) -> None:
        self.assertEqual(tables.morton_2x8(0), 0)
        self.assertEqual(tables.morton_4x8(0), 0)

    def test_two_planes_of_all_ones_come_apart_as_all_ones(self) -> None:
        self.assertEqual(tables.morton_2x8(0xFFFF), 0xFFFF)

    def test_four_planes_of_all_ones_do_too(self) -> None:
        self.assertEqual(tables.morton_4x8(0xFFFFFFFF), 0xFFFFFFFF)

    def test_the_two_plane_shuffle_is_a_permutation_of_sixteen_bits(self) -> None:
        seen = set()
        for bit in range(16):
            found = tables.morton_2x8(1 << bit)
            self.assertEqual(bin(found).count("1"), 1)
            seen.add(found)

        self.assertEqual(len(seen), 16)

    def test_the_four_plane_shuffle_is_a_permutation_of_thirty_two_bits(self) -> None:
        seen = set()
        for bit in range(32):
            found = tables.morton_4x8(1 << bit)
            self.assertEqual(bin(found).count("1"), 1)
            seen.add(found)

        self.assertEqual(len(seen), 32)

    def test_alternating_bits_separate_into_two_solid_halves(self) -> None:
        self.assertEqual(tables.morton_2x8(0x5555), 0x00FF)

    def test_and_the_other_alternation_into_the_other_half(self) -> None:
        self.assertEqual(tables.morton_2x8(0xAAAA), 0xFF00)


if __name__ == "__main__":
    unittest.main()
