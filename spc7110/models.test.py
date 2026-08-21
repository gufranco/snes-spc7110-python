import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spc7110 import models


class CatalogueTest(unittest.TestCase):
    def test_the_catalogue_names_every_mode_the_chip_has(self) -> None:
        self.assertEqual(len(models.MODES), 3)

    def test_every_mode_says_what_it_produces(self) -> None:
        for mode in models.MODES.values():
            self.assertTrue(mode.summary.strip())

    def test_each_one_names_how_many_bits_a_pixel_takes(self) -> None:
        self.assertEqual([mode.depth for mode in models.MODES.values()], [1, 2, 4])

    def test_a_mode_prints_as_something_a_person_can_read(self) -> None:
        self.assertIn("1bpp", repr(models.describe("1bpp")))


class NameTest(unittest.TestCase):
    def test_a_mode_is_found_by_its_number(self) -> None:
        self.assertEqual(models.describe(0).number, 0)

    def test_and_by_the_depth_it_produces(self) -> None:
        self.assertEqual(models.describe("4bpp").number, 2)

    def test_case_and_separators_do_not_matter(self) -> None:
        self.assertEqual(models.describe("2 BPP").number, 1)

    def test_a_name_no_mode_answers_to_is_refused(self) -> None:
        with self.assertRaises(models.UnknownMode):
            models.describe("8bpp")

    def test_a_number_the_chip_does_not_have_is_refused(self) -> None:
        with self.assertRaises(models.UnknownMode):
            models.describe(3)

    def test_and_the_refusal_lists_what_there_is(self) -> None:
        with self.assertRaises(models.UnknownMode) as caught:
            models.describe("nothing")

        self.assertIn("1bpp", str(caught.exception))


class BuildTest(unittest.TestCase):
    def test_a_mode_builds_a_decompressor_started_on_it(self) -> None:
        built = models.describe("2bpp").build(bytes(range(256)))

        self.assertEqual(built.mode, 1)

    def test_the_place_to_start_can_be_named(self) -> None:
        built = models.describe(0).build(bytes(range(256)), offset=4)

        self.assertGreaterEqual(built.offset, 4)

    def test_a_built_decompressor_produces_bytes(self) -> None:
        built = models.describe(0).build(bytes(range(256)))

        self.assertEqual(len(built.read(16)), 16)


if __name__ == "__main__":
    unittest.main()
