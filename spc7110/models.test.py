import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from spc7110 import errors, models


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
        with self.assertRaises(errors.UnknownMode):
            models.describe("8bpp")

    def test_a_number_the_chip_does_not_have_is_refused(self) -> None:
        with self.assertRaises(errors.UnknownMode):
            models.describe(3)

    def test_and_the_refusal_lists_what_there_is(self) -> None:
        with self.assertRaises(errors.UnknownMode) as caught:
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


class PartTest(unittest.TestCase):
    """The catalogue of parts, which is not the catalogue of modes.

    Three modes exist and one chip does all three, so a mode is an argument to a
    call rather than a name in this catalogue. Keeping them apart is what stops
    a caller writing `Chip("4bpp")` and getting something.
    """

    def test_the_catalogue_holds_the_one_part_there_is(self) -> None:
        self.assertEqual(sorted(models.MODELS), ["spc7110"])

    def test_a_part_prints_as_itself_and_says_how_many_modes_it_has(self) -> None:
        held = repr(models.describe_part("spc7110"))

        self.assertEqual(held, "<Model spc7110, 3 modes>")

    def test_a_built_part_prints_as_itself(self) -> None:
        held = repr(models.describe_part("spc7110").build())

        self.assertEqual(held, "<Chip spc7110>")

    def test_a_part_answers_to_the_names_a_board_calls_it(self) -> None:
        for name in ("spc7110", "spc-7110", "epsonspc7110"):
            self.assertEqual(models.describe_part(name).name, "spc7110", name)

    def test_a_name_no_part_answers_to_is_refused(self) -> None:
        with self.assertRaises(errors.UnknownModelError):
            models.describe_part("spc7120")

    def test_and_the_refusal_names_what_would_have_worked(self) -> None:
        with self.assertRaises(errors.UnknownModelError) as raised:
            models.describe_part("spc7120")

        self.assertIn("spc7110", str(raised.exception))

    def test_a_reset_hands_the_part_back(self) -> None:
        """It clears nothing, and the record says so. It exists so a caller can chain."""
        built = models.describe_part("spc7110").build()

        self.assertIs(built.reset(), built)

    def test_a_mode_the_chip_does_not_have_is_refused_at_the_call(self) -> None:
        built = models.describe_part("spc7110").build()

        with self.assertRaises(errors.UnknownMode):
            built.decompress(bytes(64), "16bpp")


if __name__ == "__main__":
    unittest.main()
