import sys
import unittest
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spc7110

PART = "spc7110"

STREAM = bytes(range(256))


class CatalogueTest(unittest.TestCase):
    def test_the_catalogue_names_every_mode_the_chip_has(self) -> None:
        # Arrange
        expected = ["1bpp", "2bpp", "4bpp"]

        # Act
        named = sorted(spc7110.MODES)

        # Assert
        self.assertEqual(named, expected)

    def test_every_mode_says_what_it_produces(self) -> None:
        # Arrange
        modes = spc7110.MODES.values()

        # Act
        blank = [mode.name for mode in modes if not mode.summary.strip()]

        # Assert
        self.assertEqual(blank, [])

    def test_each_one_names_how_many_bits_a_pixel_takes(self) -> None:
        # Arrange
        modes = spc7110.MODES.values()

        # Act
        depths = [mode.depth for mode in modes]

        # Assert
        self.assertEqual(depths, [1, 2, 4])

    def test_a_mode_prints_as_something_a_person_can_read(self) -> None:
        # Arrange
        mode = spc7110.mode_named("1bpp")

        # Act
        shown = repr(mode)

        # Assert
        self.assertEqual(shown, "<Mode 0, 1bpp>")


class NameTest(unittest.TestCase):
    def test_a_mode_is_found_by_its_number(self) -> None:
        # Arrange
        number = 0

        # Act
        found = spc7110.mode_named(number)

        # Assert
        self.assertEqual(found.name, "1bpp")

    def test_and_by_the_depth_it_produces(self) -> None:
        # Arrange
        name = "4bpp"

        # Act
        found = spc7110.mode_named(name)

        # Assert
        self.assertEqual(found.number, 2)

    def test_case_and_separators_do_not_matter(self) -> None:
        # Arrange
        name = "2 BPP"

        # Act
        found = spc7110.mode_named(name)

        # Assert
        self.assertEqual(found.number, 1)

    def test_a_name_no_mode_answers_to_is_refused(self) -> None:
        # Arrange
        name = "8bpp"

        # Act
        naming = partial(spc7110.mode_named, name)

        # Assert
        self.assertRaises(spc7110.UnknownMode, naming)

    def test_a_number_the_chip_does_not_have_is_refused(self) -> None:
        # Arrange
        number = 3

        # Act
        naming = partial(spc7110.mode_named, number)

        # Assert
        self.assertRaises(spc7110.UnknownMode, naming)

    def test_and_the_refusal_lists_what_there_is(self) -> None:
        # Arrange
        name = "nothing"

        # Act
        naming = partial(spc7110.mode_named, name)

        # Assert
        with self.assertRaises(spc7110.UnknownMode) as caught:
            naming()
        self.assertEqual(
            str(caught.exception), "nothing is not a mode this chip has; it has 1bpp, 2bpp, 4bpp"
        )


class BuildTest(unittest.TestCase):
    def test_a_mode_builds_a_decompressor_started_on_it(self) -> None:
        # Arrange
        mode = spc7110.mode_named("2bpp")

        # Act
        built = mode.build(STREAM)

        # Assert
        self.assertEqual(built.mode, 1)

    def test_the_place_to_start_can_be_named(self) -> None:
        # Arrange
        mode = spc7110.mode_named(0)

        # Act
        built = mode.build(STREAM, offset=4)

        # Assert
        self.assertEqual(built.read(16), mode.build(STREAM[4:] + STREAM[:4]).read(16))

    def test_a_built_decompressor_produces_bytes(self) -> None:
        # Arrange
        mode = spc7110.mode_named(0)

        # Act
        built = mode.build(STREAM)

        # Assert
        self.assertEqual(len(built.read(16)), 16)

    def test_a_mode_skips_the_output_it_is_told_to(self) -> None:
        # Arrange
        mode = spc7110.mode_named("4bpp")

        # Act
        built = mode.build(STREAM, index=3)

        # Assert
        self.assertEqual(built.read(5).hex(" "), "00 00 00 00 15")


class PartTest(unittest.TestCase):
    def test_the_catalogue_holds_the_one_part_there_is(self) -> None:
        # Arrange
        catalogue = spc7110.MODELS

        # Act
        names = sorted(catalogue)

        # Assert
        self.assertEqual(names, [PART])

    def test_a_part_prints_as_itself_and_says_how_many_modes_it_has(self) -> None:
        # Arrange
        model = spc7110.MODELS[PART]

        # Act
        held = repr(model)

        # Assert
        self.assertEqual(held, "<Model spc7110, 3 modes>")

    def test_a_part_carries_its_names_and_its_modes(self) -> None:
        # Arrange
        model = spc7110.MODELS[PART]

        # Act
        carried = (model.name, model.aliases, model.modes)

        # Assert
        self.assertEqual(
            carried, ("spc7110", ("spc-7110", "epsonspc7110"), ("1bpp", "2bpp", "4bpp"))
        )

    def test_a_built_part_prints_as_itself(self) -> None:
        # Arrange
        model = spc7110.MODELS[PART]

        # Act
        held = repr(model.build())

        # Assert
        self.assertEqual(held, "<Chip spc7110>")

    def test_a_part_answers_to_the_names_a_board_calls_it(self) -> None:
        # Arrange
        names = ("spc7110", "spc-7110", "epsonspc7110", "SPC_7110", "Epson SPC7110")

        # Act
        models = [spc7110.Chip(name).model for name in names]

        # Assert
        self.assertEqual(models, [PART] * len(names))

    def test_a_name_no_part_answers_to_is_refused(self) -> None:
        # Arrange
        name = "spc7120"

        # Act
        building = partial(spc7110.Chip, name)

        # Assert
        self.assertRaises(spc7110.UnknownModelError, building)

    def test_and_the_refusal_names_what_would_have_worked(self) -> None:
        # Arrange
        name = "spc7120"

        # Act
        building = partial(spc7110.Chip, name)

        # Assert
        with self.assertRaises(spc7110.UnknownModelError) as raised:
            building()
        self.assertEqual(
            str(raised.exception), "spc7120 is not a part this package covers; it has spc7110"
        )

    def test_a_reset_hands_the_part_back(self) -> None:
        # Arrange
        built = spc7110.Chip(PART)

        # Act
        returned = built.reset()

        # Assert
        self.assertIs(returned, built)

    def test_a_mode_the_chip_does_not_have_is_refused_at_the_call(self) -> None:
        # Arrange
        built = spc7110.Chip(PART)

        # Act
        starting = partial(built.decompress, bytes(64), "16bpp")

        # Assert
        self.assertRaises(spc7110.UnknownMode, starting)


class NamingNoneTest(unittest.TestCase):
    def test_building_without_naming_a_model_is_refused(self) -> None:
        # Arrange
        named = None

        # Act
        building = partial(spc7110.Chip, named)

        # Assert
        self.assertRaises(spc7110.UnknownModelError, building)

    def test_and_the_refusal_names_every_model_there_is(self) -> None:
        # Arrange
        named = None

        # Act
        building = partial(spc7110.Chip, named)

        # Assert
        with self.assertRaises(spc7110.UnknownModelError) as caught:
            building()
        self.assertEqual(
            str(caught.exception),
            "no model was named, and this package will not choose one for you."
            " Name one of: spc7110",
        )

    def test_nothing_named_describe_is_published(self) -> None:
        # Arrange
        package = spc7110

        # Act
        found = hasattr(package, "describe")

        # Assert
        self.assertFalse(found)

    def test_nor_anything_named_describe_part(self) -> None:
        # Arrange
        package = spc7110

        # Act
        found = hasattr(package, "describe_part")

        # Assert
        self.assertFalse(found)

    def test_and_no_default_model_is_published_either(self) -> None:
        # Arrange
        package = spc7110

        # Act
        found = hasattr(package, "DEFAULT_MODEL")

        # Assert
        self.assertFalse(found)

    def test_the_mode_resolver_is_still_published_under_its_own_name(self) -> None:
        # Arrange
        by_number = spc7110.mode_named(1)

        # Act
        by_name = spc7110.mode_named("2bpp")

        # Assert
        self.assertIs(by_number, by_name)


if __name__ == "__main__":
    unittest.main()
